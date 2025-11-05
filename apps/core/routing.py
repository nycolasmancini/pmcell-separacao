"""
Roteamento WebSocket para o app core
"""
from django.urls import path
from apps.core import consumers

websocket_urlpatterns = [
    path('ws/dashboard/', consumers.DashboardConsumer.as_asgi()),
]
