# chatbot/services/cache_service.py

import redis
import json
from django.conf import settings  # ⚠️ USE DJANGO SETTINGS
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Redis caching using Django settings"""
    
    def __init__(self):
        try:
            # ⚠️ READ FROM DJANGO SETTINGS
            redis_config = {
                'host': settings.REDIS_HOST,
                'port': settings.REDIS_PORT,
                'db': settings.REDIS_DB,
                'decode_responses': True,
                'socket_connect_timeout': 5
            }
            
            # Add password if exists
            if settings.REDIS_PASSWORD:
                redis_config['password'] = settings.REDIS_PASSWORD
            
            self.redis_client = redis.Redis(**redis_config)
            
            # Test connection
            self.redis_client.ping()
            self.is_available = True
            logger.info("✅ Redis connection established")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e}. Falling back to database only.")
            self.is_available = False
        
        # ⚠️ READ TTL FROM DJANGO SETTINGS
        self.cache_ttl = settings.CHATBOT_CACHE_TTL
    
    def _get_key(self, session_id: int) -> str:
        """Generate cache key for session"""
        return f"chatbot:session:{session_id}:messages"
    
    def get_messages(self, session_id: int) -> Optional[List[Dict]]:
        """Retrieve cached messages for a session"""
        if not self.is_available:
            return None
        
        try:
            key = self._get_key(session_id)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                logger.debug(f"Cache HIT for session {session_id}")
                return json.loads(cached_data)
            
            logger.debug(f"Cache MISS for session {session_id}")
            return None
            
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None
    
    def set_messages(self, session_id: int, messages: List[Dict]) -> bool:
        """Cache messages for a session"""
        if not self.is_available:
            return False
        
        try:
            key = self._get_key(session_id)
            self.redis_client.setex(
                key,
                self.cache_ttl,
                json.dumps(messages)
            )
            logger.debug(f"Cached {len(messages)} messages for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Cache write error: {e}")
            return False
    
    def invalidate(self, session_id: int) -> bool:
        """Invalidate cache for a session"""
        if not self.is_available:
            return False
        
        try:
            key = self._get_key(session_id)
            self.redis_client.delete(key)
            logger.debug(f"Invalidated cache for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return False
    
    def extend_ttl(self, session_id: int) -> bool:
        """Extend TTL for active sessions"""
        if not self.is_available:
            return False
        
        try:
            key = self._get_key(session_id)
            self.redis_client.expire(key, self.cache_ttl)
            return True
            
        except Exception as e:
            logger.error(f"TTL extension error: {e}")
            return False


# Singleton instance
cache_service = CacheService()