"""
Chrysalias.com Django Project Settings
"""
import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Core ──────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='chrysalias-django-dev-secret-key-change-in-production-2026')

DEBUG = config('DEBUG', default=False, cast=bool)

# Accept all hosts by default — Render assigns a dynamic subdomain (.onrender.com)
# Override via ALLOWED_HOSTS env var in Render dashboard if you want to restrict.
_allowed_raw = config('ALLOWED_HOSTS', default='*')
if _allowed_raw.strip() == '*':
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_raw.split(',') if h.strip()]

# ─── Applications ───────────────────────────────────────────
INSTALLED_APPS = [
    # Django Built-ins
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third Party
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    # Chrysalias Apps
    'accounts',
    'transactions',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'chrysalias.urls'

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

WSGI_APPLICATION = 'chrysalias.wsgi.application'

# ─── Database (PostgreSQL via LayerBase) ────────────────────
import dj_database_url

# DATABASE_URL must include ?sslmode=require for LayerBase/external Postgres
DEFAULT_DB_URL = 'postgresql://postgres:SFw8Jic6bAdLMvr4eGcpXngS@chrysalias-wild-trail.cloud.layerbase.dev/chrysalias?sslmode=require'
DATABASE_URL = config('DATABASE_URL', default=DEFAULT_DB_URL)

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
    )
}

# ─── Password Validation ────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internationalisation ───────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ─── Static & Media ─────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Custom User Model ──────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'

# ─── Django REST Framework ──────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# ─── CORS & CSRF ────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    'https://chrysalias.com',
    'https://www.chrysalias.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:3000',
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.github\.io$",
    r"^https://.*\.onrender\.com$",
    r"^https://.*\.chrysalias\.com$",
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://*.onrender.com',
    'https://*.github.io',
    'https://chrysalias.com',
    'https://www.chrysalias.com',
]

# ─── Session Settings ───────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Production HTTPS — Render terminates SSL at the load balancer.
# SECURE_SSL_REDIRECT must be False here because Render's proxy already
# enforces HTTPS. Enabling it causes redirect loops → 400 Bad Request.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False  # Render handles this at the load balancer
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0  # 1 year HSTS once stable
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = False  # Set True only after confirming HSTS works

# ─── Email / ZeptoMail SMTP ─────────────────────────────────
# All values read from .env (or Render environment variables)
EMAIL_BACKEND       = config('EMAIL_BACKEND',       default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST          = config('EMAIL_HOST',          default='smtp.zeptomail.com')
EMAIL_PORT          = config('EMAIL_PORT',          default=587, cast=int)
EMAIL_USE_TLS       = config('EMAIL_USE_TLS',       default=True,  cast=bool)
EMAIL_USE_SSL       = config('EMAIL_USE_SSL',       default=False, cast=bool)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='emailapikey')
EMAIL_HOST_PASSWORD = config(
    'EMAIL_HOST_PASSWORD',
    default='wSsVR61y/RWkW/p4yTOpdrhuyAtQB16kEkwp3lP36n+tH6iU8Mc6xRfJDFD0H/gWQDI8EDQbpe8hm0sC0WULhth7mA4ACCiF9mqRe1U4J3x17qnvhDzIX2VfkBSJLoIJzg1imGNnEcsr+g=='
)
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL',  default='Chrysalias Support <info@chrysalias.com>')
EMAIL_TIMEOUT       = 15

# ─── Static File Serving (WhiteNoise) ───────────────────────
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# ─── Logging ────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
