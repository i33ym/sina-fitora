# chatbot/serializers.py

from rest_framework import serializers
from .models import Session, Message


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model with all metadata
    """
    session_id = serializers.IntegerField(source='session.session_id', read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'message_id',
            'session_id',
            'author',
            'message',
            'user_id',
            'created_at',
            # Metadata fields
            'input_tokens',
            'output_tokens',
            'total_tokens',
            'response_time_ms',
            'model_used',
        ]
        read_only_fields = [
            'message_id',
            'created_at',
            'input_tokens',
            'output_tokens',
            'total_tokens',
            'response_time_ms',
            'model_used',
        ]


class SessionSerializer(serializers.ModelSerializer):
    """
    Serializer for Session list view with message count
    """
    message_count = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = [
            'session_id',
            'title',
            'created_at',
            'message_count',
            'last_message_at',
        ]
        read_only_fields = ['session_id', 'created_at']
    
    def get_message_count(self, obj):
        """Get total number of messages in session"""
        return obj.messages.count()
    
    def get_last_message_at(self, obj):
        """Get timestamp of last message"""
        last_message = obj.messages.order_by('-created_at').first()
        return last_message.created_at if last_message else None


class SessionDetailSerializer(serializers.ModelSerializer):
    """
    Detailed session serializer with all messages
    """
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    total_tokens = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = [
            'session_id',
            'title',
            'created_at',
            'message_count',
            'total_tokens',
            'messages',
        ]
        read_only_fields = ['session_id', 'created_at']
    
    def get_message_count(self, obj):
        """Get total number of messages"""
        return obj.messages.count()
    
    def get_total_tokens(self, obj):
        """Get total tokens used in this session"""
        return sum(msg.total_tokens for msg in obj.messages.all())


class ChatRequestSerializer(serializers.Serializer):
    """
    Request serializer for sending messages to chatbot
    """
    message = serializers.CharField(
        required=True,
        max_length=5000,
        help_text="Your message to the chatbot",
        error_messages={
            'required': 'Message is required',
            'max_length': 'Message is too long (max 5000 characters)',
        }
    )
    
    """session_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Session ID to continue conversation (optional)"
    )
    
    new_session = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Force create new session"
    )"""
    
    def validate_message(self, value):
        """Ensure message is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()
    
    def validate_session_id(self, value):
        """Validate session exists if provided"""
        if value is not None and value != 0:
            from .models import Session
            if not Session.objects.filter(session_id=value).exists():
                raise serializers.ValidationError("Session does not exist")
        return None if value == 0 else value


class ChatResponseSerializer(serializers.Serializer):
    """
    Response serializer for chatbot messages
    """
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
        help_text="True if this is a new conversation"
    )
    
    # Optional metadata
    tokens_used = serializers.IntegerField(
        required=False,
        help_text="Total tokens used for this response"
    )
    
    response_time_ms = serializers.IntegerField(
        required=False,
        help_text="Response time in milliseconds"
    )


class MessageHistorySerializer(serializers.Serializer):
    """
    Serializer for formatting conversation history
    """
    role = serializers.CharField(help_text="'user' or 'assistant'")
    content = serializers.CharField(help_text="Message content")
    timestamp = serializers.DateTimeField(required=False)


class SessionStatsSerializer(serializers.Serializer):
    """
    Statistics for a session
    """
    session_id = serializers.IntegerField()
    title = serializers.CharField()
    created_at = serializers.DateTimeField()
    message_count = serializers.IntegerField()
    total_tokens = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=4)
    avg_response_time = serializers.IntegerField()
    user_messages = serializers.IntegerField()
    ai_messages = serializers.IntegerField()