# chatbot/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Session, Message
from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    SessionSerializer,
    SessionDetailSerializer,
    MessageSerializer
)
from .services.chat_service import chat_service
from rest_framework.permissions import IsAuthenticated
import logging

logger = logging.getLogger(__name__)


class SendMessageView(APIView):
    """
    Send a message to the chatbot and get AI response
    
    Features:
    ✓ Automatic session management
    ✓ Caching for fast responses
    ✓ Token management to prevent errors
    ✓ Rate limiting protection
    ✓ Comprehensive error handling
    """
    
    serializer_class = ChatRequestSerializer
    permission_classes = [IsAuthenticated]
    def post(self, request):
        """
        Send a message to chatbot
        
        Body:
        - message: String (required) - Your message
        - session_id: Integer (optional) - Continue specific session
        - new_session: Boolean (optional) - Force new conversation
        
        Returns:
        - session_id: Session ID (new or existing)
        - ai_message: AI's response
        - title: Session title
        - user_message_id: Your message ID
        - ai_message_id: AI message ID
        - created_at: Timestamp
        - is_new_session: Boolean
        """
        try:
            # Validate request
            serializer = ChatRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Invalid request', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extract data
            user_id = request.user.id
            message = serializer.validated_data['message']
            session_id = request.data.get('session_id', None)
            new_session = request.data.get('new_session', False)
            
            logger.info(f"User {user_id} sent message to session {session_id}")
            
            # Process message
            session, user_message, ai_message, is_new = chat_service.process_chat_message(
                user_id=user_id,
                message=message,
                session_id=session_id,
                force_new_session=new_session
            )
            
            # Format response
            response_data = {
                'session_id': session.session_id,
                'ai_message': ai_message.message,
                'title': session.title,
                'user_message_id': user_message.message_id,
                'ai_message_id': ai_message.message_id,
                'created_at': ai_message.created_at,
                'is_new_session': is_new
            }
            
            response_serializer = ChatResponseSerializer(data=response_data)
            if response_serializer.is_valid():
                return Response(
                    response_serializer.data,
                    status=status.HTTP_200_OK
                )
            else:
                logger.error(f"Response serialization failed: {response_serializer.errors}")
                return Response(
                    {'error': 'Failed to format response'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Session.DoesNotExist:
            logger.error(f"Session {session_id} not found")
            return Response(
                {'error': f'Session {session_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            logger.exception(f"Unexpected error in SendMessageView: {str(e)}")
            return Response(
                {
                    'error': 'An unexpected error occurred. Please try again.',
                    'message': 'If this persists, please contact support.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserSessionsView(APIView):
    """
    Get all chat sessions for the authenticated user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Retrieve all sessions for authenticated user
        
        Returns:
        - List of sessions with titles and message counts
        """
        try:
            user_id = request.user.id
            
            # Get sessions using ChatService
            sessions = chat_service.get_user_sessions(user_id)
            
            # Serialize and return
            serializer = SessionSerializer(sessions, many=True)
            
            logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
            
            return Response(
                {
                    'count': len(sessions),
                    'sessions': serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.exception(f"Error retrieving sessions: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve sessions. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SessionDetailView(APIView):
    """
    Get detailed information about a specific session including all messages
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        """
        Retrieve a specific session with all its messages
        
        Path Parameters:
        - session_id: Integer - The session ID to retrieve
        
        Returns:
        - Session details with all messages in chronological order
        """
        try:
            # Get the session
            session = get_object_or_404(Session, session_id=session_id)
            
            # Verify ownership (user must have at least one message in this session)
            first_message = Message.objects.filter(session_id=session_id).first()
            if first_message and first_message.user_id != request.user.id:
                return Response(
                    {'error': 'You do not have access to this session'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get all messages for this session
            messages = chat_service.get_session_messages(session_id)
            
            # Serialize session with messages
            serializer = SessionDetailSerializer(session)
            
            logger.info(f"Retrieved session {session_id} with {len(messages)} messages")
            
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.exception(f"Error retrieving session details: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve session details. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MessageHistoryView(APIView):
    """
    Get message history for a specific session
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Retrieve messages for a session
        
        Query Parameters:
        - session_id: Integer (required) - The session ID
        - limit: Integer (optional, default=20) - Number of recent messages
        
        Returns:
        - List of messages with metadata
        """
        try:
            # Get parameters
            session_id = request.query_params.get('session_id', None)
            limit = int(request.query_params.get('limit', 20))
            
            if session_id is None:
                return Response(
                    {'error': 'session_id query parameter is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            session_id = int(session_id)
            
            # Check if session exists
            if not Session.objects.filter(session_id=session_id).exists():
                return Response(
                    {'error': 'Session not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify ownership
            first_message = Message.objects.filter(session_id=session_id).first()
            if first_message and first_message.user_id != request.user.id:
                return Response(
                    {'error': 'You do not have access to this session'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get messages
            if limit:
                messages = chat_service.get_last_messages(session_id, limit)
            else:
                messages = chat_service.get_session_messages(session_id)
            
            # Serialize and return
            serializer = MessageSerializer(messages, many=True)
            
            return Response(
                {
                    'session_id': session_id,
                    'message_count': len(messages),
                    'messages': serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        except ValueError:
            return Response(
                {'error': 'Invalid session_id or limit parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.exception(f"Error retrieving message history: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve messages. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteSessionView(APIView):
    """
    Delete a session and all its messages
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, session_id):
        """
        Delete a session
        
        Path Parameters:
        - session_id: Integer - The session ID to delete
        
        Deletes the session and all associated messages (CASCADE)
        """
        try:
            # Get the session
            session = get_object_or_404(Session, session_id=session_id)
            
            # Verify ownership
            first_message = Message.objects.filter(session_id=session_id).first()
            if first_message and first_message.user_id != request.user.id:
                return Response(
                    {'error': 'You do not have permission to delete this session'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Invalidate cache
            chat_service.cache_service.invalidate(session_id)
            
            # Delete session (messages deleted automatically due to CASCADE)
            session.delete()
            
            logger.info(f"User {request.user.id} deleted session {session_id}")
            
            return Response(
                {'message': f'Session {session_id} deleted successfully'},
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.exception(f"Error deleting session: {str(e)}")
            return Response(
                {'error': 'Failed to delete session. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )