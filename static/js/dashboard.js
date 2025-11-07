/**
 * Dashboard WebSocket Handler
 * FASE 4: Conexão WebSocket para atualizações em tempo real
 */

class DashboardWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Inicial: 1 segundo
        this.maxReconnectDelay = 30000; // Máximo: 30 segundos
        this.isIntentionallyClosed = false;

        // Detectar protocolo (ws ou wss)
        this.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.wsUrl = `${this.protocol}//${window.location.host}/ws/dashboard/`;

        this.connect();
    }

    connect() {
        console.log('[WebSocket] Conectando ao dashboard...', this.wsUrl);

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
                case 'pedido_criado':
                    this.handlePedidoCriado(data.pedido);
                    break;

                case 'pedido_atualizado':
                    this.handlePedidoAtualizado(data.pedido);
                    break;

                case 'pedido_finalizado':
                    this.handlePedidoFinalizado(data.pedido_id, data.numero_orcamento);
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

    onError(error) {
        console.error('[WebSocket] Erro na conexão:', error);
    }

    onClose(event) {
        console.log('[WebSocket] Conexão fechada:', event.code, event.reason);
        this.updateConnectionStatus(false);

        // Limpar ping interval
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }

        // Tentar reconectar se não foi fechamento intencional
        if (!this.isIntentionallyClosed) {
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[WebSocket] Número máximo de tentativas de reconexão atingido.');
            this.updateConnectionStatus(false, 'Falha na conexão');
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
            this.maxReconnectDelay
        );

        console.log(`[WebSocket] Tentando reconectar em ${delay / 1000}s... (tentativa ${this.reconnectAttempts})`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    updateConnectionStatus(isConnected, message = '') {
        const statusIndicator = document.getElementById('ws-status-indicator');
        if (statusIndicator) {
            if (isConnected) {
                statusIndicator.className = 'inline-block w-2 h-2 bg-green-500 rounded-full';
                statusIndicator.title = 'Conectado';
            } else {
                statusIndicator.className = 'inline-block w-2 h-2 bg-red-500 rounded-full';
                statusIndicator.title = message || 'Desconectado';
            }
        }
    }

    // Event Handlers

    handlePedidoCriado(pedido) {
        console.log('[Dashboard] Novo pedido criado:', pedido);

        // Adicionar card do pedido à lista (silenciosamente)
        this.addPedidoCard(pedido);

        // Atualizar métricas
        this.updateMetricas();
    }

    handlePedidoAtualizado(pedido) {
        console.log('[Dashboard] Pedido atualizado:', pedido);

        // Atualizar card existente
        const card = document.querySelector(`[data-pedido-id="${pedido.id}"]`);
        if (card) {
            this.updatePedidoCard(card, pedido);
        } else {
            // Se não existir, adicionar
            this.addPedidoCard(pedido);
        }

        // Atualizar métricas
        this.updateMetricas();
    }

    handlePedidoFinalizado(pedidoId, numeroOrcamento) {
        console.log('[Dashboard] Pedido finalizado:', pedidoId, numeroOrcamento);

        // Remover card do pedido (se existir)
        const card = document.querySelector(`[data-pedido-id="${pedidoId}"]`);
        if (card) {
            card.classList.add('opacity-0', 'transition-opacity', 'duration-300');
            setTimeout(() => {
                card.remove();
            }, 300);
        }

        // Atualizar métricas
        this.updateMetricas();
    }

    addPedidoCard(pedido) {
        const pedidosContainer = document.getElementById('pedidos-container');
        if (!pedidosContainer) return;

        // Criar card HTML
        const cardHtml = this.createPedidoCardHtml(pedido);

        // Adicionar no início da lista com animação
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = cardHtml;
        const card = tempDiv.firstElementChild;

        card.classList.add('opacity-0');
        pedidosContainer.insertBefore(card, pedidosContainer.firstChild);

        // Animar entrada
        setTimeout(() => {
            card.classList.remove('opacity-0');
            card.classList.add('transition-opacity', 'duration-300');
        }, 10);
    }

    updatePedidoCard(cardElement, pedido) {
        // Atualizar dados do card
        const statusBadge = cardElement.querySelector('[data-status]');
        if (statusBadge) {
            statusBadge.textContent = pedido.status_display;
            statusBadge.className = this.getStatusBadgeClass(pedido.status);
        }

        // Atualizar barra de progresso e porcentagem
        if (pedido.porcentagem_separacao !== undefined) {
            const progressBar = cardElement.querySelector('.progress-bar-fill');
            const progressText = cardElement.querySelector('.progress-text');

            if (progressBar) {
                progressBar.style.width = `${pedido.porcentagem_separacao}%`;
                progressBar.dataset.progress = pedido.porcentagem_separacao;
            }

            if (progressText) {
                progressText.textContent = `${pedido.porcentagem_separacao}%`;
            }

            console.log(`[Dashboard] Progresso atualizado para pedido ${pedido.id}: ${pedido.porcentagem_separacao}%`);
        }

        // Atualizar outros campos conforme necessário
        // (adicionar mais lógica de atualização conforme FASE 5)
    }

    createPedidoCardHtml(pedido) {
        const statusClass = this.getStatusBadgeClass(pedido.status);

        return `
            <div class="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow"
                 data-pedido-id="${pedido.id}"
                 data-pedido-status="${pedido.status}"
                 data-vendedor-id="${pedido.vendedor_id}">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="text-lg font-semibold text-gray-900">
                        Orçamento #${pedido.numero_orcamento}
                    </h3>
                    <span class="${statusClass}" data-status>
                        ${pedido.status_display}
                    </span>
                </div>

                <div class="text-sm text-gray-600 space-y-1">
                    <p><strong>Cliente:</strong> ${pedido.cliente}</p>
                    <p><strong>Vendedor:</strong> ${pedido.vendedor}</p>
                    <p><strong>Data:</strong> ${pedido.data}</p>
                    <p><strong>Itens:</strong> ${pedido.total_itens}</p>
                </div>

                <div class="mt-3 flex gap-2">
                    <a href="/pedidos/${pedido.id}/"
                       class="text-sm text-blue-600 hover:text-blue-800 font-medium">
                        Ver Detalhes →
                    </a>
                </div>
            </div>
        `;
    }

    getStatusBadgeClass(status) {
        const classes = {
            'PENDENTE': 'px-2 py-1 text-xs font-medium rounded bg-yellow-100 text-yellow-800',
            'EM_SEPARACAO': 'px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800',
            'AGUARDANDO_COMPRA': 'px-2 py-1 text-xs font-medium rounded bg-orange-100 text-orange-800',
            'FINALIZADO': 'px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800',
            'CANCELADO': 'px-2 py-1 text-xs font-medium rounded bg-red-100 text-red-800',
        };

        return classes[status] || classes['PENDENTE'];
    }

    async updateMetricas() {
        // Recarregar métricas do servidor
        try {
            const response = await fetch('/dashboard/', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                // Por enquanto, apenas loga
                // Em uma implementação futura, pode extrair e atualizar apenas as métricas
                console.log('[Dashboard] Métricas atualizadas');

                // Recarregar a página para atualizar métricas
                // (pode ser otimizado com endpoint AJAX dedicado)
                const pedidosEmAberto = document.querySelectorAll('[data-pedido-status]:not([data-pedido-status="FINALIZADO"]):not([data-pedido-status="CANCELADO"])').length;
                const metricaAberto = document.getElementById('metrica-em-aberto');
                if (metricaAberto) {
                    metricaAberto.textContent = pedidosEmAberto;
                }
            }
        } catch (error) {
            console.error('[Dashboard] Erro ao atualizar métricas:', error);
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

// Inicializar WebSocket quando a página carregar
let dashboardWS = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Dashboard] Inicializando WebSocket...');
    dashboardWS = new DashboardWebSocket();
});

// Fechar conexão ao sair da página
window.addEventListener('beforeunload', () => {
    if (dashboardWS) {
        dashboardWS.close();
    }
});
