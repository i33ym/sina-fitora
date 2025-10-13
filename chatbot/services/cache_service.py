import redis
import json
from django.conf import settings
from typing import List, Dict, Optional

class CacheService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )
        self.cache_ttl = 3600  # 1 hour
    
    def get_session_messages(self, session_id: int) -> Optional[List[Dict]]:
        """Get cached messages for a session"""
        key = f"session:{session_id}:messages"
        cached = self.redis_client.get(key)
        
        if cached:
            return json.loads(cached)
        return None
    
    def cache_session_messages(self, session_id: int, messages: List[Dict]):
        """Cache session messages"""
        key = f"session:{session_id}:messages"
        self.redis_client.setex(
            key,
            self.cache_ttl,
            json.dumps(messages)
        )
    
    def invalidate_session(self, session_id: int):
        """Clear cache when new message added"""
        key = f"session:{session_id}:messages"
        self.redis_client.delete(key)
    
    def extend_ttl(self, session_id: int):
        """Keep active conversations cached longer"""
        key = f"session:{session_id}:messages"
        self.redis_client.expire(key, self.cache_ttl)