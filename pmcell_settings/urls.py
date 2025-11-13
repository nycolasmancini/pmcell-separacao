"""
URL configuration for pmcell_settings project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from .views import home_view
from apps.core.views import (
    login_view,
    logout_view,
    dashboard,
    reset_pin_view,
    upload_pdf_view,
    confirmar_pedido_view,
    pedido_detalhe_view,
    separar_item_view,
    unseparar_item_view,
    marcar_compra_view,
    marcar_item_comprado_view,
    substituir_item_view,
    finalizar_pedido_view,
    deletar_pedido_view,
    painel_compras_view,
    confirmar_compra_view,
    historico_compras_view,
    lista_usuarios_view,
    criar_usuario_view,
    editar_usuario_view,
    resetar_pin_usuario_view,
    toggle_ativo_usuario_view,
    historico_view,
    metricas_view,
    configurar_empty_state_view,
)

urlpatterns = [
    # Home (redireciona para login ou dashboard)
    path('', home_view, name='home'),

    # Autenticação
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # Dashboard
    path('dashboard/', dashboard, name='dashboard'),

    # Upload de PDF (FASE 3)
    path('pedidos/upload-pdf/', upload_pdf_view, name='upload_pdf'),
    path('pedidos/confirmar/', confirmar_pedido_view, name='confirmar_pedido'),
    path('pedidos/<int:pedido_id>/', pedido_detalhe_view, name='pedido_detalhe'),

    # Ações de Separação (FASE 5)
    path('pedidos/item/<int:item_id>/separar/', separar_item_view, name='separar_item'),
    path('pedidos/item/<int:item_id>/unseparar/', unseparar_item_view, name='unseparar_item'),
    path('pedidos/item/<int:item_id>/marcar-compra/', marcar_compra_view, name='marcar_compra'),
    path('pedidos/item/<int:item_id>/marcar-comprado/', marcar_item_comprado_view, name='marcar_item_comprado'),
    path('pedidos/item/<int:item_id>/substituir/', substituir_item_view, name='substituir_item'),
    path('pedidos/<int:pedido_id>/finalizar/', finalizar_pedido_view, name='finalizar_pedido'),
    path('pedidos/<int:pedido_id>/deletar/', deletar_pedido_view, name='deletar_pedido'),

    # Painel de Compras (FASE 6)
    path('painel-compras/', painel_compras_view, name='painel_compras'),
    path('painel-compras/confirmar/<str:produto_codigo>/', confirmar_compra_view, name='confirmar_compra'),
    path('painel-compras/historico/', historico_compras_view, name='historico_compras'),

    # Admin - Reset PIN (legado, manter para compatibilidade)
    path('admin/reset-pin/<int:user_id>/', reset_pin_view, name='reset_pin'),

    # Gestão de Usuários (FASE 7)
    path('usuarios/', lista_usuarios_view, name='lista_usuarios'),
    path('usuarios/criar/', criar_usuario_view, name='criar_usuario'),
    path('usuarios/<int:usuario_id>/editar/', editar_usuario_view, name='editar_usuario'),
    path('usuarios/<int:usuario_id>/resetar-pin/', resetar_pin_usuario_view, name='resetar_pin_usuario'),
    path('usuarios/<int:usuario_id>/toggle-ativo/', toggle_ativo_usuario_view, name='toggle_ativo_usuario'),

    # Histórico e Métricas (FASE 8)
    path('historico/', historico_view, name='historico'),
    path('metricas/', metricas_view, name='metricas'),

    # Configuração do Sistema (FASE 9)
    path('config/empty-state/', configurar_empty_state_view, name='configurar_empty_state'),

    # Django Admin
    path('admin/', admin.site.urls),
]

# Serve media files
# Production: Use Django's serve view (WhiteNoise cannot serve user-uploaded media files)
# Development: Use static() helper which automatically serves media files
if not settings.DEBUG:
    # Production - serve media files via Django's serve view
    urlpatterns += [
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
else:
    # Development - use static() helper for convenience
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
