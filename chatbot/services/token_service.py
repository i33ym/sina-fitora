# chatbot/services/token_service.py

import tiktoken
from django.conf import settings  # ⚠️ USE DJANGO SETTINGS
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class TokenService:
    """Token counting and management using Django settings"""
    
    def __init__(self, model: str = None):
        """Initialize token counter"""
        
        # ⚠️ READ MODEL FROM DJANGO SETTINGS
        if model is None:
            model = settings.OPENAI_MODEL
        
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning(f"Model {model} not found, using cl100k_base encoding")
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Model-specific limits
        self.model_limits = {
            'gpt-4': 8192,
            'gpt-4-32k': 32768,
            'gpt-4-turbo-preview': 128000,
            'gpt-3.5-turbo': 4096,
            'gpt-3.5-turbo-16k': 16384,
        }
        
        self.model = model
        self.max_tokens = self.model_limits.get(model, 8192)
        
        # ⚠️ READ FROM DJANGO SETTINGS
        # Reserve tokens for response
        self.reserved_for_response = 1000
        self.max_context_tokens = min(
            settings.CHATBOT_MAX_TOKENS,
            self.max_tokens
        ) - self.reserved_for_response
        
        logger.info(f"TokenService initialized: model={model}, max_context={self.max_context_tokens}")
    
    # ... rest of the methods stay the same ...
    
    def count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in message list"""
        num_tokens = 0
        
        for message in messages:
            num_tokens += 4
            for key, value in message.items():
                try:
                    num_tokens += len(self.encoding.encode(str(value)))
                except Exception as e:
                    logger.error(f"Token encoding error: {e}")
                    num_tokens += len(str(value)) // 4
        
        num_tokens += 2
        return num_tokens
    
    def trim_messages(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int = None
    ) -> List[Dict[str, str]]:
        """Trim messages to fit within token limit"""
        if max_tokens is None:
            max_tokens = self.max_context_tokens
        
        current_tokens = self.count_tokens(messages)
        
        if current_tokens <= max_tokens:
            logger.debug(f"Messages within limit: {current_tokens}/{max_tokens} tokens")
            return messages
        
        system_message = None
        conversation_messages = messages
        
        if messages and messages[0].get('role') == 'system':
            system_message = messages[0]
            conversation_messages = messages[1:]
        
        trimmed = []
        current_tokens = 0
        
        if system_message:
            system_tokens = self.count_tokens([system_message])
            current_tokens = system_tokens
            trimmed.append(system_message)
        
        for msg in reversed(conversation_messages):
            msg_tokens = self.count_tokens([msg])
            
            if current_tokens + msg_tokens <= max_tokens:
                trimmed.insert(1 if system_message else 0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        removed_count = len(messages) - len(trimmed)
        if removed_count > 0:
            logger.info(f"Trimmed {removed_count} messages to fit token limit")
        
        return trimmed
    
    def estimate_cost(self, input_tokens: int, output_tokens: int, model: str = None) -> float:
        """Estimate API cost"""
        if model is None:
            model = self.model
        
        pricing = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-32k': {'input': 0.06, 'output': 0.12},
            'gpt-4-turbo-preview': {'input': 0.01, 'output': 0.03},
            'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
            'gpt-3.5-turbo-16k': {'input': 0.003, 'output': 0.004},
        }
        
        model_pricing = pricing.get(model, pricing['gpt-4-turbo-preview'])
        
        input_cost = (input_tokens / 1000) * model_pricing['input']
        output_cost = (output_tokens / 1000) * model_pricing['output']
        
        return input_cost + output_cost


# Singleton instance
token_service = TokenService()