# config/settings.py

import os
import sys
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# ENVIRONMENT DETECTION
# ============================================================

ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')
print(f"🔍 ENVIRONMENT: {ENVIRONMENT}", file=sys.stderr)

# ============================================================
# LOAD .env FILE (ONLY IN DEVELOPMENT, DON'T OVERRIDE)
# ============================================================

if ENVIRONMENT == 'development':
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / '.env', override=False)
        print("✅ Loaded .env for development (no override)", file=sys.stderr)
    except ImportError:
        pass
else:
    print("ℹ️ Production mode: Skipping .env loading", file=sys.stderr)

# ============================================================
# DEBUG OUTPUT
# ============================================================

print("=" * 60, file=sys.stderr)
print(f"DJANGO_ENV: {os.environ.get('DJANGO_ENV', 'NOT SET')}", file=sys.stderr)
print(f"ALLOWED_HOSTS env: {os.environ.get('ALLOWED_HOSTS', 'NOT SET')}", file=sys.stderr)
print(f"DATABASE_URL env: {os.environ.get('DATABASE_URL', 'NOT SET')[:50] if os.environ.get('DATABASE_URL') else 'NOT SET'}", file=sys.stderr)
print("=" * 60, file=sys.stderr)

# ============================================================
# BASE SECURITY SETTINGS
# ============================================================

SECRET_KEY = config('SECRET_KEY')

if ENVIRONMENT == 'production':
    DEBUG = False
    ALLOWED_HOSTS = [
        '.onrender.com',
        'sakafundi.onrender.com',
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
    ]
    
    # CSRF Trusted Origins
    CSRF_TRUSTED_ORIGINS = [
        'https://*.onrender.com',
        'https://sakafundi.onrender.com',
        'http://*.onrender.com',
        'http://sakafundi.onrender.com',
    ]
    
    # Security Settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
else:
    DEBUG = True
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
    CSRF_TRUSTED_ORIGINS = ['http://localhost:8000']
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

print(f"🔒 CSRF_TRUSTED_ORIGINS: {CSRF_TRUSTED_ORIGINS}", file=sys.stderr)

# ============================================================
# APPLICATION DEFINITION
# ============================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    
    # Third party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'django_ratelimit',
    'django_redis',
    'widget_tweaks',
    'import_export',
    
    # Allauth
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

# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# ============================================================
# URL CONFIGURATION
# ============================================================

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ============================================================
# TEMPLATES
# ============================================================

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
                'core.context_processors.site_settings',
            ],
        },
    },
]

# ============================================================
# DATABASE
# ============================================================

# Get DATABASE_URL from environment
database_url = os.environ.get('DATABASE_URL')

if database_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            ssl_require=True
        )
    }
    print(f"✅ DATABASE: Using PostgreSQL from DATABASE_URL", file=sys.stderr)
elif ENVIRONMENT == 'production':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'sakafundi'),
            'USER': os.environ.get('DB_USER', 'sakafundi_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }
    print(f"⚠️ DATABASE: Using PostgreSQL from individual variables", file=sys.stderr)
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print(f"🔧 DATABASE: Using SQLite for development", file=sys.stderr)

print(f"🔍 FINAL DATABASE ENGINE: {DATABASES['default']['ENGINE']}", file=sys.stderr)
print(f"🔍 FINAL DATABASE NAME: {DATABASES['default']['NAME']}", file=sys.stderr)

# ============================================================
# CUSTOM USER MODEL
# ============================================================

AUTH_USER_MODEL = 'accounts.User'

# ============================================================
# AUTHENTICATION
# ============================================================

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

SITE_ID = 1

# ============================================================
# ALLAUTH SETTINGS
# ============================================================

ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/300',
}

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

# ============================================================
# PASSWORD VALIDATION
# ============================================================

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

# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# ============================================================
# STATIC & MEDIA FILES
# ============================================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================
# DEFAULT FIELD
# ============================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# LOGIN/LOGOUT
# ============================================================

LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'

# ============================================================
# CRISPY FORMS
# ============================================================

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ============================================================
# EMAIL
# ============================================================

if ENVIRONMENT == 'production':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@sakafundi.co.ke')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ============================================================
# PLATFORM SETTINGS
# ============================================================

PLATFORM_FEE_PERCENTAGE = config('PLATFORM_FEE_PERCENTAGE', default=10, cast=int)
DEPOSIT_DEFAULT_PERCENTAGE = 30
CURRENCY = 'KES'
CURRENCY_SYMBOL = 'KSh'

# ============================================================
# CACHE
# ============================================================

if ENVIRONMENT == 'production':
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
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
            'TIMEOUT': 86400,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# ============================================================
# CHANNELS / WEBSOCKETS
# ============================================================

if ENVIRONMENT == 'production':
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [config('REDIS_URL', default='redis://localhost:6379/1')],
                "symmetric_encryption_keys": [SECRET_KEY[:32]],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# ============================================================
# RATE LIMITING
# ============================================================

if ENVIRONMENT == 'production':
    RATELIMIT_ENABLE = True
else:
    RATELIMIT_ENABLE = False

RATELIMIT_USE_CACHE = 'default'
RATELIMIT_HEADER_ENABLED = True
RATELIMIT_HEADER_LIMIT = 'X-RateLimit-Limit'
RATELIMIT_HEADER_REMAINING = 'X-RateLimit-Remaining'
RATELIMIT_HEADER_RESET = 'X-RateLimit-Reset'

# ============================================================
# LOGGING
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ============================================================
# M-PESA SETTINGS
# ============================================================

MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY', default='')
MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET', default='')
MPESA_PASSKEY = config('MPESA_PASSKEY', default='')
MPESA_SHORTCODE = config('MPESA_SHORTCODE', default='174379')

if ENVIRONMENT == 'production':
    MPESA_BASE_URL = config('MPESA_BASE_URL', default='https://api.safaricom.co.ke')
else:
    MPESA_BASE_URL = config('MPESA_BASE_URL', default='https://sandbox.safaricom.co.ke')

MPESA_INITIATOR_NAME = config('MPESA_INITIATOR_NAME', default='')
MPESA_TIMEOUT_URL = config('MPESA_TIMEOUT_URL', default='')
MPESA_RESULT_URL = config('MPESA_RESULT_URL', default='')

# ============================================================
# DJANGO REDIS LOGGER
# ============================================================

DJANGO_REDIS_LOGGER = 'django_redis.loggers.CacheLogger'

# ============================================================
# SESSION CONFIGURATION (Optional)
# ============================================================

# SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = "default"

# ============================================================
# CELERY CONFIGURATION (Optional)
# ============================================================

# CELERY_BROKER_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/0')
# CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://127.0.0.1:6379/0')
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = TIME_ZONE

# ============================================================
# FORCE CSRF SETTINGS FOR RENDER
# ============================================================

# Force CSRF trusted origins for Render
if 'RENDER' in os.environ:
    CSRF_TRUSTED_ORIGINS = [
        'https://*.onrender.com',
        'https://sakafundi.onrender.com',
        'http://*.onrender.com',
        'http://sakafundi.onrender.com',
    ]
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    
    # Also ensure DEBUG is False on Render
    DEBUG = False
    
    print(f"✅ FORCED CSRF_TRUSTED_ORIGINS: {CSRF_TRUSTED_ORIGINS}", file=sys.stderr)