"""
Django settings for Handout project.
"""

from pathlib import Path
import os
from datetime import timedelta
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-crpt2fuahn@7jl361u%y8w9rm3m7)ruq0iawbu2iojj-5@w-jz'

DEBUG = True

ALLOWED_HOSTS = ["*"]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "corsheaders",              # ← CORS

    "rest_framework",
    "rest_framework_simplejwt",

    "accounts",
    "courses",
    "handouts",
    "payments",
    "notifications",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",   # ← must be FIRST
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",   # Vite default
    "http://localhost:3000",   # CRA default
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True
# ──────────────────────────────────────────────────────────────────────────────

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

import os 

WSGI_APPLICATION = 'Handout.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# Celery
CELERY_BROKER_URL     = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BEAT_SCHEDULE  = {
    "expire-pending-payments": {
        "task":     "payments.tasks.expire_pending_payments",
        "schedule": 60.0,
    },
}

# Hubtel SMS
HUBTEL_CLIENT_ID     = os.getenv("HUBTEL_CLIENT_ID")
HUBTEL_CLIENT_SECRET = os.getenv("HUBTEL_CLIENT_SECRET")
HUBTEL_SENDER_ID     = os.getenv("HUBTEL_SENDER_ID", "Handout")

# Email
DEFAULT_FROM_EMAIL  = os.getenv("DEFAULT_FROM_EMAIL", "noreply@handout.app")
EMAIL_BACKEND       = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST          = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

PAYSTACK_SECRET_KEY = config("PAYSTACK_SECRET_KEY")
REP_INVITE_CODE     = config("REP_INVITE_CODE")