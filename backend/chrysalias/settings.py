"""
Chrysalias.com Django Project Settings
"""
import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Core ──────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='chrysalias-django-dev-secret-key-change-in-production-2026')

DEBUG = config('DEBUG', default=True, cast=bool)

# Accept all hosts — Render assigns a dynamic subdomain (.onrender.com)
_allowed_raw = config('ALLOWED_HOSTS', default='*')
if '*' in _allowed_raw:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_raw.split(',') if h.strip()]
    for _dh in ['127.0.0.1', 'localhost', '.onrender.com']:
        if _dh not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_dh)

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

# ─── Database ────────────────────────────────────────────────
import dj_database_url

DEFAULT_DB_URL = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
DATABASE_URL = config('DATABASE_URL', default=DEFAULT_DB_URL)

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600 if not DATABASE_URL.startswith('sqlite') else 0,
        ssl_require=DATABASE_URL.startswith('postgres') and not DEBUG,
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

# ─── CORS ───────────────────────────────────────────────────
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

from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-csrftoken',
    'x-requested-with',
]

# ─── CSRF ───────────────────────────────────────────────────
# Render uses HTTPS — Django must trust the Render domain for CSRF.
# Use wildcards to cover the auto-assigned .onrender.com subdomain.
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:3000',
    'https://*.onrender.com',
    'https://*.github.io',
    'https://chrysalias.com',
    'https://www.chrysalias.com',
    'https://*.chrysalias.com',
]

# ─── Session / Security Cookies ─────────────────────────────
# On Render (HTTPS), cookies must be Secure.
# On localhost (HTTP), Secure=False so the browser sends them.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Use environment variable to control cookie security
# Default to False (safe for local dev). Set to True on Render via env var.
_use_secure_cookies = config('USE_SECURE_COOKIES', default=not DEBUG, cast=bool)
SESSION_COOKIE_SECURE = _use_secure_cookies
CSRF_COOKIE_SECURE = _use_secure_cookies

# ─── HTTPS / SSL ────────────────────────────────────────────
# Render terminates SSL at the load balancer — never redirect here.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False   # Render handles this upstream
SECURE_HSTS_SECONDS = 0       # Disable HSTS until confirmed working
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# ─── Email / ZeptoMail SMTP ─────────────────────────────────
EMAIL_BACKEND       = config('EMAIL_BACKEND',       default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST          = config('EMAIL_HOST',          default='smtp.zeptomail.com')
EMAIL_PORT          = config('EMAIL_PORT',          default=465, cast=int)
EMAIL_USE_TLS       = config('EMAIL_USE_TLS',       default=False, cast=bool)
EMAIL_USE_SSL       = config('EMAIL_USE_SSL',       default=True,  cast=bool)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='emailapikey')
EMAIL_HOST_PASSWORD = config(
    'EMAIL_HOST_PASSWORD',
    default='wSsVR61y/RWkW/p4yTOpdrhuyAtQB16kEkwp3lP36n+tH6iU8Mc6xRfJDFD0H/gWQDI8EDQbpe8hm0sC0WULhth7mA4ACCiF9mqRe1U4J3x17qnvhDzIX2VfkBSJLoIJzg1imGNnEcsr+g=='
)
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL',  default='Chrysalias Support <info@chrysalias.com>')
EMAIL_TIMEOUT       = 15

# ─── Frontend URL (used in verification emails) ─────────────
FRONTEND_BASE_URL = config('FRONTEND_BASE_URL', default='http://localhost:8080')

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

# ── File Uploads (Payment Receipts) ──────────────────────────
MEDIA_URL  = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
