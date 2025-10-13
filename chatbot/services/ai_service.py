from openai import OpenAI
from django.conf import settings
from django.utils import timezone
from models import Session, Message
from typing import List, Dict, Optional, Tuple
from token_service import TokenService


class AIService:
    """
    Handles all OpenAI API interactions.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4-turbo-preview')
        self.token_service = TokenService(model=self.model)
    
    def generate_chat_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate AI response based on conversation history."""

        system_prompt = {
            "role": "system",
            "content": "You are a helpful assistant for Fitora. You can only answer questions about his or her meal and diary questions. If the user asks about unrelated topics, politely decline and redirect them to ask about the allowed topics."
        }

        # Insert system message at the start
        messages_with_system = [system_prompt] + messages
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_with_system,
                temperature=0.7,
                max_tokens=1000,
            )
            return response.choices[0].message.content
        
        except Exception as e:
            print(f"OpenAI API Error: {str(e)}")
            raise Exception(f"Failed to generate AI response: {str(e)}")
    
    def generate_title(self, first_message: str) -> str:
        """Generate a short title for a new conversation."""
        try:
            prompt = [
                {
                    "role": "system",
                    "content": "Generate a short, descriptive title (maximum 5 words) for a conversation that starts with the following message. Only return the title, nothing else."
                },
                {
                    "role": "user",
                    "content": first_message
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=prompt,
                temperature=0.5,
                max_tokens=20,
            )
            
            title = response.choices[0].message.content.strip()
            return title[:50] if len(title) > 50 else title
        
        except Exception as e:
            print(f"Title generation error: {str(e)}")
            return "New Conversation"


class ChatService:
    """
    Handles all chat business logic.
    """
    
    def __init__(self):
        self.ai_service = AIService()
    
    def get_last_messages(self, session_id: int, limit: int = 20) -> List[Message]:
        """Retrieve the last N messages from a session."""
        messages = Message.objects.filter(
            session_id=session_id
        ).order_by('-created_at')[:limit]
        
        return list(reversed(messages))
    
    def format_messages_for_ai(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert Message objects to OpenAI API format."""
        formatted = []
        for msg in messages:
            role = 'user' if msg.author == 'user' else 'assistant'
            formatted.append({
                'role': role,
                'content': msg.message
            })
        return formatted
    
    def create_session_with_title(self, first_message: str) -> Session:
        """Create a new session with AI-generated title."""
        title = self.ai_service.generate_title(first_message)
        session = Session.objects.create(title=title)
        return session
    
    def save_message(
        self, 
        session_id: int, 
        author: str, 
        message: str, 
        user_id: int
    ) -> Message:
        """Save a message to the database."""
        return Message.objects.create(
            session_id=session_id,
            author=author,
            message=message,
            user_id=user_id
        )
    
    def get_or_create_active_session(self, user_id: int) -> Tuple[Session, bool]:
        """
        Get user's most recent session or create new one.
        
        Returns:
            Tuple of (Session, is_new)
            - is_new: True if created new session, False if using existing
        """
        # Find user's most recent session
        last_message = Message.objects.filter(
            user_id=user_id
        ).order_by('-created_at').first()
        
        if last_message:
            # User has previous conversations - return most recent session
            return last_message.session, False
        else:
            # No previous conversations - will create new session later
            return None, True
    
    def process_chat_message(
        self, 
        user_id: int, 
        message: str, 
        session_id: Optional[int] = None,
        force_new_session: bool = False
    ) -> Tuple[Session, Message, Message, bool]:
        """
        Main orchestration method for processing a chat message.
        
        Args:
            user_id: User ID from existing system
            message: User's message
            session_id: Specific session ID (optional)
            force_new_session: Force create new session even if user has existing ones
        
        Returns:
            Tuple of (Session, user_message, ai_message, is_new_session)
        """
        
        is_new_session = False
        
        # Step 1: Determine which session to use
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
        
        # Step 2: Add current user message to conversation
        conversation_history.append({
            'role': 'user',
            'content': message
        })
        
        # Step 3: Get AI response
        ai_response = self.ai_service.generate_chat_response(conversation_history)
        
        # Step 4: Save both messages to database
        user_message = self.save_message(
            session_id=session.session_id,
            author='user',
            message=message,
            user_id=user_id
        )
        
        ai_message = self.save_message(
            session_id=session.session_id,
            author='ai',
            message=ai_response,
            user_id=user_id
        )
        
        return session, user_message, ai_message, is_new_session
    
    def get_user_sessions(self, user_id: int) -> List[Session]:
        """Get all sessions for a specific user."""
        session_ids = Message.objects.filter(
            user_id=user_id
        ).values_list('session_id', flat=True).distinct()
        
        return Session.objects.filter(
            session_id__in=session_ids
        ).order_by('-created_at')
    
    def get_session_messages(self, session_id: int) -> List[Message]:
        """Get all messages for a specific session."""
        return Message.objects.filter(
            session_id=session_id
        ).order_by('created_at')