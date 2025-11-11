/**
 * Painel de Compras WebSocket Handler + Alpine.js App
 * NOVA ESTRUTURA: Itens agrupados por pedidos com checkboxes
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
        console.log('[WebSocket] ========================================');
        console.log('[WebSocket] ✅ CONEXÃO ESTABELECIDA COM SUCESSO!');
        console.log('[WebSocket] ========================================');
        console.log('[WebSocket] URL:', this.wsUrl);
        console.log('[WebSocket] Protocol:', this.protocol);
        console.log('[WebSocket] ReadyState:', this.ws.readyState);
        console.log('[WebSocket] ========================================');

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
            console.log('[WebSocket] ========================================');
            console.log('[WebSocket] 📨 MENSAGEM RECEBIDA');
            console.log('[WebSocket] ========================================');
            console.log('[WebSocket] Data completo:', data);
            console.log('[WebSocket] Tipo de mensagem:', data.type);
            console.log('[WebSocket] Timestamp:', new Date().toISOString());
            console.log('[WebSocket] ========================================');

            switch (data.type) {
                case 'item_marcado_compra':
                    console.log('[WebSocket] Roteando para handleItemMarcadoCompra...');
                    this.handleItemMarcadoCompra(data.item);
                    break;

                case 'item_comprado':
                    this.handleItemComprado(data.item);
                    break;

                case 'compra_confirmada':
                    this.handleCompraConfirmada(data.produto);
                    break;

                case 'item_separado_direto':
                    this.handleItemSeparadoDireto(data.item);
                    break;

                case 'item_removido_compras':
                    this.handleItemRemovidoCompras(data.item_id, data.pedido_id);
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

    handleItemMarcadoCompra(itemData) {
        console.log('[WebSocket] ========================================');
        console.log('[WebSocket] INICIANDO handleItemMarcadoCompra');
        console.log('[WebSocket] Item data recebido:', itemData);
        console.log('[WebSocket] ========================================');

        try {
            // Obter componente Alpine via _x_dataStack (método correto)
            const component = document.querySelector('[x-data="painelComprasApp()"]');
            console.log('[WebSocket] Componente Alpine encontrado:', !!component);

            if (!component || !component._x_dataStack) {
                console.error('[WebSocket] ❌ Alpine.js app não encontrado, recarregando página...');
                window.location.reload();
                return;
            }

            // Acessar dados reativos do Alpine
            const alpineData = component._x_dataStack[0];
            console.log('[WebSocket] ✅ alpineData acessado com sucesso');
            console.log('[WebSocket] Estado atual de pedidos:', {
                totalPedidos: alpineData.pedidos.length,
                totalFiltered: alpineData.filteredOrders.length,
                pedidoIds: alpineData.pedidos.map(p => p.id)
            });

            // Encontrar o pedido nos dados do Alpine
            let pedidoIndex = alpineData.pedidos.findIndex(p => p.id === itemData.pedido_id);
            console.log('[WebSocket] Procurando pedido ID:', itemData.pedido_id);
            console.log('[WebSocket] Pedido encontrado no índice:', pedidoIndex);

            if (pedidoIndex === -1) {
                console.log('[WebSocket] ========================================');
                console.log('[WebSocket] CAMINHO: Criando NOVO pedido');
                console.log('[WebSocket] ========================================');

                // Novo pedido - criar com o item já incluído
                const novoItem = {
                    id: itemData.id,
                    produto_codigo: itemData.produto_codigo,
                    produto_descricao: itemData.produto_descricao,
                    quantidade: itemData.quantidade,
                    marcado_por: itemData.marcado_por,
                    marcado_em: itemData.marcado_em,
                    comprado: itemData.comprado || false
                };
                console.log('[WebSocket] Novo item criado:', novoItem);

                const novoPedido = {
                    id: itemData.pedido_id,
                    numero: itemData.pedido_numero,
                    cliente: itemData.cliente || 'Cliente Desconhecido',
                    itens: [novoItem]  // ← FIX: Include item immediately
                };
                console.log('[WebSocket] Novo pedido criado:', novoPedido);

                // Add to pedidos only - avoid duplication
                console.log('[WebSocket] Adicionando pedido a alpineData.pedidos...');
                alpineData.pedidos.push(novoPedido);
                console.log('[WebSocket] ✅ Pedido adicionado a alpineData.pedidos');

                // Call filterOrders to update filtered view properly
                console.log('[WebSocket] Chamando filterOrders() para atualizar view filtrada...');
                alpineData.filterOrders();
                console.log('[WebSocket] ✅ filterOrders() executado - filteredOrders atualizado');

                // Force Alpine.js reactivity if needed
                if (window.Alpine && Alpine.nextTick) {
                    Alpine.nextTick(() => {
                        console.log('[WebSocket] Alpine.nextTick executado - UI deve atualizar');
                    });
                }

                console.log('[WebSocket] Estado FINAL após criação:', {
                    totalPedidos: alpineData.pedidos.length,
                    totalFiltered: alpineData.filteredOrders.length,
                    pedidoIds: alpineData.pedidos.map(p => p.id),
                    filteredIds: alpineData.filteredOrders.map(p => p.id)
                });
                console.log('[WebSocket] ========================================');
                console.log('[WebSocket] FIM handleItemMarcadoCompra - NOVO PEDIDO');
                console.log('[WebSocket] ========================================');

            } else {
                console.log('[WebSocket] ========================================');
                console.log('[WebSocket] CAMINHO: Adicionando item a pedido EXISTENTE');
                console.log('[WebSocket] ========================================');

                // Pedido existente - adicionar item
                const pedido = alpineData.pedidos[pedidoIndex];
                console.log('[WebSocket] Pedido existente encontrado:', {
                    id: pedido.id,
                    numero: pedido.numero,
                    totalItens: pedido.itens.length
                });

                // Verificar se o item já existe
                const itemExistente = pedido.itens.find(i => i.id === itemData.id);
                if (itemExistente) {
                    console.warn('[WebSocket] ⚠️ Item já existe no pedido, ignorando duplicata');
                    return;
                }

                // Adicionar novo item
                const novoItem = {
                    id: itemData.id,
                    produto_codigo: itemData.produto_codigo,
                    produto_descricao: itemData.produto_descricao,
                    quantidade: itemData.quantidade,
                    marcado_por: itemData.marcado_por,
                    marcado_em: itemData.marcado_em,
                    comprado: itemData.comprado || false
                };
                console.log('[WebSocket] Novo item a ser adicionado:', novoItem);

                console.log('[WebSocket] Adicionando item ao array pedido.itens...');
                pedido.itens.push(novoItem);
                console.log('[WebSocket] ✅ Item adicionado ao array');

                // Force reactivity: Re-run filter
                console.log('[WebSocket] Chamando filterOrders() para forçar reatividade...');
                alpineData.filterOrders();
                console.log('[WebSocket] ✅ filterOrders() executado');

                console.log('[WebSocket] Estado FINAL após adição de item:', {
                    pedidoId: pedido.id,
                    totalItensNoPedido: pedido.itens.length,
                    totalPedidos: alpineData.pedidos.length,
                    totalFiltered: alpineData.filteredOrders.length
                });
                console.log('[WebSocket] ========================================');
                console.log('[WebSocket] FIM handleItemMarcadoCompra - ITEM EXISTENTE');
                console.log('[WebSocket] ========================================');
            }

        } catch (error) {
            console.error('[WebSocket] ========================================');
            console.error('[WebSocket] ❌❌❌ ERRO CRÍTICO ❌❌❌');
            console.error('[WebSocket] ========================================');
            console.error('[WebSocket] Erro ao adicionar item dinamicamente:', error);
            console.error('[WebSocket] Stack trace:', error.stack);
            console.error('[WebSocket] Recarregando página como fallback...');
            console.error('[WebSocket] ========================================');
            window.location.reload();
        }
    }

    handleItemComprado(itemData) {
        console.log('[WebSocket] Item marcado/desmarcado como comprado:', itemData);

        // Encontrar o item no DOM e atualizar o estado
        const itemElement = document.querySelector(`[data-item-id="${itemData.id}"]`);
        if (!itemElement) {
            console.warn('[WebSocket] Item não encontrado no DOM:', itemData.id);
            return;
        }

        // Encontrar o checkbox do item
        const checkbox = itemElement.querySelector(`input[type="checkbox"]#item-${itemData.id}`);
        if (!checkbox) {
            console.warn('[WebSocket] Checkbox não encontrado para item:', itemData.id);
            return;
        }

        // Atualizar o estado do checkbox
        checkbox.checked = itemData.comprado;

        // Atualizar ou criar badge "COMPRADO"
        const badgeContainer = itemElement.querySelector('.ml-3');
        if (itemData.comprado) {
            // Criar badge se não existir
            if (!badgeContainer || !badgeContainer.querySelector('.badge-comprado')) {
                const newBadge = document.createElement('span');
                newBadge.className = 'status-badge-modern badge-comprado text-xs';
                newBadge.textContent = 'COMPRADO';

                if (badgeContainer) {
                    badgeContainer.innerHTML = '';
                    badgeContainer.appendChild(newBadge);
                }
            }
        } else {
            // Remover badge se existir
            if (badgeContainer) {
                badgeContainer.innerHTML = '';
            }
        }

        console.log(`[WebSocket] Item ${itemData.id} atualizado: comprado=${itemData.comprado}`);
    }

    handleCompraConfirmada(produto) {
        console.log('[WebSocket] Compra confirmada:', produto);
        // Recarregar a página para atualizar a lista
        window.location.reload();
    }

    handleItemSeparadoDireto(item) {
        console.log('[WebSocket] Item separado direto do estoque:', item);

        try {
            // Obter componente Alpine via _x_dataStack
            const component = document.querySelector('[x-data="painelComprasApp()"]');

            if (!component || !component._x_dataStack) {
                console.warn('[WebSocket] Alpine.js app não encontrado, recarregando página...');
                window.location.reload();
                return;
            }

            // Acessar dados reativos do Alpine
            const alpineData = component._x_dataStack[0];

            // Encontrar o pedido que contém o item
            const pedido = alpineData.pedidos.find(p =>
                p.itens.some(i => i.id === item.id)
            );

            if (!pedido) {
                console.warn('[WebSocket] Pedido não encontrado para o item:', item.id);
                return;
            }

            // Remover o item do array de itens
            const itemIndex = pedido.itens.findIndex(i => i.id === item.id);
            if (itemIndex !== -1) {
                pedido.itens.splice(itemIndex, 1);
                console.log(`[WebSocket] Item ${item.id} removido do pedido ${pedido.numero}`);
                console.log('[WebSocket] Total de itens restantes no pedido:', pedido.itens.length);
            }

            // Se o pedido ficou sem itens, remover o pedido
            if (pedido.itens.length === 0) {
                const pedidoIndex = alpineData.pedidos.findIndex(p => p.id === pedido.id);
                if (pedidoIndex !== -1) {
                    alpineData.pedidos.splice(pedidoIndex, 1);
                    console.log(`[WebSocket] Pedido ${pedido.numero} removido (sem itens)`);
                }
            }

            // Forçar re-filter para atualizar a UI
            alpineData.filterOrders();

        } catch (error) {
            console.error('[WebSocket] Erro ao remover item dinamicamente, recarregando:', error);
            window.location.reload();
        }
    }

    handleItemRemovidoCompras(itemId, pedidoId) {
        console.log('[WebSocket] Item removido do painel de compras (unseparate):', {itemId, pedidoId});

        try {
            // Obter componente Alpine via _x_dataStack
            const component = document.querySelector('[x-data="painelComprasApp()"]');

            if (!component || !component._x_dataStack) {
                console.warn('[WebSocket] Alpine.js app não encontrado, recarregando página...');
                window.location.reload();
                return;
            }

            // Acessar dados reativos do Alpine
            const alpineData = component._x_dataStack[0];

            // Encontrar o pedido pelo ID
            const pedido = alpineData.pedidos.find(p => p.id === pedidoId);

            if (!pedido) {
                console.warn('[WebSocket] Pedido não encontrado para ID:', pedidoId);
                return;
            }

            // Remover o item do array de itens
            const itemIndex = pedido.itens.findIndex(i => i.id === itemId);
            if (itemIndex !== -1) {
                pedido.itens.splice(itemIndex, 1);
                console.log(`[WebSocket] Item ${itemId} removido do pedido ${pedido.numero} (unseparate)`);
                console.log('[WebSocket] Total de itens restantes no pedido:', pedido.itens.length);
            }

            // Se o pedido ficou sem itens, remover o pedido
            if (pedido.itens.length === 0) {
                const pedidoIndex = alpineData.pedidos.findIndex(p => p.id === pedido.id);
                if (pedidoIndex !== -1) {
                    alpineData.pedidos.splice(pedidoIndex, 1);
                    console.log(`[WebSocket] Pedido ${pedido.numero} removido (sem itens)`);
                }
            }

            // Forçar re-filter para atualizar a UI
            alpineData.filterOrders();

        } catch (error) {
            console.error('[WebSocket] Erro ao remover item dinamicamente (unseparate), recarregando:', error);
            window.location.reload();
        }
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
        pedidos: window.pedidosData || [],
        filteredOrders: [],
        searchText: '',
        orderFilter: '',

        // Initialization
        init() {
            console.log('[PainelComprasApp] Inicializando...');
            console.log('[PainelComprasApp] window.pedidosData:', window.pedidosData);
            console.log('[PainelComprasApp] Total pedidos carregados:', this.pedidos.length);

            if (this.pedidos.length > 0) {
                console.log('[PainelComprasApp] Primeiro pedido:', this.pedidos[0]);
            } else {
                console.warn('[PainelComprasApp] AVISO: Nenhum pedido encontrado!');
            }

            // Set filtered orders - use spread to create copy, not reference
            this.filteredOrders = [...this.pedidos];
            console.log('[PainelComprasApp] Pedidos filtrados iniciais:', this.filteredOrders.length);

            // Ensure search fields are cleared (fix browser autocomplete bugs)
            this.searchText = '';
            this.orderFilter = '';

            // Clear input values via DOM to override any browser autocomplete
            const searchInput = document.getElementById('searchText');
            const orderInput = document.getElementById('orderFilter');
            if (searchInput) searchInput.value = '';
            if (orderInput) orderInput.value = '';

            // Mark Alpine as fully initialized
            console.log('[PainelComprasApp] Alpine.js inicialização completa');
            console.log('[PainelComprasApp] Aguardando 200ms para garantir que Alpine está 100% pronto...');

            // WebSocket será iniciado externamente após Alpine estar pronto
            // Não inicializar aqui para evitar race condition
        },

        // Filter orders
        filterOrders() {
            let filtered = this.pedidos;

            // Filtro por texto (código do produto, descrição ou cliente)
            if (this.searchText.trim()) {
                const search = this.searchText.toLowerCase().trim();
                filtered = filtered.filter(pedido => {
                    // Buscar no cliente
                    const clienteMatch = pedido.cliente.toLowerCase().includes(search);

                    // Buscar nos itens (código ou descrição)
                    const itemsMatch = pedido.itens.some(item =>
                        item.produto_codigo.toLowerCase().includes(search) ||
                        item.produto_descricao.toLowerCase().includes(search)
                    );

                    return clienteMatch || itemsMatch;
                });
            }

            // Filtro por número do pedido
            if (this.orderFilter.trim()) {
                const orderSearch = this.orderFilter.toLowerCase().trim();
                filtered = filtered.filter(pedido =>
                    pedido.numero.toLowerCase().includes(orderSearch)
                );
            }

            this.filteredOrders = filtered;
            console.log('[PainelComprasApp] Pedidos filtrados:', this.filteredOrders.length);
        },

        // Toggle item comprado (checkbox handler)
        async toggleItemComprado(pedidoId, itemId, checked) {
            console.log(`[PainelComprasApp] Toggling item ${itemId} do pedido ${pedidoId}: ${checked}`);

            try {
                const response = await fetch(`/pedidos/item/${itemId}/marcar-comprado/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify({ comprado: checked })
                });

                const data = await response.json();

                if (data.success) {
                    console.log('[PainelComprasApp] Item atualizado com sucesso!', data);

                    // Atualizar o estado local do item
                    const pedido = this.pedidos.find(p => p.id === pedidoId);
                    if (pedido) {
                        const item = pedido.itens.find(i => i.id === itemId);
                        if (item) {
                            item.comprado = data.comprado;
                        }
                    }

                    // WebSocket vai atualizar os outros clientes automaticamente
                } else {
                    console.error('[PainelComprasApp] Erro ao atualizar item:', data.error);
                    alert(`Erro: ${data.error}`);

                    // Reverter o checkbox se falhou
                    const checkbox = document.querySelector(`#item-${itemId}`);
                    if (checkbox) {
                        checkbox.checked = !checked;
                    }
                }
            } catch (error) {
                console.error('[PainelComprasApp] Erro na requisição:', error);
                alert('Erro ao atualizar item. Por favor, tente novamente.');

                // Reverter o checkbox se falhou
                const checkbox = document.querySelector(`#item-${itemId}`);
                if (checkbox) {
                    checkbox.checked = !checked;
                }
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

// ============================================
// EXTERNAL WEBSOCKET INITIALIZATION
// ============================================
// This code runs AFTER Alpine.js is fully initialized to prevent race conditions.
// WebSocket messages that arrive before Alpine is ready will no longer cause failures.

document.addEventListener('DOMContentLoaded', () => {
    console.log('[PainelCompras] DOMContentLoaded fired, waiting for Alpine.js...');

    // Wait for Alpine.js to be fully initialized
    const initializeWebSocket = () => {
        const component = document.querySelector('[x-data="painelComprasApp()"]');

        if (!component || !component._x_dataStack) {
            console.warn('[PainelCompras] Alpine.js not ready yet, retrying in 100ms...');
            setTimeout(initializeWebSocket, 100);
            return;
        }

        // Alpine is ready! Wait extra 200ms to ensure 100% stability
        console.log('[PainelCompras] Alpine.js detected, waiting 200ms for stability...');

        setTimeout(() => {
            console.log('[PainelCompras] Initializing WebSocket NOW...');

            try {
                // Get Alpine data to pass to WebSocket
                const alpineData = component._x_dataStack[0];

                // Initialize WebSocket and store reference globally
                window.painelComprasWs = new PainelComprasWebSocket();

                console.log('[PainelCompras] ✅ WebSocket initialized successfully!');
                console.log('[PainelCompras] WebSocket URL:', window.painelComprasWs.wsUrl);
                console.log('[PainelCompras] Alpine.js data available:', !!alpineData);
                console.log('[PainelCompras] Current pedidos count:', alpineData.pedidos?.length || 0);
            } catch (error) {
                console.error('[PainelCompras] ❌ Failed to initialize WebSocket:', error);
                // Don't reload on initialization error - allow page to function without realtime
            }
        }, 200);
    };

    // Start initialization process
    initializeWebSocket();
});
