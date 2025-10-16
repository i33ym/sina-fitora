# chatbot/middleware/rate_limit.py

from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status
import time
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Simple rate limiting middleware
    
    Protection against:
    - API abuse
    - DDoS attacks
    - Runaway scripts
    - Cost overruns
    
    Rules:
    - 30 requests per minute per user
    - 100 requests per hour per user
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = {
            'minute': {'limit': 30, 'window': 60},
            'hour': {'limit': 100, 'window': 3600}
        }
    
    def __call__(self, request):
        # Only apply to chatbot API endpoints
        if request.path.startswith('/api/chatbot/'):
            
            # Get user identifier
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_id = str(request.user.id)
            else:
                # Fallback to IP address for unauthenticated requests
                user_id = self.get_client_ip(request)
            
            # Check rate limits
            is_allowed, retry_after = self.check_rate_limit(user_id)
            
            if not is_allowed:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return JsonResponse({
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': retry_after
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        response = self.get_response(request)
        return response
    
    def check_rate_limit(self, user_id: str) -> tuple:
        """
        Check if user has exceeded rate limits
        
        Args:
            user_id: User identifier
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        current_time = int(time.time())
        
        for period, config in self.rate_limits.items():
            cache_key = f"rate_limit:{user_id}:{period}"
            
            # Get current request count
            data = cache.get(cache_key)
            
            if data is None:
                # First request in this window
                cache.set(cache_key, {
                    'count': 1,
                    'start_time': current_time
                }, timeout=config['window'])
            else:
                # Check if window has expired
                if current_time - data['start_time'] >= config['window']:
                    # Window expired, reset
                    cache.set(cache_key, {
                        'count': 1,
                        'start_time': current_time
                    }, timeout=config['window'])
                else:
                    # Within window, increment count
                    if data['count'] >= config['limit']:
                        # Rate limit exceeded
                        retry_after = config['window'] - (current_time - data['start_time'])
                        return False, retry_after
                    
                    data['count'] += 1
                    cache.set(cache_key, data, timeout=config['window'])
        
        return True, 0
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip