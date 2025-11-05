/**
 * Pedido Detalhe WebSocket Handler e Alpine.js App
 * FASE 5: Conexão WebSocket para atualizações em tempo real de itens
 */

class PedidoDetalheWebSocket {
    constructor(pedidoId) {
        this.pedidoId = pedidoId;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.isIntentionallyClosed = false;

        // Detectar protocolo (ws ou wss)
        this.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.wsUrl = `${this.protocol}//${window.location.host}/ws/pedido/${this.pedidoId}/`;

        this.connect();
    }

    connect() {
        console.log(`[WebSocket] Conectando ao pedido ${this.pedidoId}...`, this.wsUrl);

        try {
            this.ws = new WebSocket(this.wsUrl);

            this.ws.onopen = () => this.onOpen();
            this.ws.onmessage = (event) => this.onMessage(event);
            this.ws.onerror = (error) => this.onError(error);
            this.ws.onclose = (event) => this.onClose(event);
        } catch (error) {
            console.error('[WebSocket] Erro ao criar conexão:', error);
            this.scheduleReconnect();
        }
    }

    onOpen() {
        console.log('[WebSocket] Conectado com sucesso!');
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.updateConnectionStatus(true);

        // Enviar ping a cada 30 segundos para manter conexão viva
        this.pingInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    }

    onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('[WebSocket] Mensagem recebida:', data);

            switch (data.type) {
                case 'item_separado':
                    this.handleItemSeparado(data.item);
                    break;

                case 'item_em_compra':
                    this.handleItemEmCompra(data.item);
                    break;

                case 'item_substituido':
                    this.handleItemSubstituido(data.item);
                    break;

                case 'pedido_atualizado':
                    this.handlePedidoAtualizado(data.pedido);
                    break;

                case 'pedido_finalizado':
                    this.handlePedidoFinalizado(data.pedido_id);
                    break;

                case 'pedido_deletado':
                    this.handlePedidoDeletado(data.pedido_id);
                    break;

                case 'pong':
                    // Resposta ao ping - conexão está ativa
                    break;

                default:
                    console.warn('[WebSocket] Tipo de mensagem desconhecido:', data.type);
            }
        } catch (error) {
            console.error('[WebSocket] Erro ao processar mensagem:', error);
        }
    }

    handleItemSeparado(item) {
        console.log('[WebSocket] Item separado:', item);

        const row = document.querySelector(`tr[data-item-id="${item.id}"]`);
        if (row) {
            // Atualizar status visual
            const statusCell = row.querySelector('td:nth-child(4)');
            if (statusCell) {
                statusCell.innerHTML = `
                    <span class="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        ✓ Separado
                    </span>
                    <div class="text-xs text-gray-500 mt-1">${item.separado_por} - ${item.separado_em}</div>
                `;
            }

            // Remover botões de ação
            const actionsCell = row.querySelector('td:nth-child(5)');
            if (actionsCell) {
                actionsCell.innerHTML = '<div class="text-xs text-gray-500">Concluído</div>';
            }
        }

        // Recarregar página para atualizar estatísticas
        setTimeout(() => location.reload(), 1000);
    }

    handleItemEmCompra(item) {
        console.log('[WebSocket] Item em compra:', item);

        const row = document.querySelector(`tr[data-item-id="${item.id}"]`);
        if (row) {
            const statusCell = row.querySelector('td:nth-child(4)');
            if (statusCell) {
                statusCell.innerHTML = `
                    <span class="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">
                        🛒 Em Compra
                    </span>
                    <div class="text-xs text-gray-500 mt-1">${item.marcado_compra_por} - ${item.marcado_compra_em}</div>
                `;
            }

            const actionsCell = row.querySelector('td:nth-child(5)');
            if (actionsCell) {
                actionsCell.innerHTML = '<div class="text-xs text-gray-500">Aguardando compra</div>';
            }
        }

        setTimeout(() => location.reload(), 1000);
    }

    handleItemSubstituido(item) {
        console.log('[WebSocket] Item substituído:', item);

        const row = document.querySelector(`tr[data-item-id="${item.id}"]`);
        if (row) {
            // Atualizar descrição do produto
            const produtoCell = row.querySelector('td:nth-child(1)');
            if (produtoCell) {
                const descDiv = produtoCell.querySelector('div');
                if (descDiv) {
                    descDiv.innerHTML += `
                        <div class="text-xs text-blue-600 mt-1">
                            Substituído por: <strong>${item.produto_substituto}</strong>
                        </div>
                    `;
                }
            }

            // Atualizar status
            const statusCell = row.querySelector('td:nth-child(4)');
            if (statusCell) {
                statusCell.innerHTML = `
                    <span class="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                        ↔ Substituído
                    </span>
                `;
            }

            const actionsCell = row.querySelector('td:nth-child(5)');
            if (actionsCell) {
                actionsCell.innerHTML = '<div class="text-xs text-gray-500">Concluído</div>';
            }
        }

        setTimeout(() => location.reload(), 1000);
    }

    handlePedidoAtualizado(pedido) {
        console.log('[WebSocket] Pedido atualizado:', pedido);
        // Recarregar para atualizar status do pedido
        setTimeout(() => location.reload(), 500);
    }

    handlePedidoFinalizado(pedidoId) {
        console.log('[WebSocket] Pedido finalizado:', pedidoId);
        alert('Pedido finalizado!');
        window.location.href = '/dashboard/';
    }

    handlePedidoDeletado(pedidoId) {
        console.log('[WebSocket] Pedido deletado:', pedidoId);
        alert('Este pedido foi deletado.');
        window.location.href = '/dashboard/';
    }

    onError(error) {
        console.error('[WebSocket] Erro:', error);
        this.updateConnectionStatus(false);
    }

    onClose(event) {
        console.log('[WebSocket] Conexão fechada:', event.code, event.reason);

        if (this.pingInterval) {
            clearInterval(this.pingInterval);
        }

        this.updateConnectionStatus(false);

        if (!this.isIntentionallyClosed) {
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[WebSocket] Máximo de tentativas de reconexão atingido.');
            this.updateConnectionStatus(false, 'Falha na conexão');
            return;
        }

        this.reconnectAttempts++;
        console.log(`[WebSocket] Tentando reconectar (${this.reconnectAttempts}/${this.maxReconnectAttempts}) em ${this.reconnectDelay}ms...`);

        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay);

        // Exponential backoff
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    }

    updateConnectionStatus(connected, message = '') {
        const indicator = document.getElementById('ws-status-indicator');
        if (indicator) {
            if (connected) {
                indicator.className = 'inline-block w-2 h-2 bg-green-500 rounded-full ml-2';
                indicator.title = 'Conectado';
            } else {
                indicator.className = 'inline-block w-2 h-2 bg-red-500 rounded-full ml-2';
                indicator.title = message || 'Desconectado';
            }
        }
    }

    close() {
        this.isIntentionallyClosed = true;
        if (this.ws) {
            this.ws.close();
        }
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
        }
    }
}

// Alpine.js App
function pedidoDetalheApp(pedidoId) {
    return {
        pedidoId: pedidoId,
        ws: null,

        // Modals
        modalSubstituir: {
            show: false,
            itemId: null,
            produtoSubstituto: ''
        },

        modalCompra: {
            show: false,
            itemId: null,
            outrosItens: [],
            itensSelecionados: []
        },

        init() {
            console.log('Inicializando pedido_detalhe app para pedido:', this.pedidoId);
            this.ws = new PedidoDetalheWebSocket(this.pedidoId);
        },

        // Separar Item
        async separarItem(itemId) {
            if (!confirm('Confirma a separação deste item?')) return;

            try {
                const response = await fetch(`/pedidos/item/${itemId}/separar/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    }
                });

                const data = await response.json();

                if (data.success) {
                    console.log('Item separado com sucesso:', data);
                    // WebSocket vai atualizar a UI
                } else {
                    alert('Erro: ' + (data.error || 'Erro ao separar item'));
                }
            } catch (error) {
                console.error('Erro ao separar item:', error);
                alert('Erro ao separar item. Tente novamente.');
            }
        },

        // Modal Substituir
        abrirModalSubstituir(itemId) {
            this.modalSubstituir.itemId = itemId;
            this.modalSubstituir.produtoSubstituto = '';
            this.modalSubstituir.show = true;
        },

        async substituirItem() {
            if (!this.modalSubstituir.produtoSubstituto.trim()) {
                alert('Informe o produto substituto.');
                return;
            }

            try {
                const formData = new FormData();
                formData.append('produto_substituto', this.modalSubstituir.produtoSubstituto);
                formData.append('csrfmiddlewaretoken', this.getCsrfToken());

                const response = await fetch(`/pedidos/item/${this.modalSubstituir.itemId}/substituir/`, {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    console.log('Item substituído com sucesso:', data);
                    this.modalSubstituir.show = false;
                    // WebSocket vai atualizar a UI
                } else {
                    alert('Erro: ' + (data.error || 'Erro ao substituir item'));
                }
            } catch (error) {
                console.error('Erro ao substituir item:', error);
                alert('Erro ao substituir item. Tente novamente.');
            }
        },

        // Modal Compra
        async abrirModalCompra(itemId) {
            try {
                // Buscar outros itens com o mesmo produto
                const response = await fetch(`/pedidos/item/${itemId}/marcar-compra/`, {
                    method: 'GET',
                    headers: {
                        'X-CSRFToken': this.getCsrfToken()
                    }
                });

                const data = await response.json();

                if (data.success) {
                    this.modalCompra.itemId = itemId;
                    this.modalCompra.outrosItens = data.outros_itens || [];
                    this.modalCompra.itensSelecionados = [];
                    this.modalCompra.show = true;
                } else {
                    alert('Erro ao buscar outros itens.');
                }
            } catch (error) {
                console.error('Erro ao abrir modal de compra:', error);
                alert('Erro ao abrir modal. Tente novamente.');
            }
        },

        async marcarCompra() {
            try {
                const formData = new FormData();
                formData.append('csrfmiddlewaretoken', this.getCsrfToken());

                // Adicionar outros itens selecionados
                this.modalCompra.itensSelecionados.forEach(id => {
                    formData.append('outros_pedidos', id);
                });

                const response = await fetch(`/pedidos/item/${this.modalCompra.itemId}/marcar-compra/`, {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    console.log('Item(ns) marcado(s) para compra:', data);
                    this.modalCompra.show = false;
                    // WebSocket vai atualizar a UI
                } else {
                    alert('Erro: ' + (data.error || 'Erro ao marcar para compra'));
                }
            } catch (error) {
                console.error('Erro ao marcar para compra:', error);
                alert('Erro ao marcar para compra. Tente novamente.');
            }
        },

        // Finalizar Pedido
        async finalizarPedido() {
            if (!confirm('Confirma a finalização deste pedido? Esta ação não pode ser desfeita.')) return;

            try {
                const response = await fetch(`/pedidos/${this.pedidoId}/finalizar/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    }
                });

                const data = await response.json();

                if (data.success) {
                    alert('Pedido finalizado com sucesso!');
                    window.location.href = data.redirect_url;
                } else {
                    alert('Erro: ' + (data.error || 'Erro ao finalizar pedido'));
                }
            } catch (error) {
                console.error('Erro ao finalizar pedido:', error);
                alert('Erro ao finalizar pedido. Tente novamente.');
            }
        },

        // Deletar Pedido
        async deletarPedido() {
            if (!confirm('Tem certeza que deseja deletar este pedido? Esta ação não pode ser desfeita.')) return;

            try {
                const response = await fetch(`/pedidos/${this.pedidoId}/deletar/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    }
                });

                const data = await response.json();

                if (data.success) {
                    alert('Pedido deletado com sucesso.');
                    window.location.href = data.redirect_url;
                } else {
                    alert('Erro: ' + (data.error || 'Erro ao deletar pedido'));
                }
            } catch (error) {
                console.error('Erro ao deletar pedido:', error);
                alert('Erro ao deletar pedido. Tente novamente.');
            }
        },

        // Helper: Get CSRF Token
        getCsrfToken() {
            const name = 'csrftoken';
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    };
}

// Limpar WebSocket ao sair da página
window.addEventListener('beforeunload', () => {
    if (window.pedidoWs) {
        window.pedidoWs.close();
    }
});
