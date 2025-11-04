from django.utils.deprecation import MiddlewareMixin
from .models import LogAuditoria
import json


class AuditoriaMiddleware(MiddlewareMixin):
    """
    Middleware para registrar todas as ações dos usuários autenticados.
    Registra: usuário, ação (view), IP, user_agent, timestamp
    """

    # Views que não devem ser auditadas
    EXCLUDE_PATHS = [
        '/static/',
        '/media/',
        '/admin/jsi18n/',
        '/favicon.ico',
    ]

    # Views que queremos auditar mas sem criar log (read-only)
    READ_ONLY_VIEWS = [
        'dashboard',
        'pedido_detalhe',
        'painel_compras',
        'historico',
        'metricas',
    ]

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Executa antes da view ser chamada.
        Registra a ação no LogAuditoria se o usuário estiver autenticado.
        """
        # Não auditar paths excluídos
        for path in self.EXCLUDE_PATHS:
            if request.path.startswith(path):
                return None

        # Não auditar se usuário não está autenticado
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None

        # Não auditar views de login/logout
        view_name = view_func.__name__ if hasattr(view_func, '__name__') else str(view_func)
        if view_name in ['login_view', 'logout_view']:
            return None

        # Capturar informações da requisição
        try:
            ip = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]

            # Determinar a ação (nome da view)
            acao = view_name

            # Para views read-only, não criar log (economiza espaço)
            if acao in self.READ_ONLY_VIEWS and request.method == 'GET':
                return None

            # Capturar dados da requisição (apenas POST/PUT/DELETE)
            dados_novos = None
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                try:
                    if request.content_type == 'application/json':
                        dados_novos = json.loads(request.body)
                    else:
                        # Para formulários, capturar POST data (sem senhas/pins)
                        dados_novos = {
                            k: v for k, v in request.POST.items()
                            if k not in ['pin', 'password', 'csrfmiddlewaretoken']
                        }
                except:
                    dados_novos = None

            # Criar log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                acao=acao,
                modelo='Request',  # Será atualizado na view se necessário
                objeto_id=0,  # Será atualizado na view se necessário
                dados_novos=dados_novos,
                ip=ip,
                user_agent=user_agent
            )

        except Exception as e:
            # Não quebrar a aplicação se auditoria falhar
            print(f"Erro ao criar log de auditoria: {e}")

        return None

    def get_client_ip(self, request):
        """
        Obtém o IP real do cliente, considerando proxies.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
