from django.shortcuts import render, redirect
from django.conf import settings


def home_view(request):
    """
    View inicial - redireciona para dashboard se autenticado,
    senão para login.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')