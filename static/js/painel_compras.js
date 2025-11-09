/**
 * Painel de Compras WebSocket Handler + Alpine.js App
 * FASE 6: WebSocket para atualizações em tempo real do painel de compras
 */

class PainelComprasWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Inicial: 1 segundo
        this.maxReconnectDelay = 30000; // Máximo: 30 segundos
        this.isIntentionallyClosed = false;

        // Detectar protocolo (ws ou wss)
        this.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.wsUrl = `${this.protocol}//${window.location.host}/ws/painel-compras/`;

        this.connect();
    }

    connect() {
        console.log('[WebSocket] Conectando ao painel de compras...', this.wsUrl);

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
                case 'item_marcado_compra':
                    this.handleItemMarcadoCompra(data.item);
                    break;

                case 'compra_confirmada':
                    this.handleCompraConfirmada(data.produto);
                    break;

                case 'item_separado_direto':
                    this.handleItemSeparadoDireto(data.item);
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
            console.error('[WebSocket] Número máximo de tentativas de reconexão atingido');
            this.updateConnectionStatus(false, 'Falha ao reconectar. Recarregue a página.');
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(this.reconnectDelay * this.reconnectAttempts, this.maxReconnectDelay);

        console.log(`[WebSocket] Tentando reconectar em ${delay}ms (tentativa ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    updateConnectionStatus(connected, message = '') {
        const indicator = document.getElementById('ws-status-indicator');
        if (!indicator) return;

        if (connected) {
            indicator.className = 'inline-block w-2 h-2 bg-green-500 rounded-full ml-2';
            indicator.title = 'Conectado';
        } else {
            indicator.className = 'inline-block w-2 h-2 bg-red-500 rounded-full ml-2';
            indicator.title = message || 'Desconectado';
        }
    }

    // Handlers de eventos

    handleItemMarcadoCompra(item) {
        console.log('[WebSocket] Novo item marcado para compra:', item);
        // Recarregar a página para mostrar o novo item
        // (Em uma implementação mais sofisticada, poderia adicionar dinamicamente ao DOM)
        window.location.reload();
    }

    handleCompraConfirmada(produto) {
        console.log('[WebSocket] Compra confirmada:', produto);

        // Mostrar notificação de sucesso
        if (window.Alpine && window.Alpine.store) {
            // Implementação futura: usar Alpine.js store para notificações
        }

        // Recarregar a página para atualizar a lista
        window.location.reload();
    }

    handleItemSeparadoDireto(item) {
        console.log('[WebSocket] Item separado direto do estoque:', item);
        // Recarregar a página para remover o item da lista
        window.location.reload();
    }

    close() {
        this.isIntentionallyClosed = true;
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Alpine.js App para o Painel de Compras
function painelComprasApp() {
    return {
        // State
        produtos: window.produtosData || [],
        filteredProducts: [],
        searchText: '',
        orderFilter: '',
        modalConfirmar: {
            show: false,
            produtoCodigo: '',
            produtoDesc: '',
            totalItens: 0
        },

        // Initialization
        init() {
            console.log('[PainelComprasApp] Inicializando...');
            console.log('[PainelComprasApp] window.produtosData:', window.produtosData);
            console.log('[PainelComprasApp] Total produtos carregados:', this.produtos.length);

            if (this.produtos.length > 0) {
                console.log('[PainelComprasApp] Primeiro produto:', this.produtos[0]);
            } else {
                console.warn('[PainelComprasApp] AVISO: Nenhum produto encontrado!');
            }

            // Set filtered products
            this.filteredProducts = this.produtos;
            console.log('[PainelComprasApp] Produtos filtrados iniciais:', this.filteredProducts.length);

            // Ensure search fields are cleared (fix browser autocomplete bugs)
            this.searchText = '';
            this.orderFilter = '';

            // Clear input values via DOM to override any browser autocomplete
            const searchInput = document.getElementById('searchText');
            const orderInput = document.getElementById('orderFilter');
            if (searchInput) searchInput.value = '';
            if (orderInput) orderInput.value = '';

            // Inicializar WebSocket
            this.ws = new PainelComprasWebSocket();
        },

        // Filter products
        filterProducts() {
            let filtered = this.produtos;

            // Filtro por texto (código ou descrição)
            if (this.searchText.trim()) {
                const search = this.searchText.toLowerCase().trim();
                filtered = filtered.filter(produto =>
                    produto.codigo.toLowerCase().includes(search) ||
                    produto.descricao.toLowerCase().includes(search)
                );
            }

            // Filtro por pedido
            if (this.orderFilter.trim()) {
                const orderSearch = this.orderFilter.toLowerCase().trim();
                filtered = filtered.filter(produto =>
                    produto.itens.some(item =>
                        item.pedido_numero.toLowerCase().includes(orderSearch)
                    )
                );
            }

            this.filteredProducts = filtered;
            console.log('[PainelComprasApp] Produtos filtrados:', this.filteredProducts.length);
        },

        // Open confirmation modal
        openConfirmModal(produto) {
            this.modalConfirmar.show = true;
            this.modalConfirmar.produtoCodigo = produto.codigo;
            this.modalConfirmar.produtoDesc = produto.descricao;
            this.modalConfirmar.totalItens = produto.itens.length;
            console.log('[PainelComprasApp] Modal aberto para:', produto.codigo);
        },

        // Confirm purchase
        async confirmarCompra() {
            const produtoCodigo = this.modalConfirmar.produtoCodigo;

            try {
                console.log('[PainelComprasApp] Confirmando compra de:', produtoCodigo);

                const response = await fetch(`/painel-compras/confirmar/${produtoCodigo}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    }
                });

                const data = await response.json();

                if (data.success) {
                    console.log('[PainelComprasApp] Compra confirmada com sucesso!');
                    // Fechar modal
                    this.modalConfirmar.show = false;

                    // Mostrar mensagem de sucesso (opcional)
                    alert(`Compra confirmada com sucesso! ${data.total_itens} item(ns) marcado(s) como comprado.`);

                    // Recarregar página para atualizar lista
                    window.location.reload();
                } else {
                    console.error('[PainelComprasApp] Erro ao confirmar compra:', data.error);
                    alert(`Erro: ${data.error}`);
                }
            } catch (error) {
                console.error('[PainelComprasApp] Erro na requisição:', error);
                alert('Erro ao confirmar compra. Por favor, tente novamente.');
            }
        },

        // Get CSRF token from cookie
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

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.painelComprasWs) {
        window.painelComprasWs.close();
    }
});
