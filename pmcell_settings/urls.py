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
from .views import home_view
from apps.core.views import (
    login_view,
    logout_view,
    dashboard,
    reset_pin_view,
)

urlpatterns = [
    # Home (redireciona para login ou dashboard)
    path('', home_view, name='home'),

    # Autenticação
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # Dashboard
    path('dashboard/', dashboard, name='dashboard'),

    # Admin - Reset PIN
    path('admin/reset-pin/<int:user_id>/', reset_pin_view, name='reset_pin'),

    # Django Admin
    path('admin/', admin.site.urls),
]
