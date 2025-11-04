"""
ASGI config for pmcell_settings project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pmcell_settings.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import consumers depois de inicializar o Django
# from apps.core.consumers import DashboardConsumer

# WebSocket URL routing (será implementado na FASE 4)
websocket_urlpatterns = [
    # path('ws/dashboard/', DashboardConsumer.as_asgi()),
    # path('ws/pedido/<int:pedido_id>/', PedidoDetalheConsumer.as_asgi()),
    # path('ws/compras/', PainelComprasConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
