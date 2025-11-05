from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from datetime import timedelta
from .models import Usuario, LogAuditoria
from .permissions import (
    login_required_custom,
    administrador_required,
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

    # Buscar apenas pedidos ativos (não finalizados e não deletados)
    pedidos = Pedido.objects.filter(
        deletado=False
    ).exclude(
        status__in=['FINALIZADO', 'CANCELADO']
    ).select_related('vendedor').order_by('-data_criacao')

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
        pedidos_data.append({
            'id': pedido.id,
            'numero_orcamento': pedido.numero_orcamento,
            'cliente': pedido.nome_cliente,
            'vendedor': pedido.vendedor.nome,
            'vendedor_id': pedido.vendedor.id,
            'status': pedido.status,
            'status_display': pedido.get_status_display(),
            'data': pedido.data.strftime('%d/%m/%Y'),
            'data_criacao': pedido.data_criacao.strftime('%d/%m/%Y %H:%M'),
            'total_itens': pedido.itens.count(),
        })

    context = {
        'usuario': request.user,
        'pedidos': pedidos_data,
        'vendedores': vendedores,
        'metricas': {
            'tempo_medio': formatar_tempo(metricas['tempo_medio_separacao']),
            'pedidos_em_aberto': metricas['pedidos_em_aberto'],
            'total_pedidos_hoje': metricas['total_pedidos_hoje'],
        }
    }

    return render(request, 'dashboard.html', context)


@login_required_custom
def pedido_detalhe_view(request, pedido_id):
    """
    View de detalhes do pedido (será implementada na FASE 5)
    Por enquanto, redireciona para dashboard com mensagem
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)
    messages.success(request, f'Pedido #{pedido.numero_orcamento} criado com sucesso!')
    return redirect('dashboard')


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

    if request.method == 'POST':
        form = ConfirmarPedidoForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Criar pedido
                    pedido = Pedido.objects.create(
                        numero_orcamento=dados_pdf['numero_orcamento'],
                        codigo_cliente=dados_pdf['codigo_cliente'],
                        nome_cliente=dados_pdf['nome_cliente'],
                        vendedor=request.user,
                        data=dados_pdf['data'],
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
                                    "data": pedido.data.strftime('%d/%m/%Y'),
                                    "data_criacao": pedido.data_criacao.strftime('%d/%m/%Y %H:%M'),
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
                    'dados_pdf': dados_pdf
                })
    else:
        form = ConfirmarPedidoForm()

    return render(request, 'confirmar_pedido.html', {
        'form': form,
        'dados_pdf': dados_pdf
    })
