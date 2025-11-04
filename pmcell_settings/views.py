from django.shortcuts import render
from django.conf import settings


def home_view(request):
    """View inicial para teste de deploy"""
    context = {
        'debug': settings.DEBUG,
    }
    return render(request, 'home.html', context)