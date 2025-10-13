from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Session, Message
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    SessionSerializer,
    SessionDetailSerializer,
    MessageSerializer
)
from django.db.models import Q
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.http import StreamingHttpResponse
import json
import time
from .service import ChatService
from rest_framework.permissions import IsAuthenticated

permission_classes = [IsAuthenticated]
@method_decorator(ratelimit(key='user', rate='30/m', method='POST'), name='dispatch')
class SendMessageView(APIView):
    """
    Send a message to the chatbot and get AI response.
    
    session_id is optional:
    - If not provided: Automatically continues last session or creates new one
    - If provided: Continues that specific session
    - If new_session=true: Forces new conversation
    """
    
    serializer_class = ChatRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Send a message to chatbot.
        
        Body:
        - user_id: Integer (required)
        - message: String (required)
        - session_id: Integer (optional) - specific session to continue
        - new_session: Boolean (optional) - force new conversation
        """
        # Validate request
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract data
        user_id = request.user.id
        message = serializer.validated_data['message']
        session_id = serializer.data.get('session_id', None)
        new_session = serializer.data.get('new_session', False)
        
        # Process message
        try:
            chat_service = ChatService()
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
                return Response(
                    {'error': 'Failed to format response'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Session.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

permission_classes = [IsAuthenticated]
class UserSessionsView(APIView):
    """
    Get all chat sessions for a specific user.
    """
    permission_classes = [IsAuthenticated]
    def get(self, request):
        """
        Retrieve all sessions for a user.
        
        Query Parameters:
        - user_id: Integer (required) - User ID from your existing system
        
        Returns list of sessions with titles and message counts.
        """
        # Step 1: Get user_id from query parameters
        user_id = request.user.id
        
        if user_id is None:
            return Response(
                {'error': 'user_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_id = int(user_id)
        except ValueError:
            return Response(
                {'error': 'user_id must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Step 2: Get sessions using ChatService
        try:
            chat_service = ChatService()
            sessions = chat_service.get_user_sessions(user_id)
            
            # Step 3: Serialize and return
            serializer = SessionSerializer(sessions, many=True)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve sessions: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


permission_classes = [IsAuthenticated]
class SessionDetailView(APIView):
    """
    Get detailed information about a specific session including all messages.
    """
    def get(self, request, session_id):
        """
        Retrieve a specific session with all its messages.
        
        Path Parameters:
        - session_id: Integer (required) - The session ID to retrieve
        
        Returns session details with all messages in chronological order.
        """
        # Step 1: Get the session
        session = get_object_or_404(Session, session_id=session_id)
        
        # Step 2: Get all messages for this session
        try:
            chat_service = ChatService()
            messages = chat_service.get_session_messages(session_id)
            
            # Step 3: Serialize session with messages
            serializer = SessionDetailSerializer(session)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve session details: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MessageHistoryView(APIView):
    """
    Get message history for a specific session.
    """
    
    def get(self, request):
        """
        Retrieve messages for a session.
        
        Query Parameters:
        - session_id: Integer (required) - The session ID
        - limit: Integer (optional, default=20) - Number of recent messages to retrieve
        
        Returns list of messages with metadata.
        """
        # Step 1: Get parameters
        session_id = request.query_params.get('session_id', None)
        limit = request.query_params.get('limit', 20)
        
        if session_id is None:
            return Response(
                {'error': 'session_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session_id = int(session_id)
            limit = int(limit)
        except ValueError:
            return Response(
                {'error': 'session_id and limit must be integers'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Step 2: Check if session exists
        if not Session.objects.filter(session_id=session_id).exists():
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Step 3: Get messages
        try:
            chat_service = ChatService()
            
            if limit:
                # Get last N messages
                messages = chat_service.get_last_messages(session_id, limit)
            else:
                # Get all messages
                messages = chat_service.get_session_messages(session_id)
            
            # Step 4: Serialize and return
            serializer = MessageSerializer(messages, many=True)
            return Response(
                {
                    'session_id': session_id,
                    'message_count': len(messages),
                    'messages': serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve messages: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteSessionView(APIView):
    """
    Delete a session and all its messages.
    """
    
    def delete(self, request, session_id):
        """
        Delete a session.
        
        Path Parameters:
        - session_id: Integer (required) - The session ID to delete
        
        Deletes the session and all associated messages (CASCADE).
        """
        # Step 1: Get the session
        session = get_object_or_404(Session, session_id=session_id)
        
        try:
            # Step 2: Delete session (messages deleted automatically due to CASCADE)
            session.delete()
            
            return Response(
                {'message': f'Session {session_id} deleted successfully'},
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                {'error': f'Failed to delete session: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class StreamMessageView(APIView):
    """
    Stream AI responses in real-time using Server-Sent Events (SSE).
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Stream AI response as it's generated"""
        
        # Validate input
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=400)
        
        user_id = request.user.id
        message = serializer.validated_data['message']
        session_id = request.data.get('session_id')
        
        def event_stream():
            """Generator function for SSE"""
            try:
                chat_service = ChatService()
                
                # Get conversation context
                if session_id:
                    session = Session.objects.get(session_id=session_id)
                    messages = chat_service.get_last_messages(session_id, limit=20)
                    conversation_history = chat_service.format_messages_for_ai(messages)
                else:
                    # Create new session
                    session = chat_service.create_session_with_title(message)
                    conversation_history = []
                
                # Add user message
                conversation_history.append({'role': 'user', 'content': message})
                
                # Save user message
                user_msg = chat_service.save_message(
                    session_id=session.session_id,
                    author='user',
                    message=message,
                    user_id=user_id
                )
                
                # Send session info first
                yield f"data: {json.dumps({'type': 'session', 'session_id': session.session_id})}\n\n"
                
                # Stream AI response
                full_response = ""
                
                system_prompt = {
                    "role": "system",
                    "content": "You are a helpful assistant for Fitora..."
                }
                
                messages_with_system = [system_prompt] + conversation_history
                
                # OpenAI streaming
                ai_service = ai_service()
                stream = ai_service.client.chat.completions.create(
                    model=ai_service.model,
                    messages=messages_with_system,
                    temperature=0.7,
                    max_tokens=1000,
                    stream=True  # Enable streaming
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        
                        # Send chunk to client
                        yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"
                
                # Save complete AI response
                ai_msg = chat_service.save_message(
                    session_id=session.session_id,
                    author='ai',
                    message=full_response,
                    user_id=user_id
                )
                
                # Send completion
                yield f"data: {json.dumps({'type': 'done', 'message_id': ai_msg.message_id})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        
        return response
    

class SearchConversationsView(APIView):
    """Search through user's conversations"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Search messages by keyword
        
        Query params:
        - q: search query (required)
        - limit: max results (default 20)
        """
        query = request.query_params.get('q', '').strip()
        limit = int(request.query_params.get('limit', 20))
        
        if not query:
            return Response({'error': 'Query parameter "q" is required'}, status=400)
        
        user_id = request.user.id
        
        # PostgreSQL full-text search
        search_vector = SearchVector('message', weight='A') + SearchVector('session__title', weight='B')
        search_query = SearchQuery(query)
        
        messages = Message.objects.filter(
            user_id=user_id
        ).annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(
            search=search_query
        ).order_by('-rank', '-created_at')[:limit]
        
        # Group by sessions
        results = []
        seen_sessions = set()
        
        for msg in messages:
            if msg.session_id not in seen_sessions:
                results.append({
                    'session_id': msg.session.session_id,
                    'title': msg.session.title,
                    'matched_message': msg.message[:200],
                    'created_at': msg.created_at
                })
                seen_sessions.add(msg.session_id)
        
        return Response({
            'query': query,
            'results': results,
            'count': len(results)
        })