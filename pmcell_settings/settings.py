"""
Django settings for pmcell_settings project.
Version: 1.0.1 - Force redeploy with Redis configuration
"""

from pathlib import Path
import os
from decouple import config, Csv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-ew)xqc30our7zgh0%)0y%o--=@er3+huwd4w=%j_t-2x_gts3e')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

# Railway specific
if 'RAILWAY_ENVIRONMENT' in os.environ:
    ALLOWED_HOSTS = ['*']
    DEBUG = False  # Force DEBUG=False in Railway production

# Application definition
INSTALLED_APPS = [
    'daphne',  # Django Channels ASGI server (deve estar antes de django.contrib.staticfiles)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'channels',

    # Apps do projeto
    'apps.core',
    'apps.api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Adiciona WhiteNoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.AuditoriaMiddleware',  # Middleware de auditoria (FASE 2)
]

ROOT_URLCONF = 'pmcell_settings.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pmcell_settings.wsgi.application'

# ASGI Application (Django Channels)
ASGI_APPLICATION = 'pmcell_settings.asgi.application'

# Custom User Model
AUTH_USER_MODEL = 'core.Usuario'

# Django Channels
# WebSocket Channel Layers Configuration
# Use Redis if available (production/Railway with Redis addon), fallback to InMemory (local dev)
redis_url = config('REDIS_URL', default=None)

if 'RAILWAY_ENVIRONMENT' in os.environ and redis_url:
    # Production with Redis (multiple workers support)
    print(f"[CHANNEL_LAYERS] Redis URL detectado: {redis_url[:20]}...{redis_url[-20:]}")
    try:
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels_redis.core.RedisChannelLayer',
                'CONFIG': {
                    'hosts': [redis_url],
                    'capacity': 1500,  # Max messages per channel
                    'expiry': 10,  # Message expiry (seconds)
                },
            }
        }
        print("[CHANNEL_LAYERS] ✅ Using Redis for WebSocket (Production)")
        print("[CHANNEL_LAYERS] Backend: channels_redis.core.RedisChannelLayer")
    except Exception as e:
        print(f"[CHANNEL_LAYERS] ❌ ERRO ao configurar Redis: {e}")
        print("[CHANNEL_LAYERS] Fallback para InMemory")
        CHANNEL_LAYERS = {
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            }
        }
else:
    # Development or Railway without Redis
    if 'RAILWAY_ENVIRONMENT' in os.environ:
        print("[CHANNEL_LAYERS] ⚠️  AVISO: Railway detectado mas REDIS_URL não configurado!")
        print("[CHANNEL_LAYERS] WebSockets podem não funcionar com múltiplos workers")
    print("[CHANNEL_LAYERS] Using InMemory for WebSocket (Development/Single Worker)")
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        }
    }


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Diretórios de arquivos estáticos
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# WhiteNoise settings
# Using CompressedStaticFilesStorage instead of CompressedManifestStaticFilesStorage
# to avoid 404 errors when manifest build is incomplete in Railway
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Media files (User-uploaded content)
# https://docs.djangoproject.com/en/4.2/howto/static-files/
MEDIA_URL = '/media/'

# Use Railway Volumes for persistent storage in production
if 'RAILWAY_ENVIRONMENT' in os.environ:
    MEDIA_ROOT = '/data/media'  # Railway Volume mount point
else:
    MEDIA_ROOT = BASE_DIR / 'media'  # Local development

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Security settings para produção
if not DEBUG:
    # SECURE_SSL_REDIRECT disabled for Railway (proxy already handles HTTPS)
    # Railway's proxy terminates SSL, causing redirect loop if enabled
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# CSRF Settings
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:8000', cast=Csv())

# Railway
if 'RAILWAY_ENVIRONMENT' in os.environ:
    CSRF_TRUSTED_ORIGINS = [
        'https://*.railway.app',
        'https://*.up.railway.app'
    ]

# ============================================
# CONFIGURAÇÕES DE SESSÃO - FASE 2
# ============================================

# Timeout de sessão: 8 horas (28800 segundos)
SESSION_COOKIE_AGE = 28800

# Salvar sessão a cada request (para manter timeout ativo)
SESSION_SAVE_EVERY_REQUEST = True

# Expirar sessão ao fechar navegador
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Nome do cookie de sessão
SESSION_COOKIE_NAME = 'pmcell_sessionid'

# Cookie httponly (não acessível via JavaScript)
SESSION_COOKIE_HTTPONLY = True

# Segurança de cookies (apenas HTTPS em produção)
if not DEBUG:
    SESSION_COOKIE_SECURE = True