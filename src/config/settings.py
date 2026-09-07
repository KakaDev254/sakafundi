# config/settings.py

import os
import sys
from pathlib import Path
import cloudinary
import cloudinary.uploader
import cloudinary.api
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
# CLOUDINARY CONFIGURATION
# ============================================================

# Configure Cloudinary
cloudinary.config(
    cloud_name=config('CLOUDINARY_CLOUD_NAME', default=''),
    api_key=config('CLOUDINARY_API_KEY', default=''),
    api_secret=config('CLOUDINARY_API_SECRET', default='')
)

# Cloudinary Storage Settings
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
    'STATIC_IMAGES_EXTENSIONS': ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'],
    'STATIC_VIDEOS_EXTENSIONS': ['mp4', 'webm', 'avi'],
}

if config('CLOUDINARY_CLOUD_NAME', default=''):
    print(f"✅ CLOUDINARY: Configured with cloud name: {config('CLOUDINARY_CLOUD_NAME')}", file=sys.stderr)
else:
    print(f"⚠️ CLOUDINARY: Not configured (missing cloud name)", file=sys.stderr)

# ============================================================
# BASE SECURITY SETTINGS
# ============================================================

SECRET_KEY = config('SECRET_KEY')

if ENVIRONMENT == 'production' or 'RENDER' in os.environ:
    DEBUG = False
    ALLOWED_HOSTS = [
        '.onrender.com',
        'sakafundi.onrender.com',
        '.sakafundi.com',
        'sakafundi.com',
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
    ]
    
    CSRF_TRUSTED_ORIGINS = [
        'https://*.onrender.com',
        'https://sakafundi.onrender.com',
        'https://*.sakafundi.com',
        'https://sakafundi.com',
        'http://*.onrender.com',
        'http://sakafundi.onrender.com',
    ]
    
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    USE_X_FORWARDED_PORT = True
    
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
else:
    DEBUG = True
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
    CSRF_TRUSTED_ORIGINS = ['http://localhost:8000']
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_PROXY_SSL_HEADER = None
    USE_X_FORWARDED_HOST = False
    USE_X_FORWARDED_PORT = False

print(f"🔒 CSRF_TRUSTED_ORIGINS: {CSRF_TRUSTED_ORIGINS}", file=sys.stderr)
print(f"🔒 ALLOWED_HOSTS FINAL: {ALLOWED_HOSTS}", file=sys.stderr)

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
    'django_redis',
    'widget_tweaks',
    'import_export',
    'cloudinary',
    'cloudinary_storage',
    
    # Allauth - Google only
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    
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
# MIDDLEWARE - ADDED AUTO-LOGOUT MIDDLEWARE
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
    # Auto-logout middleware
    'accounts.middleware.AutoLogoutMiddleware',
    'accounts.middleware.UserActivityMiddleware',
    'accounts.middleware.SessionExpiryMiddleware',
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
                'accounts.context_processors.user_settings',
            ],
        },
    },
]

# ============================================================
# DATABASE
# ============================================================

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

SITE_ID = 2

# ============================================================
# ALLAUTH SETTINGS - UPDATED FOR EMAIL VERIFICATION
# ============================================================

ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = 'accounts:login'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = 'accounts:profile'
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = True

ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/300',
    'signup': '5/3600',
    'password_reset': '3/3600',
    'email_confirmation': '3/3600',
}

# ============================================================
# SOCIAL ACCOUNT SETTINGS - GOOGLE ONLY (ADD THIS SECTION)
# ============================================================

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

SOCIALACCOUNT_EMAIL_VERIFICATION = 'optional'
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True

# ============================================================
# SESSION SETTINGS - FOR AUTO-LOGOUT
# ============================================================

SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

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
# STATIC & MEDIA FILES WITH CLOUDINARY
# ============================================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

if ENVIRONMENT == 'production' or 'RENDER' in os.environ:
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    MEDIA_URL = f'https://res.cloudinary.com/{config("CLOUDINARY_CLOUD_NAME", default="")}/'
    print(f"✅ Using Cloudinary for media storage", file=sys.stderr)
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
    print(f"🔧 Using local storage for media", file=sys.stderr)

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
# EMAIL - UPDATED FOR ZOHO MAIL
# ============================================================

if ENVIRONMENT == 'production' or 'RENDER' in os.environ:
    EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.zoho.com')
    EMAIL_PORT = config('EMAIL_PORT', default=465, cast=int)
    EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=True, cast=bool)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='info@sakafundi.com')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='info@sakafundi.com')
    EMAIL_TIMEOUT = 30
    
    print(f"📧 EMAIL: Configured with Zoho Mail ({EMAIL_HOST}) for production", file=sys.stderr)
    print(f"📧 EMAIL: Sending from {DEFAULT_FROM_EMAIL}", file=sys.stderr)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'noreply@sakafundi.com'
    print(f"📧 EMAIL: Using console backend for development", file=sys.stderr)

# ============================================================
# PLATFORM SETTINGS
# ============================================================

PLATFORM_FEE_PERCENTAGE = config('PLATFORM_FEE_PERCENTAGE', default=10, cast=int)
DEPOSIT_DEFAULT_PERCENTAGE = 30
CURRENCY = 'KES'
CURRENCY_SYMBOL = 'KSh'

# ============================================================
# SITE SETTINGS
# ============================================================

SITE_NAME = 'SakaFundi'
SITE_EMAIL = 'info@sakafundi.com'
SITE_PHONE = '+254 700 123456'
SITE_ADDRESS = 'Nairobi, Kenya'

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
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
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
        'accounts': {
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
# FORCE RENDER SETTINGS (OVERRIDE EVERYTHING)
# ============================================================

if 'RENDER' in os.environ:
    ALLOWED_HOSTS = [
        '.onrender.com',
        'sakafundi.onrender.com',
        '.sakafundi.com',
        'sakafundi.com',
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
    ]
    
    CSRF_TRUSTED_ORIGINS = [
        'https://*.onrender.com',
        'https://sakafundi.onrender.com',
        'https://*.sakafundi.com',
        'https://sakafundi.com',
        'http://*.onrender.com',
        'http://sakafundi.onrender.com',
    ]
    
    DEBUG = False
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Force email settings
    EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.zoho.com')
    EMAIL_PORT = config('EMAIL_PORT', default=465, cast=int)
    EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=True, cast=bool)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='info@sakafundi.com')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='info@sakafundi.com')
    EMAIL_TIMEOUT = 30
    
    # Force session settings
    SESSION_COOKIE_AGE = 3600
    SESSION_SAVE_EVERY_REQUEST = True
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    
    print(f"🚨 RENDER MODE ACTIVATED", file=sys.stderr)
    print(f"🔒 ALLOWED_HOSTS: {ALLOWED_HOSTS}", file=sys.stderr)
    print(f"🔒 CSRF_TRUSTED_ORIGINS: {CSRF_TRUSTED_ORIGINS}", file=sys.stderr)
    print(f"🔒 DEBUG: {DEBUG}", file=sys.stderr)
    print(f"📧 EMAIL: Using {EMAIL_HOST} from {DEFAULT_FROM_EMAIL}", file=sys.stderr)
    print(f"⏰ SESSION_TIMEOUT: {SESSION_COOKIE_AGE} seconds", file=sys.stderr)

# ============================================================
# CLOUDINARY URL FOR TEMPLATES
# ============================================================

if config('CLOUDINARY_CLOUD_NAME', default=''):
    CLOUDINARY_URL = f'https://res.cloudinary.com/{config("CLOUDINARY_CLOUD_NAME")}/'
else:
    CLOUDINARY_URL = ''