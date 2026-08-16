"""
Django settings for Handout project.

Every deployment-specific value is read from the environment (see .env.example).
Nothing secret is hard-coded here.
"""

from pathlib import Path
import os
from datetime import timedelta

import dj_database_url
from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = config("DEBUG", default=False, cast=bool)

SECRET_KEY = config("SECRET_KEY", default="")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is False.")
    SECRET_KEY = "django-insecure-development-key-do-not-use-in-production"

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,.fly.dev,.onrender.com",
    cast=Csv(),
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://handout-pay.vercel.app",
    cast=Csv(),
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "corsheaders",

    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_celery_beat",

    "accounts",
    "courses",
    "handouts",
    "payments",
    "notifications",
    "department",
    "school",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="https://handout-pay.vercel.app,http://localhost:5173",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = 'Handout.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Handout.wsgi.application'

DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = config("TIME_ZONE", default="Africa/Accra")
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Security ──────────────────────────────────────────────────────────────────
# Behind Fly/Render's TLS terminator, so trust their forwarded proto header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "login":    config("THROTTLE_LOGIN", default="10/min"),
        "register": config("THROTTLE_REGISTER", default="5/hour"),
        "payment":  config("THROTTLE_PAYMENT", default="10/hour"),
        "callback": config("THROTTLE_CALLBACK", default="120/min"),
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=config("ACCESS_TOKEN_MINUTES", default=60, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("REFRESH_TOKEN_DAYS", default=7, cast=int)),
    "ROTATE_REFRESH_TOKENS":  True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL     = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool)
CELERY_BEAT_SCHEDULE  = {
    "reconcile-pending-payments": {
        "task":     "payments.tasks.expire_pending_payments",
        "schedule": 300.0,
    },
}

# ── Course rep registration ───────────────────────────────────────────────────
# No default: rep signup fails closed when this is not configured.
REP_INVITE_CODE = config("REP_INVITE_CODE", default="")

# ── MTN MoMo ──────────────────────────────────────────────────────────────────
MOMO_CONSUMER_KEY     = config("MOMO_CONSUMER_KEY", default="")
MOMO_CONSUMER_SECRET  = config("MOMO_CONSUMER_SECRET", default="")
MOMO_SUBSCRIPTION_KEY = config("MOMO_SUBSCRIPTION_KEY", default="")
MOMO_BASE_URL         = config("MOMO_BASE_URL", default="https://api.mtn.com")
MOMO_CURRENCY         = config("MOMO_CURRENCY", default="GHS")
MOMO_CALLBACK_URL     = config("MOMO_CALLBACK_URL", default="")
# Shared secret echoed back by MTN in the X-Callback-Token header. When set the
# callback endpoint rejects requests that do not present it.
MOMO_CALLBACK_TOKEN   = config("MOMO_CALLBACK_TOKEN", default="")

# ── Hubtel SMS / email ────────────────────────────────────────────────────────
HUBTEL_CLIENT_ID     = config("HUBTEL_CLIENT_ID", default="")
HUBTEL_CLIENT_SECRET = config("HUBTEL_CLIENT_SECRET", default="")
HUBTEL_SENDER_ID     = config("HUBTEL_SENDER_ID", default="Handout")

EMAIL_BACKEND      = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@handout.local")

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": config("LOG_LEVEL", default="INFO"),
    },
}
