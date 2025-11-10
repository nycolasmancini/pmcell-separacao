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

        # IMPORTANTE: Aceitar conexão ANTES de acessar channel_layer
        # Isso evita erro 1006 se channel_layer falhar
        await self.accept()
        print(f"[WebSocket] Cliente conectado ao dashboard: {self.channel_name}")

        # Adicionar ao group (com error handling)
        try:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            print(f"[WebSocket] Cliente adicionado ao group '{self.group_name}'")
        except Exception as e:
            print(f"[WebSocket] ERRO ao adicionar ao group: {e}")
            # Conexão já foi aceita, continuar sem group (funciona localmente)

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

    async def card_status_updated(self, event):
        """
        Handler chamado quando o card_status de um pedido é atualizado.
        Envia o novo status do card para o dashboard.
        """
        await self.send(text_data=json.dumps({
            'type': 'card_status_updated',
            'pedido_id': event['pedido_id'],
            'card_status': event['card_status'],
            'card_status_display': event['card_status_display'],
            'separadores': event.get('separadores', [])
        }))


class PedidoDetalheConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket para atualizações em tempo real dos detalhes do pedido.

    Eventos suportados:
    - item_separado: Item foi marcado como separado
    - item_em_compra: Item foi marcado para compra
    - item_substituido: Item teve produto substituído
    - pedido_atualizado: Status do pedido mudou
    - pedido_finalizado: Pedido foi finalizado
    - pedido_deletado: Pedido foi deletado (soft delete)
    """

    async def connect(self):
        """Aceita conexão WebSocket e adiciona ao group específico do pedido"""
        self.pedido_id = self.scope['url_route']['kwargs']['pedido_id']
        self.group_name = f'pedido_{self.pedido_id}'

        # IMPORTANTE: Aceitar conexão ANTES de acessar channel_layer
        # Isso evita erro 1006 se channel_layer falhar
        await self.accept()
        print(f"[WebSocket] Cliente conectado ao pedido {self.pedido_id}: {self.channel_name}")

        # Adicionar ao group (com error handling)
        try:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            print(f"[WebSocket] Cliente adicionado ao group '{self.group_name}'")
        except Exception as e:
            print(f"[WebSocket] ERRO ao adicionar ao group '{self.group_name}': {e}")
            # Conexão já foi aceita, continuar sem group (funciona localmente)

    async def disconnect(self, close_code):
        """Remove do group ao desconectar"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        print(f"[WebSocket] Cliente desconectado do pedido {self.pedido_id}: {self.channel_name}")

    async def receive(self, text_data):
        """
        Recebe mensagens do cliente WebSocket.
        Responde a ping com pong para keep-alive.
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

    async def item_separado(self, event):
        """Handler chamado quando um item é separado"""
        await self.send(text_data=json.dumps({
            'type': 'item_separado',
            'item': event['item']
        }))

    async def item_em_compra(self, event):
        """Handler chamado quando um item é marcado para compra"""
        await self.send(text_data=json.dumps({
            'type': 'item_em_compra',
            'item': event['item']
        }))

    async def item_substituido(self, event):
        """Handler chamado quando um item tem produto substituído"""
        await self.send(text_data=json.dumps({
            'type': 'item_substituido',
            'item': event['item']
        }))

    async def pedido_atualizado(self, event):
        """Handler chamado quando o pedido é atualizado"""
        await self.send(text_data=json.dumps({
            'type': 'pedido_atualizado',
            'pedido': event['pedido']
        }))

    async def pedido_finalizado(self, event):
        """Handler chamado quando o pedido é finalizado"""
        await self.send(text_data=json.dumps({
            'type': 'pedido_finalizado',
            'pedido_id': event['pedido_id']
        }))

    async def pedido_deletado(self, event):
        """Handler chamado quando o pedido é deletado"""
        await self.send(text_data=json.dumps({
            'type': 'pedido_deletado',
            'pedido_id': event['pedido_id']
        }))

    async def compra_realizada(self, event):
        """Handler chamado quando compra de um produto é realizada"""
        await self.send(text_data=json.dumps({
            'type': 'compra_realizada',
            'produto_codigo': event['produto_codigo']
        }))

    async def item_unseparado(self, event):
        """Handler chamado quando um item é desseparado"""
        await self.send(text_data=json.dumps({
            'type': 'item_unseparado',
            'item': event['item']
        }))

    async def item_comprado(self, event):
        """Handler chamado quando um item é marcado como comprado"""
        await self.send(text_data=json.dumps({
            'type': 'item_comprado',
            'item': event['item']
        }))


# FASE 6: PainelComprasConsumer

class PainelComprasConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket para atualizações em tempo real do painel de compras.

    Eventos suportados:
    - item_marcado_compra: Novo item foi marcado para compra
    - compra_confirmada: Compra de um produto foi confirmada
    - item_separado_direto: Item foi separado direto do estoque (removido da lista de compras)
    """

    async def connect(self):
        """Aceita conexão WebSocket e adiciona ao group 'painel_compras'"""
        self.group_name = 'painel_compras'

        # IMPORTANTE: Aceitar conexão ANTES de acessar channel_layer
        # Isso evita erro 1006 se channel_layer falhar
        await self.accept()
        print(f"[WebSocket] Cliente conectado ao painel de compras: {self.channel_name}")

        # Adicionar ao group (com error handling)
        try:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            print(f"[WebSocket] Cliente adicionado ao group '{self.group_name}'")
        except Exception as e:
            print(f"[WebSocket] ERRO ao adicionar ao group: {e}")
            # Conexão já foi aceita, continuar sem group (funciona localmente)

    async def disconnect(self, close_code):
        """Remove do group ao desconectar"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        print(f"[WebSocket] Cliente desconectado do painel de compras: {self.channel_name}")

    async def receive(self, text_data):
        """
        Recebe mensagens do cliente WebSocket.
        Responde a ping com pong para keep-alive.
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

    async def item_marcado_compra(self, event):
        """
        Handler chamado quando um novo item é marcado para compra.
        Envia os dados do item para o cliente.
        """
        await self.send(text_data=json.dumps({
            'type': 'item_marcado_compra',
            'item': event['item']
        }))

    async def compra_confirmada(self, event):
        """
        Handler chamado quando uma compra é confirmada.
        Envia os dados do produto para o cliente.
        """
        await self.send(text_data=json.dumps({
            'type': 'compra_confirmada',
            'produto': event['produto']
        }))

    async def item_separado_direto(self, event):
        """
        Handler chamado quando um item é separado direto do estoque.
        Remove o item da lista de compras.
        """
        await self.send(text_data=json.dumps({
            'type': 'item_separado_direto',
            'item': event['item']
        }))

    async def item_comprado(self, event):
        """
        Handler chamado quando um item é marcado/desmarcado como comprado.
        Atualiza o status de compra do item no painel.
        """
        await self.send(text_data=json.dumps({
            'type': 'item_comprado',
            'item': event['item']
        }))
