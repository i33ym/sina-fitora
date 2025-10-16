from django.urls import path
from .views import (
    SendMessageView,
    UserSessionsView,
    SessionDetailView,
    MessageHistoryView,
    DeleteSessionView
    #StreamMessageView
)

app_name = 'chatbot'

urlpatterns = [
    path('send/', SendMessageView.as_view(), name='send_message'),
    path('sessions/', UserSessionsView.as_view(), name='user_sessions'),
    path('sessions/<int:session_id>/', SessionDetailView.as_view(), name='session_detail'),
    path('messages/', MessageHistoryView.as_view(), name='message_history'),
    path('sessions/<int:session_id>/delete/', DeleteSessionView.as_view(), name='delete_session'),
    #path('stream/', StreamMessageView.as_view(), name='stream_message'),
]