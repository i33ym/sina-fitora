# chatbot/models.py

from django.db import models
from django.utils import timezone

class Session(models.Model):
    session_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, help_text="Auto-generated conversation title")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'session'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Session {self.session_id}: {self.title}"


class Message(models.Model):
    """
    Enhanced Message model with metadata for production monitoring
    """
    
    AUTHOR_CHOICES = [
        ('user', 'User'),
        ('ai', 'AI'),
    ]
    
    message_id = models.AutoField(primary_key=True)
    session = models.ForeignKey(
        Session, 
        on_delete=models.CASCADE,
        related_name='messages',
        db_column='session_id'
    )
    author = models.CharField(
        max_length=10, 
        choices=AUTHOR_CHOICES,
        help_text="Who sent this message: user or ai"
    )
    message = models.TextField(help_text="The actual message content")
    user_id = models.IntegerField(
        help_text="User ID from the existing system"
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    # ⚠️ NEW: Metadata fields for monitoring
    input_tokens = models.IntegerField(default=0, help_text="Tokens in request")
    output_tokens = models.IntegerField(default=0, help_text="Tokens in response")
    total_tokens = models.IntegerField(default=0, help_text="Total tokens used")
    response_time_ms = models.IntegerField(default=0, help_text="AI response time in milliseconds")
    model_used = models.CharField(max_length=50, default='', blank=True, help_text="AI model used")
    
    class Meta:
        db_table = 'message'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['user_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        preview = self.message[:50] + "..." if len(self.message) > 50 else self.message
        return f"{self.author}: {preview}"