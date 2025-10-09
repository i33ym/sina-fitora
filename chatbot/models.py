from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class ChatSession(models.Model):
    """Chat session modeli"""
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        verbose_name='Foydalanuvchi'
    )
    
    title = models.CharField(
        max_length=255, 
        default="Yangi Suhbat",
        verbose_name='Sarlavha'
    )
    
    AI_MODEL_CHOICES = [
        ('gpt-4', 'GPT-4'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
        ('claude-3-opus', 'Claude 3 Opus'),
        ('claude-3-sonnet', 'Claude 3 Sonnet'),
    ]
    ai_model = models.CharField(
        max_length=20,
        choices=AI_MODEL_CHOICES,
        default='gpt-4',
        verbose_name='AI Model'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Yangilangan')
    is_active = models.BooleanField(default=True, verbose_name='Aktiv')
    
    class Meta:
        ordering = ['-updated_at']
        db_table = 'chat_sessions'
        verbose_name = 'Chat Session'
        verbose_name_plural = 'Chat Sessions'
        indexes = [
            models.Index(fields=['-updated_at']),
            models.Index(fields=['user', '-updated_at']),
        ]
        
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    @property
    def message_count(self):
        """Xabarlar soni"""
        return self.messages.count()


class Message(models.Model):
    """Xabar modeli"""
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Session'
    )
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES,
        verbose_name='Rol'
    )
    content = models.TextField(verbose_name='Matn')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan')
    tokens_used = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name='Token soni'
    )
    
    class Meta:
        ordering = ['created_at']
        db_table = 'chat_messages'
        verbose_name = 'Xabar'
        verbose_name_plural = 'Xabarlar'
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]
        
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."