from django.contrib import admin
from .models import Session, Message


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """
    Admin interface for Session model.
    Customize how sessions are displayed and managed in Django admin.
    """
    
    # Columns to display in the list view
    list_display = [
        'session_id', 
        'title', 
        'message_count',
        'created_at'
    ]
    
    # Add filters in the sidebar
    list_filter = [
        'created_at',
    ]
    
    # Add search functionality
    search_fields = [
        'title',
        'session_id'
    ]
    
    # Default ordering (newest first)
    ordering = ['-created_at']
    
    # Read-only fields (can't edit these)
    readonly_fields = [
        'session_id',
        'created_at',
        'message_count'
    ]
    
    # Fields to show when viewing/editing a session
    fields = [
        'session_id',
        'title',
        'created_at',
        'message_count'
    ]
    
    # Custom method to show message count
    def message_count(self, obj):
        """Display the number of messages in this session"""
        return obj.messages.count()
    
    message_count.short_description = 'Messages'  # Column header name


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin interface for Message model.
    Customize how messages are displayed and managed in Django admin.
    """
    
    # Columns to display in the list view
    list_display = [
        'message_id',
        'session_link',
        'author',
        'message_preview',
        'user_id',
        'created_at'
    ]
    
    # Add filters in the sidebar
    list_filter = [
        'author',
        'created_at',
        'session'
    ]
    
    # Add search functionality
    search_fields = [
        'message',
        'user_id',
        'session__title'  # Search by session title
    ]
    
    # Default ordering (newest first)
    ordering = ['-created_at']
    
    # Read-only fields
    readonly_fields = [
        'message_id',
        'session',
        'author',
        'message',
        'user_id',
        'created_at'
    ]
    
    # Fields to show when viewing a message
    fields = [
        'message_id',
        'session',
        'author',
        'user_id',
        'message',
        'created_at'
    ]
    
    # Make all fields read-only (prevent editing)
    def has_add_permission(self, request):
        """Disable adding messages through admin (they should come from API)"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing messages through admin"""
        return False
    
    # Custom method to show message preview
    def message_preview(self, obj):
        """Display first 50 characters of the message"""
        if len(obj.message) > 50:
            return obj.message[:50] + '...'
        return obj.message
    
    message_preview.short_description = 'Message Preview'
    
    # Custom method to make session clickable
    def session_link(self, obj):
        """Create a clickable link to the session"""
        from django.urls import reverse
        from django.utils.html import format_html
        
        url = reverse('admin:chatbot_session_change', args=[obj.session.session_id])
        return format_html('<a href="{}">{}</a>', url, obj.session.title)
    
    session_link.short_description = 'Session'
    session_link.admin_order_field = 'session__title'  # Allow sorting by session title