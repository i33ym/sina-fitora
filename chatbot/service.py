# Update chatbot/service.py
from .services import ai_service, cache_service
from .models import Message
from typing import List
class ChatService:
    def __init__(self):
        self.ai_service = ai_service
        self.cache_service = cache_service  # ADD THIS
    
    def get_last_messages(self, session_id: int, limit: int = 20) -> List[Message]:
        """Retrieve messages with caching"""
        # Try cache first
        cached = self.cache_service.get_session_messages(session_id)
        
        if cached:
            # Deserialize from cache
            self.cache_service.extend_ttl(session_id)
            return [Message(**msg) for msg in cached[:limit]]
        
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
        self.cache_service.cache_session_messages(session_id, messages_dict)
        
        return messages_list
    
    def save_message(self, session_id: int, author: str, message: str, user_id: int) -> Message:
        """Save message and invalidate cache"""
        msg = Message.objects.create(
            session_id=session_id,
            author=author,
            message=message,
            user_id=user_id
        )
        
        # Invalidate cache so next request gets fresh data
        self.cache_service.invalidate_session(session_id)
        
        return msg