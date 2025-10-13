# chatbot/token_service.py

import tiktoken
from typing import List, Dict

class TokenService:
    def __init__(self, model: str = "gpt-4"):
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        self.max_tokens = 8000  # Leave room for response
    
    def count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in message list"""
        num_tokens = 0
        
        for message in messages:
            num_tokens += 4  # Message formatting
            for key, value in message.items():
                num_tokens += len(self.encoding.encode(str(value)))
        
        num_tokens += 2  # Assistant priming
        return num_tokens
    
    def trim_messages_to_fit(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int = None
    ) -> List[Dict[str, str]]:
        """
        Trim messages to fit within token limit.
        Always keeps the most recent messages.
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
        
        current_tokens = self.count_tokens(messages)
        
        if current_tokens <= max_tokens:
            return messages
        
        # Remove oldest messages until we fit
        while len(messages) > 1 and current_tokens > max_tokens:
            messages.pop(0)  # Remove oldest
            current_tokens = self.count_tokens(messages)
        
        return messages
    
    def get_conversation_summary_prompt(self, old_messages: List[Dict]) -> str:
        """Generate prompt for summarizing old context"""
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in old_messages
        ])
        
        return f"""Summarize this conversation concisely (2-3 sentences):

{conversation_text}

Summary:"""