# chatbot/services/chat_service.py

from django.utils import timezone
from ..models import Session, Message
from .ai_service import ai_service
from .cache_service import cache_service
from .token_service import token_service
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """
    Orchestrates chat operations with caching and token management
    """
    
    def __init__(self):
        self.ai_service = ai_service
        self.cache_service = cache_service
        self.token_service = token_service
    
    def get_last_messages(self, session_id: int, limit: int = 20) -> List[Message]:
        """
        Retrieve last N messages with caching
        
        Performance:
        - Cache hit: ~1ms
        - Cache miss: ~50ms (database query)
        """
        # Try cache first
        cached_messages = self.cache_service.get_messages(session_id)
        
        if cached_messages is not None:
            # Extend TTL for active sessions
            self.cache_service.extend_ttl(session_id)
            
            # Convert dicts back to Message objects
            messages = []
            for msg_dict in cached_messages[:limit]:
                msg = Message(
                    message_id=msg_dict['message_id'],
                    session_id=session_id,
                    author=msg_dict['author'],
                    message=msg_dict['message'],
                    user_id=msg_dict['user_id'],
                    created_at=timezone.datetime.fromisoformat(msg_dict['created_at'])
                )
                messages.append(msg)
            
            logger.debug(f"Returned {len(messages)} messages from cache")
            return messages
        
        # Cache miss - query database
        messages = Message.objects.filter(
            session_id=session_id
        ).order_by('-created_at')[:limit]
        
        messages_list = list(reversed(messages))
        
        # Cache for next time
        messages_dict = [
            {
                'message_id': m.message_id,
                'session_id': session_id,
                'author': m.author,
                'message': m.message,
                'user_id': m.user_id,
                'created_at': m.created_at.isoformat()
            }
            for m in messages_list
        ]
        self.cache_service.set_messages(session_id, messages_dict)
        
        logger.debug(f"Returned {len(messages_list)} messages from database")
        return messages_list
    
    def format_messages_for_ai(self, messages: List[Message]) -> List[Dict[str, str]]:
        """
        Convert Message objects to OpenAI API format
        
        Args:
            messages: List of Message objects
        
        Returns:
            List of dicts with 'role' and 'content'
        """
        formatted = []
        for msg in messages:
            role = 'user' if msg.author == 'user' else 'assistant'
            formatted.append({
                'role': role,
                'content': msg.message
            })
        return formatted
    
    def create_session_with_title(self, first_message: str) -> Session:
        """
        Create a new session with AI-generated title
        
        Args:
            first_message: User's first message
        
        Returns:
            New Session object
        """
        title = self.ai_service.generate_title(first_message)
        session = Session.objects.create(title=title)
        logger.info(f"Created new session {session.session_id}: {title}")
        return session
    
    def save_message(
        self, 
        session_id: int, 
        author: str, 
        message: str, 
        user_id: int,
        metadata: Optional[Dict] = None
    ) -> Message:
        """
        Save a message with optional metadata
        
        Args:
            session_id: Session ID
            author: 'user' or 'ai'
            message: Message content
            user_id: User ID
            metadata: Optional dict with tokens, response_time, etc.
        
        Returns:
            Saved Message object
        """
        msg_data = {
            'session_id': session_id,
            'author': author,
            'message': message,
            'user_id': user_id
        }
        
        # Add metadata if provided
        if metadata:
            msg_data['input_tokens'] = metadata.get('input_tokens', 0)
            msg_data['output_tokens'] = metadata.get('output_tokens', 0)
            msg_data['total_tokens'] = metadata.get('total_tokens', 0)
            msg_data['response_time_ms'] = metadata.get('response_time_ms', 0)
            msg_data['model_used'] = metadata.get('model', '')
        
        msg = Message.objects.create(**msg_data)
        
        # Invalidate cache
        self.cache_service.invalidate(session_id)
        
        logger.debug(f"Saved {author} message {msg.message_id} to session {session_id}")
        return msg
    def get_or_create_active_session(self, user_id: int) -> Tuple[Session, bool]:
        """
        Get user's most recent session or indicate new session needed
        
        Args:
            user_id: User ID
        
        Returns:
            Tuple of (Session or None, is_new)
            - is_new: True if should create new session, False if can continue existing
        """
        # Find user's most recent message
        last_message = Message.objects.filter(
            user_id=user_id
        ).order_by('-created_at').first()
        
        if last_message:
            # User has previous conversations - return most recent session
            return last_message.session, False
        else:
            # No previous conversations - will create new session
            return None, True
    
    def process_chat_message(
        self, 
        user_id: int, 
        message: str, 
        session_id: Optional[int] = None,
        force_new_session: bool = False
    ) -> Tuple[Session, Message, Message, bool]:
        """
        Main orchestration method for processing a chat message
        
        Flow:
        1. Determine session (new or continue)
        2. Retrieve conversation history (with caching)
        3. Token management (trim if needed)
        4. Get AI response
        5. Save messages with metadata
        
        Args:
            user_id: User ID
            message: User's message
            session_id: Specific session ID (optional)
            force_new_session: Force create new session
        
        Returns:
            Tuple of (Session, user_message, ai_message, is_new_session)
        """
        is_new_session = False
        
        # ============================================
        # STEP 1: Determine which session to use
        # ============================================
        if force_new_session or session_id is None:
            if force_new_session:
                # User explicitly wants new conversation
                session = self.create_session_with_title(message)
                conversation_history = []
                is_new_session = True
            else:
                # session_id not provided - try to continue last session
                existing_session, should_create_new = self.get_or_create_active_session(user_id)
                
                if should_create_new or existing_session is None:
                    # No previous session - create new
                    session = self.create_session_with_title(message)
                    conversation_history = []
                    is_new_session = True
                else:
                    # Continue existing session
                    session = existing_session
                    last_messages = self.get_last_messages(session.session_id, limit=20)
                    conversation_history = self.format_messages_for_ai(last_messages)
                    is_new_session = False
        else:
            # Specific session_id provided - use it
            session = Session.objects.get(session_id=session_id)
            last_messages = self.get_last_messages(session_id, limit=20)
            conversation_history = self.format_messages_for_ai(last_messages)
            is_new_session = False
        
        # ============================================
        # STEP 2: Add current user message
        # ============================================
        conversation_history.append({
            'role': 'user',
            'content': message
        })
        
        # ============================================
        # STEP 3: Token management
        # ============================================
        token_count = self.token_service.count_tokens(conversation_history)
        logger.info(f"Conversation tokens: {token_count}")
        
        # Trim if necessary
        if token_count > self.token_service.max_context_tokens:
            logger.warning(f"Token count {token_count} exceeds limit, trimming...")
            conversation_history = self.token_service.trim_messages(conversation_history)
            token_count = self.token_service.count_tokens(conversation_history)
            logger.info(f"After trimming: {token_count} tokens")
        
        # ============================================
        # STEP 4: Get AI response
        # ============================================
        ai_response = self.ai_service.generate_chat_response(conversation_history)
        
        # ============================================
        # STEP 5: Save messages with metadata
        # ============================================
        
        # Save user message
        user_message = self.save_message(
            session_id=session.session_id,
            author='user',
            message=message,
            user_id=user_id
        )
        
        # Save AI response with metadata
        ai_message = self.save_message(
            session_id=session.session_id,
            author='ai',
            message=ai_response['content'],
            user_id=user_id,
            metadata={
                'input_tokens': ai_response.get('input_tokens', 0),
                'output_tokens': ai_response.get('output_tokens', 0),
                'total_tokens': ai_response.get('total_tokens', 0),
                'response_time_ms': ai_response.get('response_time_ms', 0),
                'model': ai_response.get('model', '')
            }
        )
        
        # Log metrics
        if ai_response.get('success', True):
            cost = self.token_service.estimate_cost(
                ai_response.get('input_tokens', 0),
                ai_response.get('output_tokens', 0),
                ai_response.get('model')
            )
            logger.info(f"Request completed: {ai_response.get('total_tokens', 0)} tokens, "
                       f"${cost:.4f} cost, {ai_response.get('response_time_ms', 0)}ms")
        
        return session, user_message, ai_message, is_new_session
    
    def get_user_sessions(self, user_id: int) -> List[Session]:
        """
        Get all sessions for a specific user
        
        Args:
            user_id: User ID
        
        Returns:
            List of Session objects
        """
        session_ids = Message.objects.filter(
            user_id=user_id
        ).values_list('session_id', flat=True).distinct()
        
        return Session.objects.filter(
            session_id__in=session_ids
        ).order_by('-created_at')
    
    def get_session_messages(self, session_id: int) -> List[Message]:
        """
        Get all messages for a specific session
        
        Args:
            session_id: Session ID
        
        Returns:
            List of Message objects in chronological order
        """
        return Message.objects.filter(
            session_id=session_id
        ).order_by('created_at')


# Singleton instance
chat_service = ChatService()