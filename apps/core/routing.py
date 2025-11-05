"""
Roteamento WebSocket para o app core
"""
from django.urls import path
from apps.core import consumers

websocket_urlpatterns = [
    path('ws/dashboard/', consumers.DashboardConsumer.as_asgi()),
    path('ws/pedido/<int:pedido_id>/', consumers.PedidoDetalheConsumer.as_asgi()),
    path('ws/painel-compras/', consumers.PainelComprasConsumer.as_asgi()),
]
