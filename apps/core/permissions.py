from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def login_required_custom(view_func):
    """
    Decorator customizado para verificar autenticação.
    Redireciona para login se não autenticado.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Você precisa fazer login para acessar esta página.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def tipo_usuario_required(*tipos_permitidos):
    """
    Decorator factory para verificar tipo de usuário.
    Uso: @tipo_usuario_required('VENDEDOR', 'ADMINISTRADOR')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Você precisa fazer login para acessar esta página.')
                return redirect('login')

            if request.user.tipo not in tipos_permitidos:
                messages.error(request, f'Acesso negado. Esta área é restrita para: {", ".join(tipos_permitidos)}.')
                return redirect('dashboard')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def vendedor_required(view_func):
    """
    Decorator para views que exigem usuário do tipo VENDEDOR.
    """
    return tipo_usuario_required('VENDEDOR')(view_func)


def separador_required(view_func):
    """
    Decorator para views que exigem usuário do tipo SEPARADOR.
    """
    return tipo_usuario_required('SEPARADOR')(view_func)


def compradora_required(view_func):
    """
    Decorator para views que exigem usuário do tipo COMPRADORA.
    """
    return tipo_usuario_required('COMPRADORA')(view_func)


def administrador_required(view_func):
    """
    Decorator para views que exigem usuário do tipo ADMINISTRADOR.
    """
    return tipo_usuario_required('ADMINISTRADOR')(view_func)


def admin_or_vendedor(view_func):
    """
    Decorator para views que permitem ADMINISTRADOR ou VENDEDOR.
    """
    return tipo_usuario_required('ADMINISTRADOR', 'VENDEDOR')(view_func)


def admin_or_separador(view_func):
    """
    Decorator para views que permitem ADMINISTRADOR ou SEPARADOR.
    """
    return tipo_usuario_required('ADMINISTRADOR', 'SEPARADOR')(view_func)


def admin_or_compradora(view_func):
    """
    Decorator para views que permitem ADMINISTRADOR ou COMPRADORA.
    """
    return tipo_usuario_required('ADMINISTRADOR', 'COMPRADORA')(view_func)
