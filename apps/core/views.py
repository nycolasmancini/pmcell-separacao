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
    Dashboard principal (será implementado na FASE 4)
    """
    return render(request, 'dashboard.html', {
        'usuario': request.user
    })
