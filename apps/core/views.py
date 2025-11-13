from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from datetime import timedelta, datetime, date
import copy
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Usuario, LogAuditoria, Pedido, ItemPedido, Produto, SistemaConfig
from .forms import (
    CriarUsuarioForm,
    EditarUsuarioForm,
    ResetarPinForm,
    HistoricoFiltrosForm,
    EmptyStateImageForm,
)
from .permissions import (
    login_required_custom,
    administrador_required,
    separador_required,
    compradora_required,
    admin_or_separador,
    admin_or_compradora,
)


# =====================
# SISTEMA DE AUTENTICAÇÃO - FASE 2
# =====================

def get_client_ip(request):
    """Obtém o IP real do cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# =====================
# WEBSOCKET HELPER FUNCTIONS
# =====================

logger = logging.getLogger(__name__)


def broadcast_to_websocket(group_name, message_type, data):
    """
    Helper function for WebSocket broadcasts with error handling

    Args:
        group_name: The channel group name to broadcast to
        message_type: The type of message (e.g., 'item_separado', 'item_em_compra')
        data: Dictionary with data to send

    Returns:
        True if broadcast was successful, False otherwise
    """
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            message = {"type": message_type}
            message.update(data)
            async_to_sync(channel_layer.group_send)(
                group_name,
                message
            )
            logger.debug(f"[WebSocket] Broadcast sent: {message_type} to {group_name}")
            return True
        except Exception as e:
            logger.error(f"[WebSocket] Broadcast failed: {e} (type: {message_type}, group: {group_name})")
            return False
    else:
        logger.warning(f"[WebSocket] channel_layer is None - broadcast failed for {group_name}")
        return False


def broadcast_card_status_update(pedido):
    """
    Broadcasts card_status update to dashboard

    Args:
        pedido: Pedido instance

    Returns:
        True if broadcast was successful, False otherwise
    """
    try:
        card_status_code, card_status_display = pedido.get_card_status()

        # Obter nomes únicos dos separadores (para badges no card)
        # Usar set() para garantir valores únicos
        separadores = list(set(
            pedido.itens.filter(separado=True, separado_por__isnull=False)
            .values_list('separado_por__nome', flat=True)
        ))

        return broadcast_to_websocket(
            "dashboard",
            "card_status_updated",
            {
                "pedido_id": pedido.id,
                "card_status": card_status_code,
                "card_status_display": card_status_display,
                "separadores": separadores,
            }
        )
    except Exception as e:
        logger.error(f"[WebSocket] Failed to broadcast card_status for pedido {pedido.id}: {e}")
        return False


# Cache para rate limiting (em memória)
# Estrutura: {'numero_login': {'tentativas': int, 'primeiro_timestamp': datetime}}
RATE_LIMIT_CACHE = {}


def verificar_rate_limit(numero_login):
    """
    Verifica rate limiting: máximo 10 tentativas em 15 minutos.
    Retorna (permitido: bool, tentativas_restantes: int)
    """
    now = timezone.now()

    if numero_login not in RATE_LIMIT_CACHE:
        RATE_LIMIT_CACHE[numero_login] = {
            'tentativas': 0,
            'primeiro_timestamp': now
        }

    cache_entry = RATE_LIMIT_CACHE[numero_login]

    # Limpar cache se passaram 15 minutos
    if now - cache_entry['primeiro_timestamp'] > timedelta(minutes=15):
        RATE_LIMIT_CACHE[numero_login] = {
            'tentativas': 0,
            'primeiro_timestamp': now
        }
        return True, 10

    # Verificar limite
    if cache_entry['tentativas'] >= 10:
        return False, 0

    return True, 10 - cache_entry['tentativas']


def registrar_tentativa_rate_limit(numero_login):
    """Registra uma tentativa de login para rate limiting"""
    now = timezone.now()

    if numero_login not in RATE_LIMIT_CACHE:
        RATE_LIMIT_CACHE[numero_login] = {
            'tentativas': 1,
            'primeiro_timestamp': now
        }
    else:
        RATE_LIMIT_CACHE[numero_login]['tentativas'] += 1


@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    View de login com numero_login + PIN.
    - Validação de formato (4 dígitos)
    - Sistema de bloqueio (5 tentativas)
    - Desbloqueio automático (30min) ou manual (admin)
    - Rate limiting (10 tentativas/15min por numero_login)
    - Auditoria completa
    """
    # Se já está autenticado, redireciona para dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        numero_login = request.POST.get('numero_login', '').strip()
        pin = request.POST.get('pin', '').strip()
        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]

        # Validação básica de formato
        if not numero_login or not pin:
            messages.error(request, 'Por favor, preencha número de login e PIN.')
            return render(request, 'login.html')

        # Validar formato: 4 dígitos
        if not numero_login.isdigit() or len(numero_login) != 4:
            messages.error(request, 'Número de login deve ter exatamente 4 dígitos.')
            LogAuditoria.objects.create(
                usuario=None,
                acao='login_falhou',
                modelo='Usuario',
                objeto_id=0,
                dados_novos={'numero_login': numero_login, 'motivo': 'formato_invalido'},
                ip=ip,
                user_agent=user_agent
            )
            return render(request, 'login.html')

        if not pin.isdigit() or len(pin) != 4:
            messages.error(request, 'PIN deve ter exatamente 4 dígitos.')
            return render(request, 'login.html')

        # Verificar rate limiting
        permitido, tentativas_restantes = verificar_rate_limit(numero_login)
        if not permitido:
            messages.error(request, 'Muitas tentativas de login. Aguarde 15 minutos e tente novamente.')
            LogAuditoria.objects.create(
                usuario=None,
                acao='login_bloqueado_rate_limit',
                modelo='Usuario',
                objeto_id=0,
                dados_novos={'numero_login': numero_login},
                ip=ip,
                user_agent=user_agent
            )
            return render(request, 'login.html')

        # Registrar tentativa no rate limit
        registrar_tentativa_rate_limit(numero_login)

        # Buscar usuário
        try:
            usuario = Usuario.objects.get(numero_login=int(numero_login))
        except Usuario.DoesNotExist:
            messages.error(request, 'Número de login não encontrado.')
            LogAuditoria.objects.create(
                usuario=None,
                acao='login_falhou',
                modelo='Usuario',
                objeto_id=0,
                dados_novos={'numero_login': numero_login, 'motivo': 'usuario_nao_encontrado'},
                ip=ip,
                user_agent=user_agent
            )
            return render(request, 'login.html')

        # Verificar se usuário está ativo
        if not usuario.ativo:
            messages.error(request, 'Usuário inativo. Contate o administrador.')
            LogAuditoria.objects.create(
                usuario=usuario,
                acao='login_falhou',
                modelo='Usuario',
                objeto_id=usuario.id,
                dados_novos={'motivo': 'usuario_inativo'},
                ip=ip,
                user_agent=user_agent
            )
            return render(request, 'login.html')

        # Verificar se pode fazer login (bloqueio temporário)
        pode_logar, motivo = usuario.pode_fazer_login()
        if not pode_logar:
            if 'bloqueado' in motivo.lower():
                # Verifica se já passou 30 minutos (desbloqueio automático)
                if usuario.bloqueado_ate and timezone.now() >= usuario.bloqueado_ate:
                    usuario.tentativas_login = 0
                    usuario.bloqueado_ate = None
                    usuario.save(update_fields=['tentativas_login', 'bloqueado_ate'])
                else:
                    messages.error(request, motivo)
                    LogAuditoria.objects.create(
                        usuario=usuario,
                        acao='login_falhou',
                        modelo='Usuario',
                        objeto_id=usuario.id,
                        dados_novos={'motivo': 'bloqueado_temporariamente'},
                        ip=ip,
                        user_agent=user_agent
                    )
                    return render(request, 'login.html')
            else:
                messages.error(request, motivo)
                return render(request, 'login.html')

        # Verificar PIN
        if not usuario.check_pin(pin):
            # PIN incorreto - incrementar tentativas
            usuario.tentativas_login += 1

            # Bloquear após 5 tentativas (30 minutos)
            if usuario.tentativas_login >= 5:
                usuario.bloqueado_ate = timezone.now() + timedelta(minutes=30)
                usuario.save(update_fields=['tentativas_login', 'bloqueado_ate'])
                messages.error(request, 'PIN incorreto. Você atingiu o limite de 5 tentativas. Usuário bloqueado por 30 minutos.')
                LogAuditoria.objects.create(
                    usuario=usuario,
                    acao='usuario_bloqueado',
                    modelo='Usuario',
                    objeto_id=usuario.id,
                    dados_novos={'motivo': '5_tentativas_incorretas', 'bloqueado_ate': usuario.bloqueado_ate.isoformat()},
                    ip=ip,
                    user_agent=user_agent
                )
            else:
                usuario.save(update_fields=['tentativas_login'])
                tentativas_restantes = 5 - usuario.tentativas_login
                messages.error(request, f'PIN incorreto. Você tem mais {tentativas_restantes} tentativa(s).')
                LogAuditoria.objects.create(
                    usuario=usuario,
                    acao='login_falhou',
                    modelo='Usuario',
                    objeto_id=usuario.id,
                    dados_novos={'motivo': 'pin_incorreto', 'tentativas': usuario.tentativas_login},
                    ip=ip,
                    user_agent=user_agent
                )

            return render(request, 'login.html')

        # Login bem-sucedido
        usuario.tentativas_login = 0
        usuario.bloqueado_ate = None
        usuario.ultimo_acesso = timezone.now()
        usuario.save(update_fields=['tentativas_login', 'bloqueado_ate', 'ultimo_acesso'])

        # Fazer login no Django
        login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')

        # Registrar login no log de auditoria
        LogAuditoria.objects.create(
            usuario=usuario,
            acao='login_sucesso',
            modelo='Usuario',
            objeto_id=usuario.id,
            dados_novos={'tipo': usuario.tipo},
            ip=ip,
            user_agent=user_agent
        )

        messages.success(request, f'Bem-vindo, {usuario.nome}!')
        return redirect('dashboard')

    return render(request, 'login.html')


@login_required_custom
@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    View de logout.
    Registra no log de auditoria e encerra sessão.
    """
    if request.method == 'POST':
        usuario = request.user
        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]

        # Registrar logout
        LogAuditoria.objects.create(
            usuario=usuario,
            acao='logout',
            modelo='Usuario',
            objeto_id=usuario.id,
            ip=ip,
            user_agent=user_agent
        )

        logout(request)
        messages.success(request, 'Logout realizado com sucesso.')
        return redirect('login')

    return redirect('dashboard')


@administrador_required
@require_http_methods(["GET", "POST"])
def reset_pin_view(request, user_id):
    """
    View para administrador resetar PIN de um usuário.
    - Apenas ADMINISTRADOR pode acessar
    - Zera tentativas e desbloqueio
    - Registra no log de auditoria
    """
    usuario = get_object_or_404(Usuario, id=user_id)

    if request.method == 'POST':
        novo_pin = request.POST.get('novo_pin', '').strip()

        # Validar formato
        if not novo_pin or not novo_pin.isdigit() or len(novo_pin) != 4:
            messages.error(request, 'PIN deve ter exatamente 4 dígitos.')
            return render(request, 'reset_pin.html', {'usuario_alvo': usuario})

        # Resetar PIN e desbloqueio
        usuario.set_pin(novo_pin)
        usuario.tentativas_login = 0
        usuario.bloqueado_ate = None
        usuario.save(update_fields=['tentativas_login', 'bloqueado_ate'])

        # Registrar no log
        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
        LogAuditoria.objects.create(
            usuario=request.user,
            acao='reset_pin',
            modelo='Usuario',
            objeto_id=usuario.id,
            dados_novos={'usuario_alvo': usuario.numero_login, 'nome': usuario.nome},
            ip=ip,
            user_agent=user_agent
        )

        messages.success(request, f'PIN do usuário {usuario.nome} ({usuario.numero_login}) foi resetado com sucesso.')
        return redirect('lista_usuarios')

    return render(request, 'reset_pin.html', {'usuario_alvo': usuario})


# =====================
# DASHBOARD - FASE 4
# =====================

@login_required_custom
def dashboard(request):
    """
    Dashboard principal com pedidos ativos e métricas do dia.
    FASE 4: WebSocket + filtros client-side
    """
    from apps.core.utils import calcular_metricas_dia, formatar_tempo
    from datetime import datetime

    # Mensagens rotativas para empty state (baseado no dia da semana)
    EMPTY_STATE_MESSAGES = {
        0: {  # Segunda-feira
            'titulo': 'Tudo certo por aqui!',
            'subtitulo': 'Nenhum pedido pendente. Aproveite o momento pra recarregar as energias ☕️'
        },
        1: {  # Terça-feira
            'titulo': 'Tudo tranquilo na área de separação',
            'subtitulo': 'Nenhum pedido encontrado nos filtros aplicados. Que tal organizar o espaço ou aproveitar um café? ☕️'
        },
        2: {  # Quarta-feira
            'titulo': 'Hora do descanso merecido',
            'subtitulo': 'Nenhum pedido disponível. Use esse tempo pra alongar, respirar e voltar com tudo!'
        },
        3: {  # Quinta-feira
            'titulo': 'Fila zerada 🙌',
            'subtitulo': 'Nenhum pedido em separação no momento. Um bom sinal de produtividade!'
        },
        4: {  # Sexta-feira
            'titulo': 'Tudo sob controle',
            'subtitulo': 'Nenhum pedido para separar agora — sinal de que a equipe está mandando bem! 👏'
        },
        5: {  # Sábado
            'titulo': 'Tudo certo por aqui!',
            'subtitulo': 'Nenhum pedido pendente. Aproveite o momento pra recarregar as energias ☕️'
        },
        6: {  # Domingo
            'titulo': 'Tudo tranquilo na área de separação',
            'subtitulo': 'Nenhum pedido encontrado. Que tal organizar o espaço ou aproveitar um café? ☕️'
        }
    }

    # Buscar apenas pedidos ativos (não finalizados e não deletados)
    # Ordenação será feita em Python por data de criação (mais recentes primeiro)
    pedidos = Pedido.objects.filter(
        deletado=False
    ).exclude(
        status__in=['FINALIZADO', 'CANCELADO']
    ).select_related('vendedor').prefetch_related('itens')

    # Calcular métricas do dia
    metricas = calcular_metricas_dia()

    # Lista de vendedores para o filtro
    vendedores = Usuario.objects.filter(
        tipo='VENDEDOR',
        ativo=True
    ).order_by('nome')

    # Preparar dados dos pedidos para o template
    pedidos_data = []
    for pedido in pedidos:
        # Calcular itens separados e substituídos para a barra de progresso
        itens = pedido.itens.all()
        total_itens = itens.count()
        itens_separados = itens.filter(separado=True).count()
        itens_substituidos = itens.filter(substituido=True).count()
        # Substituídos já são contados como separados, não somar duas vezes
        itens_completos = itens_separados
        porcentagem_separacao = (itens_completos / total_itens * 100) if total_itens > 0 else 0

        # Obter nomes únicos dos separadores (para badges no card)
        # Usar set() para garantir valores únicos
        separadores = list(set(
            itens.filter(separado=True, separado_por__isnull=False)
            .values_list('separado_por__nome', flat=True)
        ))

        # Obter card_status baseado no estado dos itens
        card_status_code, card_status_display = pedido.get_card_status()
        card_status_css = pedido.get_card_status_css()

        pedidos_data.append({
            'id': pedido.id,
            'numero_orcamento': pedido.numero_orcamento,
            'cliente': pedido.nome_cliente,
            'vendedor': pedido.vendedor.nome,
            'vendedor_id': pedido.vendedor.id,
            'status': pedido.status,
            'status_display': pedido.get_status_display(),
            'card_status': card_status_code,
            'card_status_display': card_status_display,
            'card_status_css': card_status_css,
            'data': pedido.data.strftime('%d/%m/%Y'),
            'data_criacao': pedido.data_criacao.strftime('%d/%m/%Y %H:%M'),
            'data_criacao_timestamp': pedido.data_criacao.timestamp(),
            'criado_em': pedido.data_criacao.isoformat(),
            'total_itens': total_itens,
            'logistica': pedido.get_logistica_display() if pedido.logistica else "Não definida",
            'embalagem': pedido.get_embalagem_display() if pedido.embalagem else "Embalagem padrão",
            'itens_separados': itens_completos,
            'porcentagem_separacao': round(porcentagem_separacao, 1),
            'separadores': separadores,
        })

    # Ordenar pedidos por data de criação (mais recentes primeiro)
    pedidos_data.sort(key=lambda p: -p['data_criacao_timestamp'])

    # Calcular estatísticas de compras (para COMPRADORA e ADMIN)
    itens_aguardando_compra = 0
    if request.user.tipo in ['COMPRADORA', 'ADMINISTRADOR']:
        itens_aguardando_compra = ItemPedido.objects.filter(
            em_compra=True,
            compra_realizada=False,
            pedido__deletado=False
        ).count()

    # Determinar mensagem do empty state baseada no dia da semana
    dia_semana = datetime.now().weekday()  # 0 = Segunda, 6 = Domingo
    empty_state = EMPTY_STATE_MESSAGES[dia_semana]

    # Carregar configuração do sistema para imagem do empty state
    config = SistemaConfig.load()

    context = {
        'usuario': request.user,
        'pedidos': pedidos_data,
        'vendedores': vendedores,
        'metricas': {
            'tempo_medio': formatar_tempo(metricas['tempo_medio_separacao']),
            'pedidos_em_aberto': metricas['pedidos_em_aberto'],
            'total_pedidos_hoje': metricas['total_pedidos_hoje'],
        },
        'itens_aguardando_compra': itens_aguardando_compra,
        'empty_state_titulo': empty_state['titulo'],
        'empty_state_subtitulo': empty_state['subtitulo'],
        'empty_state_image_url': config.empty_state_image.url if config.empty_state_image else None,
    }

    return render(request, 'dashboard.html', context)


@login_required_custom
@require_http_methods(["GET"])
def pedido_detalhe_view(request, pedido_id):
    """
    View de detalhes do pedido com lista de itens.
    Mostra status de separação, botões de ação e atualiza em tempo real via WebSocket.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id, deletado=False)

    # Buscar itens do pedido
    itens = pedido.itens.select_related('produto', 'separado_por', 'marcado_compra_por').all()

    # Calcular estatísticas do pedido
    total_itens = itens.count()
    itens_separados = itens.filter(separado=True).count()
    itens_substituidos = itens.filter(substituido=True).count()
    itens_em_compra = itens.filter(em_compra=True).count()
    # Substituídos já são contados como separados
    itens_pendentes = total_itens - itens_separados

    # Substituídos já são contados como separados, não somar duas vezes
    progresso_separacao = (itens_separados / total_itens * 100) if total_itens > 0 else 0

    # Verificar se pode finalizar
    pode_finalizar = pedido.pode_ser_finalizado()

    # Verificar se pode deletar (vendedor que criou ou admin)
    pode_deletar = (
        request.user.tipo == 'ADMINISTRADOR' or
        (request.user.tipo == 'VENDEDOR' and pedido.vendedor == request.user)
    )

    # Calcular card_status para exibir no header (igual ao dashboard)
    card_status_code, card_status_display = pedido.get_card_status()

    # Definir CSS class baseado no card_status
    card_status_css_map = {
        'NAO_INICIADO': 'nao-iniciado',
        'EM_SEPARACAO': 'em-separacao',
        'AGUARDANDO_COMPRA': 'aguardando-compra',
        'CONCLUIDO': 'concluido',
    }
    card_status_css = card_status_css_map.get(card_status_code, 'nao-iniciado')

    # Extrair nomes únicos de separadores (igual ao dashboard)
    separadores = list(set(
        item.separado_por.nome
        for item in itens
        if item.separado and item.separado_por
    ))

    context = {
        'pedido': pedido,
        'itens': itens,
        'total_itens': total_itens,
        'itens_separados': itens_separados,
        'itens_substituidos': itens_substituidos,
        'itens_em_compra': itens_em_compra,
        'itens_pendentes': itens_pendentes,
        'progresso_separacao': round(progresso_separacao, 1),
        'pode_finalizar': pode_finalizar,
        'pode_deletar': pode_deletar,
        # Novos dados para o header
        'card_status': card_status_code,
        'card_status_display': card_status_display,
        'card_status_css': card_status_css,
        'separadores': separadores,
        'porcentagem_separacao': round(progresso_separacao, 1),  # Alias para compatibilidade
    }

    return render(request, 'pedido_detalhe.html', context)


# =====================
# UPLOAD E PROCESSAMENTO DE PDF - FASE 3
# =====================

from .forms import UploadPDFForm, ConfirmarPedidoForm
from .pdf_parser import extrair_dados_pdf, validar_orcamento, PDFParserError
from .models import Pedido, Produto, ItemPedido
from decimal import Decimal
from django.db import transaction


@login_required_custom
@require_http_methods(["GET", "POST"])
def upload_pdf_view(request):
    """
    View para upload de PDF de orçamento.
    Disponível apenas para VENDEDOR ou ADMINISTRADOR.
    """
    # Verificar permissão (somente vendedor ou admin)
    if request.user.tipo not in ['VENDEDOR', 'ADMINISTRADOR']:
        messages.error(request, 'Você não tem permissão para fazer upload de orçamentos.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = UploadPDFForm(request.POST, request.FILES)

        if form.is_valid():
            arquivo_pdf = form.cleaned_data['arquivo_pdf']

            try:
                # Extrair dados do PDF
                dados = extrair_dados_pdf(arquivo_pdf)

                # Validar dados extraídos
                valido, erro = validar_orcamento(dados)
                if not valido:
                    messages.error(request, f'Erro na validação do PDF: {erro}')
                    return render(request, 'upload_pdf.html', {'form': form})

                # Verificar duplicata
                if Pedido.objects.filter(numero_orcamento=dados['numero_orcamento']).exists():
                    messages.error(request,
                        f'Orçamento #{dados["numero_orcamento"]} já existe no sistema. '
                        'Não é possível importar orçamentos duplicados.')
                    return render(request, 'upload_pdf.html', {'form': form})

                # Armazenar dados na sessão para a próxima etapa
                request.session['dados_pdf'] = {
                    'numero_orcamento': dados['numero_orcamento'],
                    'codigo_cliente': dados['codigo_cliente'],
                    'nome_cliente': dados['nome_cliente'],
                    'data': dados['data'].isoformat(),
                    'produtos': [
                        {
                            'codigo': p['codigo'],
                            'descricao': p['descricao'],
                            'quantidade': str(p['quantidade']),
                            'preco_unitario': str(p['preco_unitario'])
                        }
                        for p in dados['produtos']
                    ]
                }

                # Registrar no log
                ip = get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
                LogAuditoria.objects.create(
                    usuario=request.user,
                    acao='upload_pdf',
                    modelo='Pedido',
                    objeto_id=0,
                    dados_novos={
                        'numero_orcamento': dados['numero_orcamento'],
                        'total_produtos': len(dados['produtos'])
                    },
                    ip=ip,
                    user_agent=user_agent
                )

                messages.success(request, f'PDF processado com sucesso! {len(dados["produtos"])} produtos encontrados.')
                return redirect('confirmar_pedido')

            except PDFParserError as e:
                messages.error(request, f'Erro ao processar PDF: {str(e)}')
                return render(request, 'upload_pdf.html', {'form': form})
            except Exception as e:
                messages.error(request, f'Erro inesperado ao processar PDF: {str(e)}')
                return render(request, 'upload_pdf.html', {'form': form})
    else:
        form = UploadPDFForm()

    return render(request, 'upload_pdf.html', {'form': form})


@login_required_custom
@require_http_methods(["GET", "POST"])
def confirmar_pedido_view(request):
    """
    View para confirmar o pedido após upload do PDF.
    Exibe dados extraídos e solicita logística/embalagem.
    """
    # Verificar se há dados na sessão
    dados_pdf = request.session.get('dados_pdf')
    if not dados_pdf:
        messages.error(request, 'Nenhum PDF foi processado. Por favor, faça o upload primeiro.')
        return redirect('upload_pdf')

    # Criar cópia profunda para uso no template (não modifica sessão)
    # Session data permanece como strings (JSON serializável)
    dados_pdf_template = copy.deepcopy(dados_pdf)

    # Converter valores de string para float para uso no template e JavaScript
    # (float é JSON serializável e compatível com JavaScript)
    for produto in dados_pdf_template['produtos']:
        produto['quantidade'] = float(produto['quantidade'])
        produto['preco_unitario'] = float(produto['preco_unitario'])

    if request.method == 'POST':
        form = ConfirmarPedidoForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Converter data de ISO string para date object
                    data_str = dados_pdf['data']
                    data_obj = datetime.fromisoformat(data_str).date() if isinstance(data_str, str) else data_str

                    # Criar pedido
                    pedido = Pedido.objects.create(
                        numero_orcamento=dados_pdf['numero_orcamento'],
                        codigo_cliente=dados_pdf['codigo_cliente'],
                        nome_cliente=dados_pdf['nome_cliente'],
                        vendedor=request.user,
                        data=data_obj,
                        logistica=form.cleaned_data['logistica'],
                        embalagem=form.cleaned_data['embalagem'],
                        observacoes=form.cleaned_data.get('observacoes', ''),
                        status='PENDENTE'
                    )

                    # Criar produtos e itens
                    produtos_criados = 0
                    for produto_data in dados_pdf['produtos']:
                        # Buscar ou criar produto
                        produto, created = Produto.objects.get_or_create(
                            codigo=produto_data['codigo'],
                            defaults={
                                'descricao': produto_data['descricao'],
                                'criado_automaticamente': True
                            }
                        )

                        if created:
                            produtos_criados += 1

                        # Criar item do pedido
                        ItemPedido.objects.create(
                            pedido=pedido,
                            produto=produto,
                            quantidade_solicitada=Decimal(produto_data['quantidade']),
                            preco_unitario=Decimal(produto_data['preco_unitario'])
                        )

                    # Registrar no log
                    ip = get_client_ip(request)
                    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
                    LogAuditoria.objects.create(
                        usuario=request.user,
                        acao='criar_pedido',
                        modelo='Pedido',
                        objeto_id=pedido.id,
                        dados_novos={
                            'numero_orcamento': pedido.numero_orcamento,
                            'cliente': pedido.nome_cliente,
                            'total_itens': len(dados_pdf['produtos']),
                            'produtos_criados': produtos_criados
                        },
                        ip=ip,
                        user_agent=user_agent
                    )

                    # Broadcast WebSocket - notificar todos os dashboards
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync

                    channel_layer = get_channel_layer()
                    if channel_layer:
                        # Garantir formatação de data (pedido.data já é date object após save)
                        data_formatada = pedido.data.strftime('%d/%m/%Y') if hasattr(pedido.data, 'strftime') else str(pedido.data)
                        data_criacao_formatada = pedido.data_criacao.strftime('%d/%m/%Y %H:%M') if hasattr(pedido.data_criacao, 'strftime') else str(pedido.data_criacao)

                        # Obter card_status
                        card_status_code, card_status_display = pedido.get_card_status()
                        card_status_css = pedido.get_card_status_css()

                        async_to_sync(channel_layer.group_send)(
                            "dashboard",
                            {
                                "type": "pedido_criado",
                                "pedido": {
                                    "id": pedido.id,
                                    "numero_orcamento": pedido.numero_orcamento,
                                    "cliente": pedido.nome_cliente,
                                    "vendedor": pedido.vendedor.nome,
                                    "vendedor_id": pedido.vendedor.id,
                                    "status": pedido.status,
                                    "status_display": pedido.get_status_display(),
                                    "card_status": card_status_code,
                                    "card_status_display": card_status_display,
                                    "card_status_css": card_status_css,
                                    "data": data_formatada,
                                    "data_criacao": data_criacao_formatada,
                                    "total_itens": pedido.itens.count(),
                                }
                            }
                        )

                    # Limpar sessão
                    del request.session['dados_pdf']

                    msg_produtos = f' ({produtos_criados} produto(s) novo(s) criado(s))' if produtos_criados > 0 else ''
                    messages.success(request,
                        f'Pedido #{pedido.numero_orcamento} criado com sucesso! '
                        f'{len(dados_pdf["produtos"])} item(ns) adicionado(s){msg_produtos}.')

                    return redirect('pedido_detalhe', pedido_id=pedido.id)

            except Exception as e:
                messages.error(request, f'Erro ao criar pedido: {str(e)}')
                return render(request, 'confirmar_pedido.html', {
                    'form': form,
                    'dados_pdf': dados_pdf_template
                })
    else:
        form = ConfirmarPedidoForm()

    return render(request, 'confirmar_pedido.html', {
        'form': form,
        'dados_pdf': dados_pdf_template
    })


# =====================
# SEPARAÇÃO DE PEDIDOS - FASE 5
# =====================

from .forms import SubstituirProdutoForm, MarcarCompraForm
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.http import JsonResponse

# Logger para debugging
logger = logging.getLogger(__name__)


@login_required_custom
@require_http_methods(["POST"])
@transaction.atomic()  # Garantir transação atômica
def separar_item_view(request, item_id):
    """
    View para marcar um item como separado (tudo-ou-nada).
    Disponível para qualquer usuário autenticado.
    """
    # Safe user access - avoid AttributeError if user is AnonymousUser
    username = getattr(request.user, 'nome', 'anonymous') if hasattr(request.user, 'is_authenticated') and request.user.is_authenticated else 'anonymous'
    logger.info(f"[SEPARAR ITEM] Requisição recebida - Item ID: {item_id}, User: {username}")

    try:
        item = get_object_or_404(ItemPedido, id=item_id)
        pedido = item.pedido

        logger.info(f"[SEPARAR ITEM] Item encontrado - Produto: {item.produto.descricao[:50]}, Pedido: {pedido.numero_orcamento}")

        # Verificar se pedido não está deletado
        if pedido.deletado:
            logger.warning(f"[SEPARAR ITEM] Pedido deletado - Item ID: {item_id}")
            return JsonResponse({'success': False, 'error': 'Pedido foi deletado.'}, status=400)

        # Verificar se já está separado
        if item.separado:
            logger.warning(f"[SEPARAR ITEM] Item já separado - Item ID: {item_id}")
            return JsonResponse({'success': False, 'error': 'Item já está separado.'}, status=400)

        # Verificar se está substituído
        if item.substituido:
            logger.warning(f"[SEPARAR ITEM] Item substituído - Item ID: {item_id}")
            return JsonResponse({'success': False, 'error': 'Item foi substituído.'}, status=400)

        # Verificar se item estava marcado para compra
        estava_em_compra = item.em_compra

        # Marcar como separado (e remover de compra se estava)
        item.separado = True
        item.em_compra = False  # Remove da lista de compras
        item.separado_por = request.user
        item.separado_em = timezone.now()

        logger.info(f"[SEPARAR ITEM] Salvando item - ID: {item.id}, separado=True, user={username}")
        item.save(update_fields=['separado', 'em_compra', 'separado_por', 'separado_em'])
        logger.info(f"[SEPARAR ITEM] ✓ Item salvo com sucesso - ID: {item.id}")

    except Exception as e:
        logger.error(f"[SEPARAR ITEM] ✗ ERRO ao salvar item {item_id}: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Erro ao processar: {str(e)}'}, status=500)

    # Atualizar status do pedido se necessário
    if pedido.status == 'PENDENTE':
        pedido.status = 'EM_SEPARACAO'
        pedido.save()

    # Auditoria
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='separar_item_direto' if estava_em_compra else 'separar_item',
        modelo='ItemPedido',
        objeto_id=item.id,
        dados_novos={
            'item_id': item.id,
            'pedido_id': pedido.id,
            'produto': item.produto.descricao,
            'quantidade': str(item.quantidade_solicitada),
            'estava_em_compra': estava_em_compra
        },
        ip=ip,
        user_agent=user_agent
    )

    # Broadcast WebSocket para o pedido
    broadcast_to_websocket(
        f"pedido_{pedido.id}",
        "item_separado",
        {
            "item": {
                "id": item.id,
                "separado": True,
                "separado_por": request.user.nome,
                "separado_em": timezone.localtime(item.separado_em).strftime('%d/%m/%Y %H:%M')
            }
        }
    )

    # Calcular porcentagem de separação para atualização em tempo real
    itens_separados_count = pedido.itens.filter(separado=True).count()
    total_itens_count = pedido.itens.count()
    porcentagem_separacao = round((itens_separados_count / total_itens_count * 100), 1) if total_itens_count > 0 else 0

    # Broadcast para dashboard (pedido atualizado)
    broadcast_to_websocket(
        "dashboard",
        "pedido_atualizado",
        {
            "pedido": {
                "id": pedido.id,
                "numero_orcamento": pedido.numero_orcamento,
                "status": pedido.status,
                "porcentagem_separacao": porcentagem_separacao
            }
        }
    )

    # Broadcast card_status update
    broadcast_card_status_update(pedido)

    # Se estava em compra, broadcast para painel de compras
    if estava_em_compra:
        broadcast_to_websocket(
            "painel_compras",
            "item_separado_direto",
            {
                "item": {
                    "id": item.id,
                    "produto_codigo": item.produto.codigo,
                    "produto_descricao": item.produto.descricao,
                    "pedido_id": pedido.id,
                    "pedido_numero": pedido.numero_orcamento
                }
            }
        )

    logger.info(f"[SEPARAR ITEM] ✓ PROCESSO COMPLETO - Item {item.id} separado com sucesso, progresso: {porcentagem_separacao}%")
    return JsonResponse({
        'success': True,
        'item_id': item.id,
        'separado_por': request.user.nome,
        'separado_em': item.separado_em.strftime('%d/%m/%Y %H:%M'),
        'pedido_status': pedido.status,
        'porcentagem_separacao': porcentagem_separacao
    })


@login_required_custom
@require_http_methods(["POST"])
@transaction.atomic()
def unseparar_item_view(request, item_id):
    """
    View para desseparar um item (reverter separação).
    Remove marcação de separação e retorna item ao estado Pendente.
    IMPORTANTE: Não permite desseparar itens substituídos.
    """
    # Safe user access - avoid AttributeError if user is AnonymousUser
    username = getattr(request.user, 'nome', 'anonymous') if hasattr(request.user, 'is_authenticated') and request.user.is_authenticated else 'anonymous'
    logger.info(f"[UNSEPARAR ITEM] Requisição recebida - Item ID: {item_id}, User: {username}")

    try:
        item = get_object_or_404(ItemPedido, id=item_id)
        pedido = item.pedido

        logger.info(f"[UNSEPARAR ITEM] Item encontrado - Produto: {item.produto.descricao[:50]}, Pedido: {pedido.numero_orcamento}")

        # Verificar se pedido não está deletado
        if pedido.deletado:
            logger.warning(f"[UNSEPARAR ITEM] Pedido deletado - Item ID: {item_id}")
            return JsonResponse({'success': False, 'error': 'Pedido foi deletado.'}, status=400)

        # Verificar se está separado
        if not item.separado:
            logger.warning(f"[UNSEPARAR ITEM] Item não está separado - Item ID: {item_id}")
            return JsonResponse({'success': False, 'error': 'Item não está separado.'}, status=400)

        # Detectar se item está substituído para limpar campos adicionais
        estava_substituido = item.substituido
        produto_substituto_anterior = item.produto_substituto if estava_substituido else None
        estava_em_compra = item.em_compra

        # Guardar dados para auditoria
        separado_por_anterior = item.separado_por.nome if item.separado_por else 'Desconhecido'
        separado_em_anterior = item.separado_em.strftime('%d/%m/%Y %H:%M') if item.separado_em else 'N/A'

        # Remover marcação de separação
        item.separado = False
        item.separado_por = None
        item.separado_em = None

        # Se estava substituído, limpar campos de substituição
        fields_to_update = ['separado', 'separado_por', 'separado_em']
        if estava_substituido:
            logger.info(f"[UNSEPARAR ITEM] Removendo substituição - Item ID: {item_id}, produto_substituto: {produto_substituto_anterior}")
            item.substituido = False
            item.produto_substituto = ''
            fields_to_update.extend(['substituido', 'produto_substituto'])

        # Se estava em compra, limpar TODOS os campos de compra
        if estava_em_compra:
            logger.info(f"[UNSEPARAR ITEM] Removendo marcação de compra - Item ID: {item_id}")
            item.em_compra = False
            item.marcado_compra_por = None
            item.marcado_compra_em = None
            item.compra_realizada = False
            item.compra_realizada_por = None
            item.compra_realizada_em = None
            fields_to_update.extend(['em_compra', 'marcado_compra_por', 'marcado_compra_em',
                                    'compra_realizada', 'compra_realizada_por', 'compra_realizada_em'])

        logger.info(f"[UNSEPARAR ITEM] Salvando item - ID: {item.id}, separado=False, substituido=False, em_compra=False")
        item.save(update_fields=fields_to_update)
        logger.info(f"[UNSEPARAR ITEM] ✓ Item salvo com sucesso - ID: {item.id}")

    except Exception as e:
        logger.error(f"[UNSEPARAR ITEM] ✗ ERRO ao desseparar item {item_id}: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Erro ao processar: {str(e)}'}, status=500)

    # Atualizar status do pedido se necessário
    # Verificar se todos os itens não estão mais separados
    itens_separados = pedido.itens.filter(separado=True).count()
    if itens_separados == 0 and pedido.status == 'EM_SEPARACAO':
        pedido.status = 'PENDENTE'
        pedido.save()

    # Auditoria
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='unseparar_item',
        modelo='ItemPedido',
        objeto_id=item.id,
        dados_novos={
            'item_id': item.id,
            'pedido_id': pedido.id,
            'produto': item.produto.descricao,
            'quantidade': str(item.quantidade_solicitada),
            'separado_por_anterior': separado_por_anterior,
            'separado_em_anterior': separado_em_anterior
        },
        ip=ip,
        user_agent=user_agent
    )

    # Broadcast WebSocket para o pedido
    broadcast_to_websocket(
        f"pedido_{pedido.id}",
        "item_unseparado",
        {
            "item": {
                "id": item.id,
                "separado": False,
                "separado_por": None,
                "separado_em": None,
                "substituido": False,
                "produto_substituto": "",
                "em_compra": False,
                "marcado_compra_por": None,
                "marcado_compra_em": None,
                "compra_realizada": False,
                "compra_realizada_por": None,
                "compra_realizada_em": None,
                "estava_substituido": estava_substituido,
                "estava_em_compra": estava_em_compra
            }
        }
    )

    # Calcular porcentagem de separação para atualização em tempo real
    itens_separados_count = pedido.itens.filter(separado=True).count()
    total_itens_count = pedido.itens.count()
    porcentagem_separacao = round((itens_separados_count / total_itens_count * 100), 1) if total_itens_count > 0 else 0

    # Broadcast para dashboard (pedido atualizado)
    broadcast_to_websocket(
        "dashboard",
        "pedido_atualizado",
        {
            "pedido": {
                "id": pedido.id,
                "numero_orcamento": pedido.numero_orcamento,
                "status": pedido.status,
                "porcentagem_separacao": porcentagem_separacao
            }
        }
    )

    # Broadcast card_status update
    broadcast_card_status_update(pedido)

    # Se estava em compra, broadcast para painel de compras (remoção do item)
    if estava_em_compra:
        logger.info(f"[UNSEPARAR ITEM] Enviando broadcast para painel_compras - Item ID: {item_id}, Pedido ID: {pedido.id}")
        broadcast_to_websocket(
            "painel_compras",
            "item_removido_compras",
            {
                "item_id": item.id,
                "pedido_id": pedido.id
            }
        )

    logger.info(f"[UNSEPARAR ITEM] ✓ PROCESSO COMPLETO - Item {item.id} desseparado com sucesso, progresso: {porcentagem_separacao}%")
    return JsonResponse({
        'success': True,
        'item_id': item.id,
        'pedido_status': pedido.status,
        'porcentagem_separacao': porcentagem_separacao
    })


@admin_or_compradora
@require_http_methods(["GET", "POST"])
def marcar_compra_view(request, item_id):
    """
    View para marcar item para compra.
    Se GET: retorna modal com outros pedidos que têm o mesmo produto.
    Se POST: marca item(s) para compra.
    Disponível para COMPRADORA ou ADMINISTRADOR.
    """
    item = get_object_or_404(ItemPedido, id=item_id)
    pedido = item.pedido

    # Verificar se pedido não está deletado
    if pedido.deletado:
        return JsonResponse({'success': False, 'error': 'Pedido foi deletado.'}, status=400)

    # Verificar se já está em compra
    if item.em_compra:
        return JsonResponse({'success': False, 'error': 'Item já está marcado para compra.'}, status=400)

    # Verificar se já está separado ou substituído
    if item.separado or item.substituido:
        return JsonResponse({'success': False, 'error': 'Item já foi separado ou substituído.'}, status=400)

    if request.method == 'GET':
        # Buscar outros itens com o mesmo produto em pedidos ativos
        outros_itens = ItemPedido.objects.filter(
            produto=item.produto,
            pedido__deletado=False,
            pedido__status__in=['PENDENTE', 'EM_SEPARACAO', 'AGUARDANDO_COMPRA'],
            separado=False,
            substituido=False,
            em_compra=False
        ).exclude(id=item.id).select_related('pedido')

        form = MarcarCompraForm(outros_itens=list(outros_itens))

        return JsonResponse({
            'success': True,
            'outros_itens': [
                {
                    'id': i.id,
                    'pedido_numero': i.pedido.numero_orcamento,
                    'quantidade': str(i.quantidade_solicitada)
                }
                for i in outros_itens
            ]
        })

    # POST: Marcar para compra
    outros_pedidos_ids = request.POST.getlist('outros_pedidos')

    # Marcar item atual
    item.em_compra = True
    item.marcado_compra_por = request.user
    item.marcado_compra_em = timezone.now()
    item.save()

    itens_marcados = [item]

    # Marcar outros itens se selecionados
    if outros_pedidos_ids:
        outros_itens = ItemPedido.objects.filter(
            id__in=outros_pedidos_ids,
            produto=item.produto,
            pedido__deletado=False,
            separado=False,
            substituido=False,
            em_compra=False
        )

        for outro_item in outros_itens:
            outro_item.em_compra = True
            outro_item.marcado_compra_por = request.user
            outro_item.marcado_compra_em = timezone.now()
            outro_item.save()
            itens_marcados.append(outro_item)

    # Atualizar status do pedido se necessário
    if pedido.status != 'AGUARDANDO_COMPRA':
        # Verificar se tem itens aguardando compra
        if pedido.itens.filter(em_compra=True).exists():
            pedido.status = 'AGUARDANDO_COMPRA'
            pedido.save()

    # Auditoria
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='marcar_compra',
        modelo='ItemPedido',
        objeto_id=item.id,
        dados_novos={
            'item_id': item.id,
            'pedido_id': pedido.id,
            'produto': item.produto.descricao,
            'outros_itens': [i.id for i in itens_marcados[1:]]
        },
        ip=ip,
        user_agent=user_agent
    )

    # Broadcast WebSocket para cada pedido afetado
    pedidos_afetados = set()

    for i in itens_marcados:
        pedidos_afetados.add(i.pedido.id)
        broadcast_to_websocket(
            f"pedido_{i.pedido.id}",
            "item_em_compra",
            {
                "item": {
                    "id": i.id,
                    "em_compra": True,
                    "marcado_compra_por": request.user.nome,
                    "marcado_compra_em": timezone.localtime(i.marcado_compra_em).strftime('%d/%m/%Y %H:%M')
                }
            }
        )

    # Broadcast para dashboard
    for pedido_id in pedidos_afetados:
        p = Pedido.objects.get(id=pedido_id)
        # Calcular porcentagem de separação
        itens_separados_count = p.itens.filter(separado=True).count()
        total_itens_count = p.itens.count()
        porcentagem_separacao = round((itens_separados_count / total_itens_count * 100), 1) if total_itens_count > 0 else 0

        broadcast_to_websocket(
            "dashboard",
            "pedido_atualizado",
            {
                "pedido": {
                    "id": p.id,
                    "numero_orcamento": p.numero_orcamento,
                    "status": p.status,
                    "porcentagem_separacao": porcentagem_separacao
                }
            }
        )

            # Broadcast card_status update para cada pedido afetado
        broadcast_card_status_update(p)

    # Broadcast para painel de compras (para adicionar itens em real-time)
    logger.info(f"[PAINEL_COMPRAS] Iniciando broadcast para {len(itens_marcados)} itens marcados")
    for i in itens_marcados:
        marcado_em_formatted = timezone.localtime(i.marcado_compra_em).strftime('%d/%m/%Y %H:%M') if i.marcado_compra_em else None
        item_data = {
            "item": {
                "id": i.id,
                "pedido_id": i.pedido.id,
                "pedido_numero": i.pedido.numero_orcamento,
                "cliente": i.pedido.nome_cliente,
                "produto_codigo": i.produto.codigo,
                "produto_descricao": i.produto.descricao,
                "quantidade": str(i.quantidade_solicitada),
                "marcado_por": request.user.nome,
                "marcado_em": marcado_em_formatted,
                "comprado": i.compra_realizada
            }
        }
        logger.info(f"[PAINEL_COMPRAS] Broadcasting item_marcado_compra para item {i.id}, pedido #{i.pedido.numero_orcamento}")
        logger.debug(f"[PAINEL_COMPRAS] Item data: {item_data}")

        result = broadcast_to_websocket(
            "painel_compras",
            "item_marcado_compra",
            item_data
        )

        if result:
            logger.info(f"[PAINEL_COMPRAS] ✅ Broadcast bem-sucedido para item {i.id}")
        else:
            logger.error(f"[PAINEL_COMPRAS] ❌ Broadcast FALHOU para item {i.id}")

    return JsonResponse({
        'success': True,
        'itens_marcados': len(itens_marcados),
        'pedido_status': pedido.status
    })


@admin_or_compradora
@require_http_methods(["POST"])
def marcar_item_comprado_view(request, item_id):
    """
    View para marcar/desmarcar item como comprado no painel de compras.
    Disponível para COMPRADORA ou ADMINISTRADOR.
    """
    item = get_object_or_404(ItemPedido, id=item_id)
    pedido = item.pedido

    # Verificar se pedido não está deletado
    if pedido.deletado:
        return JsonResponse({'success': False, 'error': 'Pedido foi deletado.'}, status=400)

    # Verificar se item está marcado para compra
    if not item.em_compra:
        return JsonResponse({'success': False, 'error': 'Item não está marcado para compra.'}, status=400)

    # Toggle compra_realizada
    item.compra_realizada = not item.compra_realizada

    if item.compra_realizada:
        item.compra_realizada_por = request.user
        item.compra_realizada_em = timezone.now()
    else:
        item.compra_realizada_por = None
        item.compra_realizada_em = None

    item.save()

    # Auditoria
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='marcar_item_comprado' if item.compra_realizada else 'desmarcar_item_comprado',
        modelo='ItemPedido',
        objeto_id=item.id,
        dados_novos={
            'item_id': item.id,
            'pedido_id': pedido.id,
            'produto': item.produto.descricao,
            'comprado': item.compra_realizada
        },
        ip=ip,
        user_agent=user_agent
    )

    # Broadcast WebSocket para painel de compras
    comprado_em_formatted = None
    if item.compra_realizada and item.compra_realizada_em:
        comprado_em_formatted = timezone.localtime(item.compra_realizada_em).strftime('%d/%m/%Y %H:%M')

    broadcast_to_websocket(
        "painel_compras",
        "item_comprado",
        {
            "item": {
                "id": item.id,
                "pedido_id": pedido.id,
                "comprado": item.compra_realizada,
                "comprado_por": request.user.nome if item.compra_realizada else None,
                "comprado_em": comprado_em_formatted
            }
        }
    )

    # Broadcast WebSocket para página de detalhes do pedido (badge em tempo real)
    broadcast_to_websocket(
        f"pedido_{pedido.id}",
        "item_comprado",
        {
            "item": {
                "id": item.id,
                "comprado": item.compra_realizada,
                "comprado_por": request.user.nome if item.compra_realizada else None,
                "comprado_em": comprado_em_formatted
            }
        }
    )

    # Se item foi comprado E depois separado, remove do painel de compras
    # (broadcast para remover do painel será enviado pelo separar_item_view)

    return JsonResponse({
        'success': True,
        'comprado': item.compra_realizada,
        'comprado_por': request.user.nome if item.compra_realizada else None,
        'comprado_em': comprado_em_formatted
    })


@admin_or_separador
@require_http_methods(["POST"])
def substituir_item_view(request, item_id):
    """
    View para substituir produto em um item.
    Disponível para SEPARADOR ou ADMINISTRADOR.
    """
    item = get_object_or_404(ItemPedido, id=item_id)
    pedido = item.pedido

    # Verificar se pedido não está deletado
    if pedido.deletado:
        return JsonResponse({'success': False, 'error': 'Pedido foi deletado.'}, status=400)

    # Verificar se já está substituído
    if item.substituido:
        return JsonResponse({'success': False, 'error': 'Item já foi substituído.'}, status=400)

    # Verificar se já está separado
    if item.separado:
        return JsonResponse({'success': False, 'error': 'Item já está separado.'}, status=400)

    form = SubstituirProdutoForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    # Marcar como substituído E como separado (item substituído conta como separado)
    item.substituido = True
    item.produto_substituto = form.cleaned_data['produto_substituto']
    item.separado = True
    item.separado_por = request.user
    item.separado_em = timezone.now()
    item.save(update_fields=['substituido', 'produto_substituto', 'separado', 'separado_por', 'separado_em'])

    # Atualizar status do pedido se necessário
    if pedido.status == 'PENDENTE':
        pedido.status = 'EM_SEPARACAO'
        pedido.save()

    # Auditoria
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='substituir_item',
        modelo='ItemPedido',
        objeto_id=item.id,
        dados_novos={
            'item_id': item.id,
            'pedido_id': pedido.id,
            'produto_original': item.produto.descricao,
            'produto_substituto': item.produto_substituto
        },
        ip=ip,
        user_agent=user_agent
    )

    # Broadcast WebSocket
    broadcast_to_websocket(
        f"pedido_{pedido.id}",
        "item_substituido",
        {
            "item": {
                "id": item.id,
                "substituido": True,
                "produto_substituto": item.produto_substituto,
                "separado": True,
                "separado_por": request.user.nome,
                "separado_em": timezone.localtime(item.separado_em).strftime('%d/%m/%Y %H:%M') if item.separado_em else None
            }
        }
    )

    # Calcular porcentagem de separação para atualização em tempo real
    itens_separados_count = pedido.itens.filter(separado=True).count()
    total_itens_count = pedido.itens.count()
    porcentagem_separacao = round((itens_separados_count / total_itens_count * 100), 1) if total_itens_count > 0 else 0

    # Broadcast para dashboard
    broadcast_to_websocket(
        "dashboard",
        "pedido_atualizado",
        {
            "pedido": {
                "id": pedido.id,
                "numero_orcamento": pedido.numero_orcamento,
                "status": pedido.status,
                "porcentagem_separacao": porcentagem_separacao
            }
        }
    )

    # Broadcast card_status update
    broadcast_card_status_update(pedido)

    return JsonResponse({
        'success': True,
        'item_id': item.id,
        'produto_substituto': item.produto_substituto,
        'pedido_status': pedido.status,
        'porcentagem_separacao': porcentagem_separacao
    })


@admin_or_separador
@require_http_methods(["POST"])
def finalizar_pedido_view(request, pedido_id):
    """
    View para finalizar pedido.
    Valida se todos itens foram separados ou substituídos e nenhum está em compra.
    Disponível para SEPARADOR ou ADMINISTRADOR.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id, deletado=False)

    # Verificar se pode finalizar
    if not pedido.pode_ser_finalizado():
        return JsonResponse({
            'success': False,
            'error': 'Pedido não pode ser finalizado. Verifique se todos os itens foram separados/substituídos e nenhum está aguardando compra.'
        }, status=400)

    # Finalizar pedido
    pedido.status = 'FINALIZADO'
    pedido.data_finalizacao = timezone.now()
    pedido.save()

    # Auditoria
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='finalizar_pedido',
        modelo='Pedido',
        objeto_id=pedido.id,
        dados_novos={
            'pedido_id': pedido.id,
            'numero_orcamento': pedido.numero_orcamento,
            'data_finalizacao': pedido.data_finalizacao.isoformat()
        },
        ip=ip,
        user_agent=user_agent
    )

    # Broadcast WebSocket
    broadcast_to_websocket(
        f"pedido_{pedido.id}",
        "pedido_finalizado",
        {
            "pedido_id": pedido.id
        }
    )

    # Broadcast para dashboard
    broadcast_to_websocket(
        "dashboard",
        "pedido_finalizado",
        {
            "pedido_id": pedido.id,
            "numero_orcamento": pedido.numero_orcamento
        }
    )

    return JsonResponse({
        'success': True,
        'pedido_id': pedido.id,
        'redirect_url': '/dashboard/'
    })


@login_required_custom
@require_http_methods(["POST"])
def deletar_pedido_view(request, pedido_id):
    """
    View para fazer soft delete de pedido.
    Disponível para VENDEDOR que criou o pedido ou ADMINISTRADOR.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id, deletado=False)

    # Verificar permissão
    if request.user.tipo == 'ADMINISTRADOR':
        pode_deletar = True
    elif request.user.tipo == 'VENDEDOR' and pedido.vendedor == request.user:
        pode_deletar = True
    else:
        pode_deletar = False

    if not pode_deletar:
        return JsonResponse({
            'success': False,
            'error': 'Você não tem permissão para deletar este pedido.'
        }, status=403)

    # Soft delete
    pedido.deletado = True
    pedido.deletado_por = request.user
    pedido.deletado_em = timezone.now()
    pedido.save()

    # Auditoria
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='deletar_pedido',
        modelo='Pedido',
        objeto_id=pedido.id,
        dados_novos={
            'pedido_id': pedido.id,
            'numero_orcamento': pedido.numero_orcamento,
            'deletado_em': pedido.deletado_em.isoformat()
        },
        ip=ip,
        user_agent=user_agent
    )

    # Broadcast WebSocket
    broadcast_to_websocket(
        f"pedido_{pedido.id}",
        "pedido_deletado",
        {
            "pedido_id": pedido.id
        }
    )

    # Broadcast para dashboard (remove da lista)
    broadcast_to_websocket(
        "dashboard",
        "pedido_finalizado",  # Usa o mesmo evento para remover da lista
        {
            "pedido_id": pedido.id,
            "numero_orcamento": pedido.numero_orcamento
        }
    )

    return JsonResponse({
        'success': True,
        'pedido_id': pedido.id,
        'redirect_url': '/dashboard/'
    })


# =====================
# PAINEL DE COMPRAS - FASE 6
# =====================

from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from datetime import datetime, timedelta


@admin_or_compradora
@require_http_methods(["GET"])
def painel_compras_view(request):
    """
    Painel de compras - lista itens marcados para compra agrupados por pedido.
    Disponível para COMPRADORA ou ADMINISTRADOR.
    """
    # Filtros
    search_text = request.GET.get('search', '').strip()
    order_filter = request.GET.get('order', '').strip()

    # Query base: itens em compra (não comprados ainda) em pedidos ativos
    query = ItemPedido.objects.filter(
        em_compra=True,
        compra_realizada=False,
        pedido__deletado=False
    ).select_related('produto', 'pedido', 'pedido__vendedor', 'marcado_compra_por')

    # Aplicar filtros
    if search_text:
        query = query.filter(
            Q(produto__codigo__icontains=search_text) |
            Q(produto__descricao__icontains=search_text) |
            Q(pedido__nome_cliente__icontains=search_text)
        )

    if order_filter:
        query = query.filter(pedido__numero_orcamento__icontains=order_filter)

    # Agrupar por pedido
    pedidos_agrupados = {}

    for item in query:
        pedido_id = item.pedido.id

        if pedido_id not in pedidos_agrupados:
            pedidos_agrupados[pedido_id] = {
                'id': pedido_id,
                'numero': item.pedido.numero_orcamento,
                'cliente': item.pedido.nome_cliente if item.pedido.nome_cliente else 'Cliente não informado',
                'itens': []
            }

        pedidos_agrupados[pedido_id]['itens'].append({
            'id': item.id,
            'produto_codigo': item.produto.codigo,
            'produto_descricao': item.produto.descricao,
            'quantidade': item.quantidade_solicitada,
            'marcado_por': item.marcado_compra_por.nome if item.marcado_compra_por else 'N/A',
            'marcado_em': item.marcado_compra_em.strftime('%d/%m/%Y %H:%M') if item.marcado_compra_em else 'N/A',
            'comprado': item.compra_realizada
        })

    # Converter para lista e ordenar por número do pedido
    pedidos_lista = sorted(pedidos_agrupados.values(), key=lambda x: x['numero'])

    # Calcular estatísticas
    total_pedidos = len(pedidos_lista)
    total_itens = query.count()

    import json
    from django.core.serializers.json import DjangoJSONEncoder
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Painel Compras - Total pedidos: {total_pedidos}, Total itens: {total_itens}")
    logger.info(f"Painel Compras - Filtros: search='{search_text}', order='{order_filter}'")
    if total_pedidos > 0:
        logger.info(f"Painel Compras - Primeiro pedido: {pedidos_lista[0]['numero']} - {pedidos_lista[0]['cliente']}")

    context = {
        'pedidos': pedidos_lista,
        'pedidos_json': json.dumps(pedidos_lista, cls=DjangoJSONEncoder),
        'total_pedidos': total_pedidos,
        'total_itens': total_itens,
        'search_text': '',  # Always pass empty strings to prevent browser autocomplete issues
        'order_filter': '',  # Always pass empty strings to prevent browser autocomplete issues
    }

    return render(request, 'painel_compras.html', context)


@admin_or_compradora
@require_http_methods(["POST"])
def confirmar_compra_view(request, produto_codigo):
    """
    Confirma compra de todos os itens de um produto específico.
    Marca compra_realizada=True para todos itens do produto.
    Disponível para COMPRADORA ou ADMINISTRADOR.
    """
    # Buscar todos os itens do produto que estão em compra
    itens = ItemPedido.objects.filter(
        produto__codigo=produto_codigo,
        em_compra=True,
        compra_realizada=False,
        pedido__deletado=False
    ).select_related('produto', 'pedido')

    if not itens.exists():
        return JsonResponse({
            'success': False,
            'error': 'Nenhum item encontrado para este produto.'
        }, status=404)

    # Contar itens antes de atualizar
    total_itens = itens.count()
    produto_descricao = itens.first().produto.descricao

    # Atualizar todos os itens
    now = timezone.now()
    pedidos_afetados = set()

    for item in itens:
        item.compra_realizada = True
        item.compra_realizada_por = request.user
        item.compra_realizada_em = now
        item.save()
        pedidos_afetados.add(item.pedido.id)

    # Auditoria
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='confirmar_compra',
        modelo='ItemPedido',
        objeto_id=0,
        dados_novos={
            'produto_codigo': produto_codigo,
            'produto_descricao': produto_descricao,
            'total_itens': total_itens,
            'pedidos_afetados': list(pedidos_afetados)
        },
        ip=ip,
        user_agent=user_agent
    )

    # Broadcast WebSocket para painel de compras
    broadcast_to_websocket(
        "painel_compras",
        "compra_confirmada",
        {
            "produto": {
                "codigo": produto_codigo,
                "descricao": produto_descricao,
                "total_itens": total_itens
            }
        }
    )

    # Broadcast para cada pedido afetado
    for pedido_id in pedidos_afetados:
        broadcast_to_websocket(
            f"pedido_{pedido_id}",
            "compra_realizada",
            {
                "produto_codigo": produto_codigo
            }
        )

    # Broadcast para dashboard
    broadcast_to_websocket(
        "dashboard",
        "compra_confirmada",
        {
            "produto_codigo": produto_codigo
        }
    )

    return JsonResponse({
        'success': True,
        'produto_codigo': produto_codigo,
        'total_itens': total_itens
    })


@admin_or_compradora
@require_http_methods(["GET"])
def historico_compras_view(request):
    """
    Histórico de compras realizadas nos últimos 90 dias.
    Disponível para COMPRADORA ou ADMINISTRADOR.
    """
    # Data limite: 90 dias atrás
    data_limite = timezone.now() - timedelta(days=90)

    # Buscar itens com compra realizada nos últimos 90 dias
    query = ItemPedido.objects.filter(
        compra_realizada=True,
        compra_realizada_em__gte=data_limite
    ).select_related('produto', 'pedido', 'compra_realizada_por').order_by('-compra_realizada_em')

    # Agrupar por produto e data de compra
    compras_agrupadas = {}

    for item in query:
        # Chave: produto_codigo + data (apenas dia)
        data_compra = item.compra_realizada_em.date()
        chave = f"{item.produto.codigo}_{data_compra}"

        if chave not in compras_agrupadas:
            compras_agrupadas[chave] = {
                'produto_codigo': item.produto.codigo,
                'produto_descricao': item.produto.descricao,
                'data_compra': item.compra_realizada_em,
                'comprado_por': item.compra_realizada_por.nome if item.compra_realizada_por else 'N/A',
                'quantidade_total': 0,
                'pedidos': []
            }

        compras_agrupadas[chave]['quantidade_total'] += item.quantidade_solicitada
        compras_agrupadas[chave]['pedidos'].append({
            'numero': item.pedido.numero_orcamento,
            'quantidade': item.quantidade_solicitada
        })

    # Converter para lista e ordenar por data (mais recente primeiro)
    historico_lista = sorted(
        compras_agrupadas.values(),
        key=lambda x: x['data_compra'],
        reverse=True
    )

    # Paginação (20 por página)
    paginator = Paginator(historico_lista, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_compras': len(historico_lista),
    }

    return render(request, 'historico_compras.html', context)


# =====================
# FASE 7: GESTÃO DE USUÁRIOS
# =====================

@login_required_custom
@administrador_required
@require_http_methods(["GET"])
def lista_usuarios_view(request):
    """
    Lista todos os usuários do sistema (ativos e inativos).
    Apenas ADMINISTRADOR tem acesso.
    """
    usuarios = Usuario.objects.all().order_by('-ativo', 'numero_login')

    context = {
        'usuarios': usuarios,
    }

    return render(request, 'lista_usuarios.html', context)


@login_required_custom
@administrador_required
@require_http_methods(["GET", "POST"])
def criar_usuario_view(request):
    """
    Cria novo usuário no sistema.
    Admin define: numero_login, nome, tipo, PIN inicial.
    Apenas ADMINISTRADOR tem acesso.
    """
    if request.method == 'POST':
        form = CriarUsuarioForm(request.POST)

        if form.is_valid():
            # Criar usuário
            usuario = Usuario(
                numero_login=form.cleaned_data['numero_login'],
                nome=form.cleaned_data['nome'],
                tipo=form.cleaned_data['tipo'],
                ativo=True,
            )

            # Definir PIN
            usuario.set_pin(form.cleaned_data['pin'])

            # Salvar
            usuario.save()

            # Auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                acao='criar_usuario',
                modelo='Usuario',
                objeto_id=usuario.id,
                dados_novos={
                    'numero_login': usuario.numero_login,
                    'nome': usuario.nome,
                    'tipo': usuario.tipo,
                },
                ip=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )

            messages.success(request, f'Usuário {usuario.nome} ({usuario.numero_login}) criado com sucesso!')
            return redirect('lista_usuarios')

        else:
            # Mostrar erros do formulário
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')

    else:
        form = CriarUsuarioForm()

    context = {
        'form': form,
    }

    return render(request, 'criar_usuario.html', context)


@login_required_custom
@administrador_required
@require_http_methods(["GET", "POST"])
def editar_usuario_view(request, usuario_id):
    """
    Edita usuário existente (nome, tipo, ativo).
    Não permite editar numero_login nem PIN.
    Apenas ADMINISTRADOR tem acesso.
    """
    usuario = get_object_or_404(Usuario, id=usuario_id)

    # Não permite editar o próprio usuário admin inicial (1000)
    if usuario.numero_login == 1000 and request.user.numero_login != 1000:
        messages.error(request, 'Não é permitido editar o administrador principal.')
        return redirect('lista_usuarios')

    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST)

        if form.is_valid():
            # Dados anteriores para auditoria
            dados_anteriores = {
                'nome': usuario.nome,
                'tipo': usuario.tipo,
                'ativo': usuario.ativo,
            }

            # Atualizar dados
            usuario.nome = form.cleaned_data['nome']
            usuario.tipo = form.cleaned_data['tipo']
            usuario.ativo = form.cleaned_data['ativo']
            usuario.save()

            # Auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                acao='editar_usuario',
                modelo='Usuario',
                objeto_id=usuario.id,
                dados_anteriores=dados_anteriores,
                dados_novos={
                    'nome': usuario.nome,
                    'tipo': usuario.tipo,
                    'ativo': usuario.ativo,
                },
                ip=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )

            messages.success(request, f'Usuário {usuario.nome} atualizado com sucesso!')
            return redirect('lista_usuarios')

        else:
            # Mostrar erros do formulário
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')

    else:
        # Preencher formulário com dados atuais
        form = EditarUsuarioForm(initial={
            'nome': usuario.nome,
            'tipo': usuario.tipo,
            'ativo': usuario.ativo,
        })

    context = {
        'form': form,
        'usuario': usuario,
    }

    return render(request, 'editar_usuario.html', context)


@login_required_custom
@administrador_required
@require_http_methods(["GET", "POST"])
def resetar_pin_usuario_view(request, usuario_id):
    """
    Reseta o PIN de um usuário.
    Apenas ADMINISTRADOR tem acesso.
    """
    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        form = ResetarPinForm(request.POST)

        if form.is_valid():
            # Resetar tentativas e bloqueio
            usuario.tentativas_login = 0
            usuario.bloqueado_ate = None

            # Definir novo PIN
            usuario.set_pin(form.cleaned_data['pin'])
            usuario.save()

            # Limpar rate limit cache se existir
            if usuario.numero_login in RATE_LIMIT_CACHE:
                del RATE_LIMIT_CACHE[usuario.numero_login]

            # Auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                acao='resetar_pin',
                modelo='Usuario',
                objeto_id=usuario.id,
                dados_novos={
                    'numero_login': usuario.numero_login,
                    'nome': usuario.nome,
                },
                ip=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )

            messages.success(request, f'PIN de {usuario.nome} ({usuario.numero_login}) resetado com sucesso!')
            return redirect('lista_usuarios')

        else:
            # Mostrar erros do formulário
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')

    else:
        form = ResetarPinForm()

    context = {
        'form': form,
        'usuario': usuario,
    }

    return render(request, 'resetar_pin_usuario.html', context)


@login_required_custom
@administrador_required
@require_http_methods(["POST"])
def toggle_ativo_usuario_view(request, usuario_id):
    """
    Ativa/desativa usuário (AJAX-friendly).
    Apenas ADMINISTRADOR tem acesso.
    """
    usuario = get_object_or_404(Usuario, id=usuario_id)

    # Não permite desativar o admin inicial (1000)
    if usuario.numero_login == 1000:
        messages.error(request, 'Não é permitido desativar o administrador principal.')
        return redirect('lista_usuarios')

    # Toggle
    dados_anteriores = {'ativo': usuario.ativo}
    usuario.ativo = not usuario.ativo
    usuario.save()

    # Auditoria
    acao = 'ativar_usuario' if usuario.ativo else 'desativar_usuario'
    LogAuditoria.objects.create(
        usuario=request.user,
        acao=acao,
        modelo='Usuario',
        objeto_id=usuario.id,
        dados_anteriores=dados_anteriores,
        dados_novos={'ativo': usuario.ativo},
        ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
    )

    status_text = 'ativado' if usuario.ativo else 'desativado'
    messages.success(request, f'Usuário {usuario.nome} {status_text} com sucesso!')

    return redirect('lista_usuarios')


# =====================
# FASE 8: HISTÓRICO E MÉTRICAS
# =====================

@login_required_custom
def historico_view(request):
    """
    Exibe histórico de pedidos com filtros avançados.
    Acessível por todos os usuários logados.
    """
    # Inicializar form com dados do GET
    form = HistoricoFiltrosForm(request.GET or None)

    # Query base: apenas pedidos ativos (não deletados)
    pedidos = Pedido.objects.filter(deletado=False).select_related('vendedor')

    # Aplicar filtros
    if form.is_valid():
        # Filtro de período
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')

        if data_inicio:
            pedidos = pedidos.filter(data_criacao__date__gte=data_inicio)
        if data_fim:
            pedidos = pedidos.filter(data_criacao__date__lte=data_fim)

        # Filtro de vendedor
        vendedor_id = form.cleaned_data.get('vendedor')
        if vendedor_id:
            pedidos = pedidos.filter(vendedor_id=vendedor_id)

        # Filtro de status
        status = form.cleaned_data.get('status')
        if status:
            pedidos = pedidos.filter(status=status)

    # Ordenar por data de criação (mais recentes primeiro)
    pedidos = pedidos.order_by('-data_criacao')

    # Paginação (20 pedidos por página)
    paginator = Paginator(pedidos, 20)
    page = request.GET.get('page', 1)

    try:
        pedidos_paginados = paginator.page(page)
    except PageNotAnInteger:
        pedidos_paginados = paginator.page(1)
    except EmptyPage:
        pedidos_paginados = paginator.page(paginator.num_pages)

    # Log de auditoria
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='VISUALIZAR',
        modelo='Historico',
        objeto_id=0,
        dados_novos={'filtros': request.GET.dict()},
        ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
    )

    context = {
        'form': form,
        'pedidos': pedidos_paginados,
        'total_pedidos': paginator.count,
    }

    return render(request, 'historico.html', context)


@login_required_custom
@require_http_methods(["GET", "POST"])
def metricas_view(request):
    """
    Exibe métricas de performance do sistema.
    Acessível por todos os usuários logados.
    Botão 'Atualizar' recalcula via POST.
    """
    from apps.core.utils import calcular_metricas_periodo

    # Definir período padrão (últimos 30 dias)
    data_fim = timezone.localdate()
    data_inicio = data_fim - timedelta(days=30)

    # Se POST, recalcular métricas com período customizado (se fornecido)
    if request.method == 'POST':
        # Pode vir do formulário customizado de período
        periodo_selecionado = request.POST.get('periodo', '30')

        if periodo_selecionado == '7':
            data_inicio = data_fim - timedelta(days=7)
        elif periodo_selecionado == '30':
            data_inicio = data_fim - timedelta(days=30)
        elif periodo_selecionado == '90':
            data_inicio = data_fim - timedelta(days=90)
        elif periodo_selecionado == 'custom':
            # Período customizado
            data_inicio_str = request.POST.get('data_inicio')
            data_fim_str = request.POST.get('data_fim')

            if data_inicio_str:
                try:
                    data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                except ValueError:
                    messages.error(request, 'Data de início inválida.')
            if data_fim_str:
                try:
                    data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
                except ValueError:
                    messages.error(request, 'Data de fim inválida.')

        messages.success(request, 'Métricas atualizadas com sucesso!')

    # Calcular métricas
    metricas = calcular_metricas_periodo(data_inicio, data_fim)

    # Log de auditoria
    LogAuditoria.objects.create(
        usuario=request.user,
        acao='VISUALIZAR_METRICAS' if request.method == 'GET' else 'ATUALIZAR_METRICAS',
        modelo='Metricas',
        objeto_id=0,
        dados_novos={
            'periodo': f"{data_inicio} a {data_fim}",
            'metodo': request.method
        },
        ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
    )

    context = {
        'metricas': metricas,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }

    return render(request, 'metricas.html', context)


# =====================
# FASE 9: Configuração do Sistema
# =====================

@login_required_custom
@administrador_required
@require_http_methods(["GET", "POST"])
def configurar_empty_state_view(request):
    """
    Configurar imagem customizada do empty state.
    Apenas ADMINISTRADOR tem acesso.

    Permite upload de imagens personalizadas que serão:
    - Validadas (tamanho, dimensões, formato)
    - Otimizadas automaticamente (resize, compressão, conversão para WebP)
    - Armazenadas em Railway Volumes (/data/media em produção)
    """
    from .utils.image_utils import optimize_empty_state_image

    # Load singleton configuration
    config = SistemaConfig.load()

    if request.method == 'POST':
        form = EmptyStateImageForm(request.POST, request.FILES)

        if form.is_valid():
            arquivo = form.cleaned_data.get('empty_state_image')

            if arquivo:
                # Otimizar imagem se não for SVG
                arquivo_otimizado = optimize_empty_state_image(arquivo)

                # Salvar arquivo otimizado ou original (SVG)
                if arquivo_otimizado:
                    config.empty_state_image = arquivo_otimizado
                else:
                    # SVG não precisa otimização
                    config.empty_state_image = arquivo

                config.save()

                # Log audit
                LogAuditoria.objects.create(
                    usuario=request.user,
                    acao='atualizar_empty_state_image',
                    modelo='SistemaConfig',
                    objeto_id=config.id,
                    dados_novos={'imagem': arquivo.name},
                    ip=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                )

                messages.success(request, 'Imagem do empty state atualizada com sucesso!')
            else:
                # Remover imagem customizada (restaurar default)
                if config.empty_state_image:
                    config.empty_state_image.delete()
                    config.empty_state_image = None
                    config.save()

                    # Log audit
                    LogAuditoria.objects.create(
                        usuario=request.user,
                        acao='remover_empty_state_image',
                        modelo='SistemaConfig',
                        objeto_id=config.id,
                        dados_novos={'imagem': None},
                        ip=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                    )

                    messages.success(request, 'Imagem customizada removida. Usando imagem padrão.')

            return redirect('configurar_empty_state')
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = EmptyStateImageForm()

    context = {
        'form': form,
        'config': config,
    }

    return render(request, 'configurar_empty_state.html', context)
