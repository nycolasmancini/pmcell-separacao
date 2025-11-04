from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils import timezone
from .models import Usuario, Pedido, ItemPedido, Produto, LogAuditoria


class UsuarioAdmin(BaseUserAdmin):
    """Admin customizado para o modelo Usuario"""

    list_display = ('numero_login', 'nome', 'tipo', 'ativo', 'ultimo_acesso', 'get_status_bloqueio')
    list_filter = ('tipo', 'ativo', 'criado_em')
    search_fields = ('numero_login', 'nome')
    ordering = ('numero_login',)

    fieldsets = (
        ('Dados de Acesso', {
            'fields': ('numero_login', 'pin_hash')
        }),
        ('Informações Pessoais', {
            'fields': ('nome', 'tipo')
        }),
        ('Status', {
            'fields': ('ativo', 'ultimo_acesso', 'tentativas_login', 'bloqueado_ate')
        }),
        ('Permissões Django Admin', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('criado_em', 'atualizado_em', 'ultimo_acesso')

    def get_status_bloqueio(self, obj):
        """Mostra status de bloqueio colorido"""
        if obj.bloqueado_ate and timezone.now() < obj.bloqueado_ate:
            return format_html(
                '<span style="color: red; font-weight: bold;">BLOQUEADO até {}</span>',
                obj.bloqueado_ate.strftime('%d/%m/%Y %H:%M')
            )
        return format_html('<span style="color: green;">Liberado</span>')

    get_status_bloqueio.short_description = 'Status de Bloqueio'

    def save_model(self, request, obj, form, change):
        """Customiza o salvamento para lidar com PIN"""
        # Se está criando um novo usuário e há um campo 'pin' temporário
        if not change and hasattr(form, 'cleaned_data') and 'pin' in form.cleaned_data:
            obj.set_pin(form.cleaned_data['pin'])
        super().save_model(request, obj, form, change)


class ItemPedidoInline(admin.TabularInline):
    """Inline para exibir itens do pedido dentro do admin de Pedido"""
    model = ItemPedido
    extra = 0
    readonly_fields = ('separado', 'separado_por', 'separado_em', 'em_compra',
                       'marcado_compra_por', 'marcado_compra_em', 'compra_realizada',
                       'compra_realizada_por', 'compra_realizada_em')
    fields = ('produto', 'quantidade_solicitada', 'preco_unitario', 'separado',
              'em_compra', 'substituido', 'produto_substituto')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    """Admin para o modelo Pedido"""

    list_display = ('numero_orcamento', 'nome_cliente', 'vendedor', 'data', 'get_status_badge',
                    'data_criacao', 'get_deletado_status')
    list_filter = ('status', 'deletado', 'data', 'data_criacao', 'vendedor')
    search_fields = ('numero_orcamento', 'nome_cliente', 'codigo_cliente')
    date_hierarchy = 'data_criacao'
    ordering = ('-data_criacao',)
    inlines = [ItemPedidoInline]

    fieldsets = (
        ('Informações do Orçamento', {
            'fields': ('numero_orcamento', 'codigo_cliente', 'nome_cliente', 'vendedor', 'data')
        }),
        ('Detalhes', {
            'fields': ('logistica', 'embalagem', 'observacoes')
        }),
        ('Status', {
            'fields': ('status', 'data_criacao', 'data_finalizacao')
        }),
        ('Soft Delete', {
            'fields': ('deletado', 'deletado_por', 'deletado_em'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('data_criacao', 'data_finalizacao')

    def get_status_badge(self, obj):
        """Exibe status com cores"""
        colors = {
            'PENDENTE': '#FFA500',  # Laranja
            'EM_SEPARACAO': '#1E90FF',  # Azul
            'AGUARDANDO_COMPRA': '#9370DB',  # Roxo
            'FINALIZADO': '#32CD32',  # Verde
            'CANCELADO': '#DC143C',  # Vermelho
        }
        color = colors.get(obj.status, '#808080')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    get_status_badge.short_description = 'Status'

    def get_deletado_status(self, obj):
        """Mostra se o pedido foi deletado"""
        if obj.deletado:
            return format_html('<span style="color: red;">✖ Deletado</span>')
        return format_html('<span style="color: green;">✓ Ativo</span>')

    get_deletado_status.short_description = 'Status Exclusão'


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    """Admin para o modelo ItemPedido"""

    list_display = ('pedido', 'produto', 'quantidade_solicitada', 'preco_unitario',
                    'get_separado_badge', 'get_compra_badge', 'get_substituido_badge')
    list_filter = ('separado', 'em_compra', 'substituido', 'compra_realizada')
    search_fields = ('pedido__numero_orcamento', 'produto__codigo', 'produto__descricao')
    ordering = ('-pedido__data_criacao',)

    fieldsets = (
        ('Pedido e Produto', {
            'fields': ('pedido', 'produto', 'quantidade_solicitada', 'preco_unitario')
        }),
        ('Separação', {
            'fields': ('separado', 'separado_por', 'separado_em')
        }),
        ('Compra', {
            'fields': ('em_compra', 'marcado_compra_por', 'marcado_compra_em',
                       'compra_realizada', 'compra_realizada_por', 'compra_realizada_em')
        }),
        ('Substituição', {
            'fields': ('substituido', 'produto_substituto')
        }),
    )

    readonly_fields = ('separado_por', 'separado_em', 'marcado_compra_por',
                       'marcado_compra_em', 'compra_realizada_por', 'compra_realizada_em')

    def get_separado_badge(self, obj):
        """Badge de separação"""
        if obj.separado:
            return format_html('<span style="color: green;">✓ Separado</span>')
        return format_html('<span style="color: gray;">Pendente</span>')

    get_separado_badge.short_description = 'Separação'

    def get_compra_badge(self, obj):
        """Badge de compra"""
        if obj.compra_realizada:
            return format_html('<span style="color: green;">✓ Comprado</span>')
        elif obj.em_compra:
            return format_html('<span style="color: orange;">Em Compra</span>')
        return format_html('<span style="color: gray;">-</span>')

    get_compra_badge.short_description = 'Compra'

    def get_substituido_badge(self, obj):
        """Badge de substituição"""
        if obj.substituido:
            return format_html(
                '<span style="color: blue;">✓ Subst: {}</span>',
                obj.produto_substituto
            )
        return format_html('<span style="color: gray;">-</span>')

    get_substituido_badge.short_description = 'Substituição'


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    """Admin para o modelo Produto"""

    list_display = ('codigo', 'descricao', 'criado_automaticamente', 'criado_em')
    list_filter = ('criado_automaticamente', 'criado_em')
    search_fields = ('codigo', 'descricao')
    ordering = ('codigo',)

    fieldsets = (
        ('Informações do Produto', {
            'fields': ('codigo', 'descricao')
        }),
        ('Metadados', {
            'fields': ('criado_automaticamente', 'criado_em', 'atualizado_em')
        }),
    )

    readonly_fields = ('criado_em', 'atualizado_em')


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    """Admin para o modelo LogAuditoria"""

    list_display = ('timestamp', 'usuario', 'acao', 'modelo', 'objeto_id', 'ip')
    list_filter = ('acao', 'modelo', 'timestamp')
    search_fields = ('usuario__nome', 'acao', 'modelo', 'ip')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)

    fieldsets = (
        ('Informações da Ação', {
            'fields': ('usuario', 'acao', 'modelo', 'objeto_id')
        }),
        ('Dados', {
            'fields': ('dados_anteriores', 'dados_novos')
        }),
        ('Metadados', {
            'fields': ('ip', 'user_agent', 'timestamp')
        }),
    )

    readonly_fields = ('timestamp',)

    def has_add_permission(self, request):
        """Não permite adicionar logs manualmente"""
        return False

    def has_change_permission(self, request, obj=None):
        """Não permite editar logs"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Não permite deletar logs"""
        return False


# Desregistrar o modelo User padrão do Django se estiver registrado
from django.contrib.auth.models import User as DjangoUser
try:
    admin.site.unregister(DjangoUser)
except admin.sites.NotRegistered:
    pass

# Registrar o Usuario customizado
admin.site.register(Usuario, UsuarioAdmin)
