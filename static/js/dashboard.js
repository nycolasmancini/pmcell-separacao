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

                case 'card_status_updated':
                    this.handleCardStatusUpdated(data.pedido_id, data.card_status, data.card_status_display);
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

    handleCardStatusUpdated(pedidoId, cardStatus, cardStatusDisplay) {
        console.log('[Dashboard] Card status updated:', pedidoId, cardStatus, cardStatusDisplay);

        const card = document.querySelector(`[data-pedido-id="${pedidoId}"]`);
        if (!card) {
            console.warn(`[Dashboard] Card não encontrado para pedido ${pedidoId}`);
            return;
        }

        // Update data attribute
        card.dataset.cardStatus = cardStatus;

        // Update border - remove all card-border-* classes and add new one
        const borderTop = card.querySelector('.card-border-top');
        if (borderTop) {
            borderTop.className = borderTop.className.replace(/card-border-\S+/g, '').trim();
            const borderClass = 'card-border-' + cardStatus.toLowerCase().replace(/_/g, '-');
            borderTop.className = 'card-border-top ' + borderClass;
            console.log(`[Dashboard] Border atualizado: ${borderClass}`);
        }

        // Update status badge - remove all badge-* classes and add new one
        const statusBadge = card.querySelector('[data-status]');
        if (statusBadge) {
            statusBadge.textContent = cardStatusDisplay;
            statusBadge.className = statusBadge.className.replace(/badge-\S+/g, '').trim();
            const badgeClass = 'badge-' + cardStatus.toLowerCase().replace(/_/g, '-');
            statusBadge.className = 'status-badge-modern ' + badgeClass;
            console.log(`[Dashboard] Badge atualizado: ${badgeClass}, texto: ${cardStatusDisplay}`);
        }

        // Add pulse animation for visual feedback
        card.classList.add('pulse-once');
        setTimeout(() => {
            card.classList.remove('pulse-once');
        }, 1000);
    }

    createPedidoCardHtml(pedido) {
        const borderClass = this.getStatusBorderClass(pedido.status);
        const badgeClass = this.getStatusBadgeClass(pedido.status);

        return `
            <a href="/pedido/${pedido.id}/" class="card-link">
                <div class="card-modern fade-in"
                     data-pedido-id="${pedido.id}"
                     data-pedido-status="${pedido.status}"
                     data-vendedor-id="${pedido.vendedor_id}">

                    <!-- Borda superior colorida baseada no status -->
                    <div class="card-border-top ${borderClass}"></div>

                    <div class="card-content">
                        <!-- Header: Número do orçamento e Badge de Status -->
                        <div class="card-header">
                            <span class="card-number">#${pedido.numero_orcamento}</span>
                            <span class="status-badge-modern ${badgeClass}" data-status>
                                ${pedido.status_display}
                            </span>
                        </div>

                        <!-- Divisor -->
                        <div class="card-divider"></div>

                        <!-- Informações do Pedido -->
                        <div class="card-info">
                            <p class="card-info-primary">${pedido.cliente}</p>
                            <p class="card-info-item">
                                <span class="card-info-label">Vendedor:</span>
                                <span class="card-info-value">${pedido.vendedor}</span>
                            </p>
                            <p class="card-info-item">
                                <span class="card-info-label">Logística:</span>
                                <span class="card-info-value">${pedido.logistica || 'Não definida'}</span>
                            </p>
                            <p class="card-info-item card-info-value">
                                ${pedido.embalagem || 'Embalagem padrão'}
                            </p>
                        </div>

                        <!-- Barra de Progresso -->
                        <div class="progress-container">
                            <div class="progress-wrapper">
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill"
                                         style="width: ${pedido.porcentagem_separacao || 0}%"
                                         data-progress="${pedido.porcentagem_separacao || 0}"></div>
                                </div>
                                <span class="progress-text">
                                    ${pedido.porcentagem_separacao || 0}%
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </a>
        `;
    }

    getStatusBadgeClass(status) {
        const classes = {
            'PENDENTE': 'badge-pendente',
            'EM_SEPARACAO': 'badge-em-separacao',
            'AGUARDANDO_COMPRA': 'badge-aguardando-compra',
            'FINALIZADO': 'badge-finalizado',
            'CANCELADO': 'badge-cancelado',
        };

        return classes[status] || classes['PENDENTE'];
    }

    getStatusBorderClass(status) {
        const classes = {
            'PENDENTE': 'card-border-pendente',
            'EM_SEPARACAO': 'card-border-em-separacao',
            'AGUARDANDO_COMPRA': 'card-border-aguardando-compra',
            'FINALIZADO': 'card-border-finalizado',
            'CANCELADO': 'card-border-cancelado',
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
