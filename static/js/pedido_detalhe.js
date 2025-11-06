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
            // Update checkbox
            const checkbox = row.querySelector('.item-checkbox');
            if (checkbox) {
                checkbox.checked = true;
            }

            // Add separated class to row
            row.classList.add('row-separated');

            // Add strikethrough to description
            const description = row.querySelector('.item-description');
            if (description) {
                description.classList.add('line-through');
            }

            // Update status badge
            const statusBadge = row.querySelector('.status-badge');
            if (statusBadge) {
                statusBadge.className = 'status-badge px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800';
                statusBadge.innerHTML = `
                    <span class="status-text">✓ Separado</span>
                `;
            }

            // Add timestamp below status
            const statusCell = row.querySelector('td:nth-child(5)');
            if (statusCell) {
                const existingTimestamp = statusCell.querySelector('.text-xs.text-gray-500.mt-1');
                if (!existingTimestamp) {
                    const timestampDiv = document.createElement('div');
                    timestampDiv.className = 'text-xs text-gray-500 mt-1';
                    timestampDiv.textContent = `${item.separado_por} - ${item.separado_em}`;
                    statusCell.appendChild(timestampDiv);
                }
            }

            // Update statistics without full page reload
            this.updateStatistics();
        }
    }

    updateStatistics() {
        // Update statistics cards dynamically
        const separatedCheckboxes = document.querySelectorAll('.item-checkbox:checked');
        const separatedCount = separatedCheckboxes.length;
        const totalItems = document.querySelectorAll('.item-checkbox').length;
        const progress = totalItems > 0 ? Math.round((separatedCount / totalItems) * 100) : 0;

        // Update "Separados" count
        const separadosElement = document.querySelector('.bg-white.rounded-lg.shadow.p-4.text-center .text-2xl.font-bold.text-green-600');
        if (separadosElement) {
            separadosElement.textContent = separatedCount;
        }

        // Update progress bar
        const progressBar = document.querySelector('.bg-green-600.h-2.rounded-full');
        const progressText = document.querySelector('.text-sm.font-bold.text-gray-800');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        if (progressText) {
            progressText.textContent = `${progress}%`;
        }
    }

    handleItemEmCompra(item) {
        console.log('[WebSocket] Item em compra:', item);

        const row = document.querySelector(`tr[data-item-id="${item.id}"]`);
        if (row) {
            const statusCell = row.querySelector('td:nth-child(5)');
            if (statusCell) {
                const statusBadge = statusCell.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.className = 'status-badge px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800';
                    statusBadge.innerHTML = `<span class="status-text">🛒 Em Compra</span>`;
                }

                // Add timestamp if not exists
                const existingTimestamp = statusCell.querySelector('.text-xs.text-gray-500.mt-1');
                if (!existingTimestamp) {
                    const timestampDiv = document.createElement('div');
                    timestampDiv.className = 'text-xs text-gray-500 mt-1';
                    timestampDiv.textContent = `${item.marcado_compra_por} - ${item.marcado_compra_em}`;
                    statusCell.appendChild(timestampDiv);
                }
            }

            // Update "Em Compra" statistics
            const emCompraCount = document.querySelectorAll('.status-badge.bg-yellow-100').length;
            const emCompraElement = document.querySelector('.bg-white.rounded-lg.shadow.p-4.text-center .text-2xl.font-bold.text-yellow-600');
            if (emCompraElement) {
                emCompraElement.textContent = emCompraCount;
            }
        }
    }

    handleItemSubstituido(item) {
        console.log('[WebSocket] Item substituído:', item);

        const row = document.querySelector(`tr[data-item-id="${item.id}"]`);
        if (row) {
            // Atualizar descrição do produto
            const produtoCell = row.querySelector('td:nth-child(2)');
            if (produtoCell) {
                const descDiv = produtoCell.querySelector('.item-description');
                if (descDiv && descDiv.parentElement) {
                    // Check if substitution info already exists
                    const existingSubInfo = descDiv.parentElement.querySelector('.text-xs.text-blue-600');
                    if (!existingSubInfo) {
                        const subDiv = document.createElement('div');
                        subDiv.className = 'text-xs text-blue-600 mt-1';
                        subDiv.innerHTML = `Substituído por: <strong>${item.produto_substituto}</strong>`;
                        descDiv.parentElement.appendChild(subDiv);
                    }
                }
            }

            // Atualizar status
            const statusCell = row.querySelector('td:nth-child(5)');
            if (statusCell) {
                const statusBadge = statusCell.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.className = 'status-badge px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800';
                    statusBadge.innerHTML = `<span class="status-text">↔ Substituído</span>`;
                }
            }

            // Update "Substituídos" statistics
            const substituidosCount = document.querySelectorAll('.status-badge.bg-blue-100').length;
            const substituidosElement = document.querySelector('.bg-white.rounded-lg.shadow.p-4.text-center .text-2xl.font-bold.text-blue-600');
            if (substituidosElement) {
                substituidosElement.textContent = substituidosCount;
            }
        }
    }

    handlePedidoAtualizado(pedido) {
        console.log('[WebSocket] Pedido atualizado:', pedido);
        // Update status display dynamically instead of reloading
        const statusElement = document.querySelector('.text-lg.font-bold');
        if (statusElement && pedido.status) {
            // Update status text
            const statusMap = {
                'PENDENTE': 'Pendente',
                'EM_SEPARACAO': 'Em Separação',
                'AGUARDANDO_COMPRA': 'Aguardando Compra',
                'FINALIZADO': 'Finalizado'
            };
            statusElement.textContent = statusMap[pedido.status] || pedido.status;

            // Update status color
            statusElement.className = 'text-lg font-bold';
            if (pedido.status === 'PENDENTE') statusElement.classList.add('text-gray-600');
            else if (pedido.status === 'EM_SEPARACAO') statusElement.classList.add('text-blue-600');
            else if (pedido.status === 'AGUARDANDO_COMPRA') statusElement.classList.add('text-yellow-600');
            else if (pedido.status === 'FINALIZADO') statusElement.classList.add('text-green-600');
        }
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

        // Track separated items for dynamic styling
        itemsSeparados: [],

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

            // Initialize itemsSeparados with already separated items
            document.querySelectorAll('.item-checkbox:checked').forEach(checkbox => {
                const itemId = parseInt(checkbox.dataset.itemId);
                if (!this.itemsSeparados.includes(itemId)) {
                    this.itemsSeparados.push(itemId);
                }
            });
        },

        // Handle checkbox change for item separation
        async handleCheckboxChange(itemId, isChecked) {
            if (isChecked) {
                // Separate item
                if (!confirm('Confirma a separação deste item?')) {
                    // Revert checkbox if user cancels
                    const checkbox = document.querySelector(`.item-checkbox[data-item-id="${itemId}"]`);
                    if (checkbox) checkbox.checked = false;
                    return;
                }

                try {
                    console.log(`[CHECKBOX] Enviando requisição para separar item ${itemId}...`);

                    const response = await fetch(`/pedidos/item/${itemId}/separar/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.getCsrfToken()
                        }
                    });

                    console.log(`[CHECKBOX] Response status: ${response.status} ${response.statusText}`);

                    // Check if response is OK before parsing JSON
                    if (!response.ok) {
                        const errorText = await response.text();
                        console.error(`[CHECKBOX] Erro HTTP ${response.status}:`, errorText);
                        alert(`Erro ao separar item (HTTP ${response.status}). Verifique o console para detalhes.`);
                        this.revertVisualFeedback(itemId);
                        return;
                    }

                    const data = await response.json();
                    console.log('[CHECKBOX] Response data:', data);

                    if (data.success) {
                        console.log('✓ [CHECKBOX] Item separado com sucesso:', data);

                        // Add to separated items array
                        if (!this.itemsSeparados.includes(itemId)) {
                            this.itemsSeparados.push(itemId);
                        }

                        // Apply visual feedback ONLY after server confirms success
                        this.applyVisualFeedback(itemId, true);

                        // WebSocket will also handle updates
                    } else {
                        console.error('✗ [CHECKBOX] Servidor retornou erro:', data.error);
                        alert('Erro: ' + (data.error || 'Erro ao separar item'));
                        // Revert checkbox and visual feedback
                        this.revertVisualFeedback(itemId);
                    }
                } catch (error) {
                    console.error('✗ [CHECKBOX] Exceção ao separar item:', error);
                    alert(`Erro ao separar item: ${error.message}\nVerifique o console para mais detalhes.`);
                    // Revert checkbox and visual feedback
                    this.revertVisualFeedback(itemId);
                }
            } else {
                // Prevent unchecking - we don't allow unseparating items
                const checkbox = document.querySelector(`.item-checkbox[data-item-id="${itemId}"]`);
                if (checkbox) checkbox.checked = true;
            }
        },

        // Apply visual feedback to separated items
        applyVisualFeedback(itemId, isSeparated) {
            const row = document.querySelector(`tr[data-item-id="${itemId}"]`);
            if (!row) return;

            if (isSeparated) {
                // Add separated class to row
                row.classList.add('row-separated');

                // Add strikethrough to description
                const description = row.querySelector('.item-description');
                if (description) {
                    description.classList.add('line-through');
                }

                // Update status badge
                const statusBadge = row.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.className = 'status-badge px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800';
                    const statusText = statusBadge.querySelector('.status-text');
                    if (statusText) {
                        statusText.textContent = '✓ Separado';
                    }
                }
            }
        },

        // Revert visual feedback when operation fails
        revertVisualFeedback(itemId) {
            // Revert checkbox
            const checkbox = document.querySelector(`.item-checkbox[data-item-id="${itemId}"]`);
            if (checkbox) checkbox.checked = false;

            // Remove from separated items array
            const index = this.itemsSeparados.indexOf(itemId);
            if (index > -1) {
                this.itemsSeparados.splice(index, 1);
            }

            // Remove visual styling
            const row = document.querySelector(`tr[data-item-id="${itemId}"]`);
            if (row) {
                row.classList.remove('row-separated');

                const description = row.querySelector('.item-description');
                if (description) {
                    description.classList.remove('line-through');
                }

                // Reset status badge to original state
                const statusBadge = row.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.className = 'status-badge px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800';
                    const statusText = statusBadge.querySelector('.status-text');
                    if (statusText) {
                        statusText.textContent = '⏳ Pendente';
                    }
                }
            }
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

// Make pedidoDetalheApp globally available for Alpine.js
window.pedidoDetalheApp = pedidoDetalheApp;

// Limpar WebSocket ao sair da página
window.addEventListener('beforeunload', () => {
    if (window.pedidoWs) {
        window.pedidoWs.close();
    }
});
