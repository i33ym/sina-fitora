# chatbot/services/ai_service.py

from openai import OpenAI
from django.conf import settings  # ⚠️ USE DJANGO SETTINGS
from typing import List, Dict
import time
import logging

logger = logging.getLogger(__name__)


class AIService:
    """OpenAI API integration using Django settings"""
    
    def __init__(self):
        # ⚠️ READ FROM DJANGO SETTINGS
        api_key = settings.OPENAI_API_KEY
        
        if not api_key:
            logger.error("❌ OPENAI_API_KEY not set in settings!")
            raise ValueError("OPENAI_API_KEY is required")
        
        self.client = OpenAI(api_key=api_key)
        self.model = settings.OPENAI_MODEL
        self.max_retries = 3
        self.retry_delay = 2
        
        logger.info(f"✅ AIService initialized with model: {self.model}")
    
    def generate_chat_response(self, messages: List[Dict[str, str]]) -> Dict:
        """Generate AI response with error handling"""
        
        system_prompt = {
            "role": "system",
            "content": """You are a helpful assistant for Fitora. 
            You can only answer questions about meal planning, nutrition, fitness, and health. 
            If the user asks about unrelated topics, politely decline and redirect them 
            to ask about fitness and nutrition topics."""
        }
        
        messages_with_system = [system_prompt] + messages
        
        start_time = time.time()
        attempt = 0
        last_error = None
        
        while attempt < self.max_retries:
            try:
                logger.debug(f"Calling OpenAI API (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages_with_system,
                    temperature=0.7,
                    max_tokens=1000,
                )
                
                response_time_ms = int((time.time() - start_time) * 1000)
                
                logger.info(f"✅ OpenAI response received in {response_time_ms}ms")
                
                return {
                    'success': True,
                    'content': response.choices[0].message.content,
                    'input_tokens': response.usage.prompt_tokens,
                    'output_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens,
                    'response_time_ms': response_time_ms,
                    'model': self.model,
                    'finish_reason': response.choices[0].finish_reason
                }
            
            except Exception as e:
                attempt += 1
                last_error = str(e)
                logger.error(f"❌ OpenAI API error (attempt {attempt}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    return {
                        'success': False,
                        'content': "I'm having trouble connecting right now. Please try again in a moment.",
                        'error': last_error,
                        'response_time_ms': response_time_ms,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'total_tokens': 0,
                        'model': self.model,
                        'finish_reason': 'error'
                    }
    
    def generate_title(self, first_message: str) -> str:
        """Generate a short title for a new conversation"""
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
            logger.error(f"Title generation error: {e}")
            words = first_message.split()[:5]
            return ' '.join(words) + "..." if len(words) == 5 else ' '.join(words)


# Singleton instance
ai_service = AIService()