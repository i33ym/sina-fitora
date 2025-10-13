from django.db import models
from django.utils import timezone

class Session(models.Model):
    session_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, help_text="Auto-generated conversation title")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'session'
        ordering = ['-created_at']  # Newest sessions first
    
    def __str__(self):
        return f"Session {self.session_id}: {self.title}"
    
class Message(models.Model):
    """
    Represents a single message in a chat session.
    Can be from either 'user' or 'ai'.
    """
    
    AUTHOR_CHOICES = [
        ('user', 'User'),
        ('ai', 'AI'),
    ]
    
    message_id = models.AutoField(primary_key=True)
    session = models.ForeignKey(
        Session, 
        on_delete=models.CASCADE,  # Delete messages when session is deleted
        related_name='messages',    # Access messages via session.messages.all()
        db_column='session_id'
    )
    author = models.CharField(
        max_length=10, 
        choices=AUTHOR_CHOICES,
        help_text="Who sent this message: user or ai"
    )
    message = models.TextField(help_text="The actual message content")
    user_id = models.IntegerField(
        help_text="User ID from the existing system (not a foreign key)"
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'message'
        ordering = ['created_at']  # Oldest messages first (chronological order)
        indexes = [
            models.Index(fields=['session', 'created_at']),  # Fast lookup for message history
            models.Index(fields=['user_id']),                 # Fast lookup by user
        ]
    
    def __str__(self):
        preview = self.message[:50] + "..." if len(self.message) > 50 else self.message
        return f"{self.author}: {preview}"# chatbot/serializers.py

from rest_framework import serializers
from .models import Session, Message


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""
    class Meta:
        model = Message
        fields = ['message_id', 'session_id', 'author', 'message', 'user_id', 'created_at']
        read_only_fields = ['message_id', 'created_at']
    
    session_id = serializers.IntegerField(source='session.session_id', read_only=True)


class SessionSerializer(serializers.ModelSerializer):
    """Serializer for Session model with message count."""
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = ['session_id', 'title', 'created_at', 'message_count']
        read_only_fields = ['session_id', 'created_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()


class SessionDetailSerializer(serializers.ModelSerializer):
    """Detailed session serializer with all messages."""
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Session
        fields = ['session_id', 'title', 'created_at', 'messages']
        read_only_fields = ['session_id', 'created_at']


class ChatRequestSerializer(serializers.Serializer):
    """
    Request serializer for sending messages to chatbot.
    
    session_id is now truly optional:
    - Not provided or null: Auto-continue last session OR create new if none exists
    - Provided: Continue that specific session
    """
    
    message = serializers.CharField(
        required=True,
        max_length=5000,
        help_text="Your message to the chatbot",
        style={'base_template': 'textarea.html'}
    )
    
    def validate_message(self, value):
        """Ensure message is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()
    
    def validate_session_id(self, value):
        """Validate session exists if provided"""
        if value is not None and value != 0:  # Allow 0 or null
            if not Session.objects.filter(session_id=value).exists():
                raise serializers.ValidationError("Session does not exist")
        return None if value == 0 else value  # Convert 0 to None


class ChatResponseSerializer(serializers.Serializer):
    """Response serializer for chatbot messages."""
    session_id = serializers.IntegerField(
        help_text="Session ID (new or existing)"
    )
    ai_message = serializers.CharField(
        help_text="AI's response to your message"
    )
    title = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Session title"
    )
    user_message_id = serializers.IntegerField(
        help_text="ID of your saved message"
    )
    ai_message_id = serializers.IntegerField(
        help_text="ID of the AI's saved message"
    )
    created_at = serializers.DateTimeField(
        help_text="Timestamp of the response"
    )
    is_new_session = serializers.BooleanField(
        help_text="True if this is a new conversation, False if continuing"
    )


class MessageHistorySerializer(serializers.Serializer):
    """Serializer for formatting conversation history."""
    role = serializers.CharField(help_text="'user' or 'assistant'")
    content = serializers.CharField(help_text="Message content")