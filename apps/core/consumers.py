from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from django.utils import timezone


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket para atualizações em tempo real do dashboard.

    Eventos suportados:
    - pedido_criado: Novo pedido foi criado
    - pedido_atualizado: Pedido foi atualizado (status, itens, etc)
    - pedido_finalizado: Pedido foi finalizado
    """

    async def connect(self):
        """Aceita conexão WebSocket e adiciona ao group 'dashboard'"""
        self.group_name = 'dashboard'

        # Adicionar ao group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Aceitar conexão
        await self.accept()

        # Log de conexão (opcional)
        print(f"[WebSocket] Cliente conectado ao dashboard: {self.channel_name}")

    async def disconnect(self, close_code):
        """Remove da group ao desconectar"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        print(f"[WebSocket] Cliente desconectado do dashboard: {self.channel_name}")

    async def receive(self, text_data):
        """
        Recebe mensagens do cliente WebSocket.
        Por enquanto, apenas loga (pode ser expandido para ping/pong, etc).
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'unknown')

            # Responder a ping com pong (para keep-alive)
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
        except json.JSONDecodeError:
            print(f"[WebSocket] Mensagem inválida recebida: {text_data}")

    # Handlers para eventos do channel layer

    async def pedido_criado(self, event):
        """
        Handler chamado quando um novo pedido é criado.
        Envia os dados do pedido para o cliente.
        """
        await self.send(text_data=json.dumps({
            'type': 'pedido_criado',
            'pedido': event['pedido']
        }))

    async def pedido_atualizado(self, event):
        """
        Handler chamado quando um pedido é atualizado.
        Envia os dados atualizados do pedido.
        """
        await self.send(text_data=json.dumps({
            'type': 'pedido_atualizado',
            'pedido': event['pedido']
        }))

    async def pedido_finalizado(self, event):
        """
        Handler chamado quando um pedido é finalizado.
        Envia apenas o ID do pedido finalizado.
        """
        await self.send(text_data=json.dumps({
            'type': 'pedido_finalizado',
            'pedido_id': event['pedido_id'],
            'numero_orcamento': event.get('numero_orcamento', '')
        }))


# FASE 5: PedidoDetalheConsumer
# FASE 6: PainelComprasConsumer
