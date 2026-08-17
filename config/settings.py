# config/settings.py
import os
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')



ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')

if ENVIRONMENT == 'production':
    from .settings_production import *
else:
    # Development settings
    DEBUG = True
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',  # <-- REQUIRED for allauth
    
    # Third party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'django_ratelimit',
    'django_redis',
    'widget_tweaks',
    'import_export',
    
    # Allauth - must be in this order
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    
    # Channels
    'channels',
    
    # Local apps
    'core',
    'accounts',
    'services',
    'projects',
    'payments',
    'chat',
    'notifications',
    'reviews',
    'dashboard',
    'admin_dashboard',
]

# Sites framework - REQUIRED for allauth
SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # <-- Add this for allauth
]

ROOT_URLCONF = 'config.urls'

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
                'django.template.context_processors.request',  # Required for allauth
                'core.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'  # <-- Add this for Channels

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Authentication backends
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

# Allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_LOGOUT_ON_GET = True

# Social account providers
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    },
    'facebook': {
        'METHOD': 'oauth2',
        'SCOPE': ['email', 'public_profile'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs
LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Use console for development
# For production, use:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = config('EMAIL_HOST')
# EMAIL_PORT = config('EMAIL_PORT', cast=int)
# EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
# EMAIL_HOST_USER = config('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
# DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Platform settings
PLATFORM_FEE_PERCENTAGE = config('PLATFORM_FEE_PERCENTAGE', default=10, cast=int)
DEPOSIT_DEFAULT_PERCENTAGE = 30
CURRENCY = 'KES'
CURRENCY_SYMBOL = 'KSh'

# Security settings (relaxed for development)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ============================================================
# CACHE CONFIGURATION
# ============================================================

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'timeout': 20,
            },
            'MAX_CONNECTIONS': 1000,
            'PICKLE_VERSION': -1,
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'sakafundi',
        'TIMEOUT': 86400,  # 24 hours default timeout
    }
}

# ============================================================
# CHANNELS / WEBSOCKET CONFIGURATION
# ============================================================

# Redis Channel Layer for WebSockets
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [config('REDIS_URL', default='redis://127.0.0.1:6379/1')],
            "symmetric_encryption_keys": [SECRET_KEY[:32]],
        },
    },
}

# If Redis is not available, use in-memory (for development)
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels.layers.InMemoryChannelLayer',
#     },
# }

# ============================================================
# RATE LIMITING
# ============================================================

RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_HEADER_ENABLED = True
RATELIMIT_HEADER_LIMIT = 'X-RateLimit-Limit'
RATELIMIT_HEADER_REMAINING = 'X-RateLimit-Remaining'
RATELIMIT_HEADER_RESET = 'X-RateLimit-Reset'

# ============================================================
# DJANGO REDIS LOGGER
# ============================================================

DJANGO_REDIS_LOGGER = 'django_redis.loggers.CacheLogger'

# ============================================================
# SESSION CONFIGURATION (Optional - store sessions in cache)
# ============================================================

# SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = "default"

# ============================================================
# ENVIRONMENT SPECIFIC SETTINGS
# ============================================================

ENVIRONMENT = config('DJANGO_ENV', default='development')

if ENVIRONMENT == 'production':
    DEBUG = False
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # Use PostgreSQL in production
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }

# ============================================================
# LOGGING CONFIGURATION
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django_redis': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'channels': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# ============================================================
# CELERY CONFIGURATION (Optional - for async tasks)
# ============================================================

# CELERY_BROKER_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/0')
# CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://127.0.0.1:6379/0')
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = TIME_ZONE