/**
 * PMCell Card System - Dynamic Progress and Animations
 * Handles progress calculations and card updates
 */

(function() {
    'use strict';

    // Card Progress Manager
    const CardProgress = {
        /**
         * Initialize all progress bars on the page
         */
        init: function() {
            this.updateAllProgressBars();
            this.setupWebSocketListeners();
            this.setupAnimations();
        },

        /**
         * Update all progress bars based on data attributes
         */
        updateAllProgressBars: function() {
            const progressBars = document.querySelectorAll('.progress-bar-fill');
            progressBars.forEach(bar => {
                const progress = bar.dataset.progress || 0;
                this.animateProgressBar(bar, progress);
            });
        },

        /**
         * Animate a single progress bar
         */
        animateProgressBar: function(bar, targetProgress) {
            // Reset to 0 for animation
            bar.style.width = '0%';

            // Trigger reflow
            void bar.offsetWidth;

            // Animate to target
            setTimeout(() => {
                bar.style.width = `${targetProgress}%`;
            }, 100);
        },

        /**
         * Calculate progress percentage
         * Note: substituídos já são contados como separados no backend, não somar duas vezes
         */
        calculateProgress: function(separated, substituted, total) {
            if (total === 0) return 0;
            // Apenas usar 'separated' porque substituídos já têm separado=True
            return Math.round((separated / total) * 100);
        },

        /**
         * Update a specific card's progress
         */
        updateCardProgress: function(cardId, separated, substituted, total) {
            const card = document.querySelector(`[data-pedido-id="${cardId}"]`);
            if (!card) return;

            const progressBar = card.querySelector('.progress-bar-fill');
            const progressText = card.querySelector('.progress-text');

            if (progressBar) {
                const progress = this.calculateProgress(separated, substituted, total);
                progressBar.dataset.progress = progress;
                this.animateProgressBar(progressBar, progress);
            }

            if (progressText) {
                const progress = this.calculateProgress(separated, substituted, total);
                progressText.textContent = `${progress}%`;
            }
        },

        /**
         * Setup WebSocket listeners for real-time updates
         */
        setupWebSocketListeners: function() {
            // Listen for custom events from WebSocket
            document.addEventListener('pedido-updated', (event) => {
                const { pedidoId, itemsSeparados, itemsSubstituidos, totalItems } = event.detail;
                this.updateCardProgress(pedidoId, itemsSeparados, itemsSubstituidos, totalItems);
            });

            // Listen for status changes
            document.addEventListener('pedido-status-changed', (event) => {
                const { pedidoId, newStatus, statusDisplay } = event.detail;
                this.updateCardStatus(pedidoId, newStatus, statusDisplay);
            });
        },

        /**
         * Update card status and border color
         */
        updateCardStatus: function(pedidoId, newStatus, statusDisplay) {
            const card = document.querySelector(`[data-pedido-id="${pedidoId}"]`);
            if (!card) return;

            // Update border color
            const borderTop = card.querySelector('.card-border-top');
            if (borderTop) {
                // Remove all status classes
                borderTop.className = 'card-border-top';

                // Add new status class
                const statusClass = this.getStatusClass(newStatus);
                borderTop.classList.add(statusClass);
            }

            // Update status badge
            const statusBadge = card.querySelector('[data-status]');
            if (statusBadge) {
                statusBadge.textContent = statusDisplay;

                // Update badge color classes
                statusBadge.className = 'status-badge-modern';
                const badgeClass = this.getBadgeClass(newStatus);
                statusBadge.classList.add(badgeClass);
            }

            // Add pulse animation for status change
            card.classList.add('pulse-once');
            setTimeout(() => {
                card.classList.remove('pulse-once');
            }, 1000);
        },

        /**
         * Get border class for status
         */
        getStatusClass: function(status) {
            const statusMap = {
                'PENDENTE': 'card-border-pendente',
                'EM_SEPARACAO': 'card-border-em-separacao',
                'AGUARDANDO_COMPRA': 'card-border-aguardando-compra',
                'FINALIZADO': 'card-border-finalizado',
                'CANCELADO': 'card-border-cancelado'
            };
            return statusMap[status] || 'card-border-pendente';
        },

        /**
         * Get badge class for status
         */
        getBadgeClass: function(status) {
            const badgeMap = {
                'PENDENTE': 'badge-pendente',
                'EM_SEPARACAO': 'badge-em-separacao',
                'AGUARDANDO_COMPRA': 'badge-aguardando-compra',
                'FINALIZADO': 'badge-finalizado',
                'CANCELADO': 'badge-cancelado'
            };
            return badgeMap[status] || 'badge-pendente';
        },

        /**
         * Setup card animations and interactions
         */
        setupAnimations: function() {
            // Add hover effects
            const cards = document.querySelectorAll('.card-modern');
            cards.forEach(card => {
                card.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-2px)';
                });

                card.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                });
            });

            // Setup expandable cards
            const expandableCards = document.querySelectorAll('.card-expandable');
            expandableCards.forEach(card => {
                const expandTrigger = card.querySelector('[data-expand]');
                if (expandTrigger) {
                    expandTrigger.addEventListener('click', () => {
                        card.classList.toggle('card-expanded');
                    });
                }
            });
        }
    };

    // Utility functions for external use
    window.CardSystem = {
        /**
         * Update progress for a specific order
         */
        updateOrderProgress: function(orderId, data) {
            CardProgress.updateCardProgress(
                orderId,
                data.separated || 0,
                data.substituted || 0,
                data.total || 0
            );
        },

        /**
         * Update order status
         */
        updateOrderStatus: function(orderId, status, displayText) {
            CardProgress.updateCardStatus(orderId, status, displayText);
        },

        /**
         * Trigger a card highlight animation
         */
        highlightCard: function(orderId) {
            const card = document.querySelector(`[data-pedido-id="${orderId}"]`);
            if (card) {
                card.classList.add('highlight-card');
                setTimeout(() => {
                    card.classList.remove('highlight-card');
                }, 2000);
            }
        },

        /**
         * Refresh all progress bars
         */
        refreshAllProgress: function() {
            CardProgress.updateAllProgressBars();
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            CardProgress.init();
        });
    } else {
        CardProgress.init();
    }

    // Add custom styles for animations
    const style = document.createElement('style');
    style.textContent = `
        .pulse-once {
            animation: pulse-animation 1s ease-in-out;
        }

        @keyframes pulse-animation {
            0%, 100% {
                transform: scale(1);
            }
            50% {
                transform: scale(1.02);
            }
        }

        .highlight-card {
            animation: highlight-animation 2s ease-in-out;
        }

        @keyframes highlight-animation {
            0%, 100% {
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
            }
            50% {
                box-shadow: 0 0 20px 5px rgba(59, 130, 246, 0.5);
            }
        }
    `;
    document.head.appendChild(style);

})();