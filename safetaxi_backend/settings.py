import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# In production, DJANGO_SECRET_KEY MUST be set as an env variable.
# In development, a random key is generated if not provided.
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    from django.core.management.utils import get_random_secret_key
    SECRET_KEY = get_random_secret_key()
DEBUG = os.getenv('DJANGO_DEBUG', '0') == '1'

_allowed_hosts_env = os.getenv('DJANGO_ALLOWED_HOSTS', '')
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
if _allowed_hosts_env:
    for _host in _allowed_hosts_env.split(','):
        _host = _host.strip()
        if _host and _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
]

# Local apps
INSTALLED_APPS += [
    'users',
    'taxis',
    'trips',
    'sos',
    'api',
    'ocr',
    'verification',
]
INSTALLED_APPS += [
    'rest_framework_simplejwt.token_blacklist',
]
# API docs
INSTALLED_APPS += [
    'drf_spectacular',
]

# Channels for realtime
INSTALLED_APPS += [
    'channels',
]

# notifications
INSTALLED_APPS += [
    'notifications',
    'biometric',
]

# Local third-party apps already created
INSTALLED_APPS += [
    'documents',
    'ratings',
    'rotations',
    'ai',
]

# Celery
try:
    import django_celery_results
    INSTALLED_APPS += ['django_celery_results']
except ImportError:
    pass

try:
    import django_celery_beat
    if 'django_celery_beat' not in INSTALLED_APPS:
        INSTALLED_APPS += ['django_celery_beat']
except ImportError:
    pass

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'safetaxi_backend.middleware.CORSMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS & CSRF settings are configured below (near end of file) using env vars.
# In development, CORS_ALLOW_ALL_ORIGINS defaults to True.
# In production, set DJANGO_CORS_ALLOWED_ORIGINS and DJANGO_CSRF_TRUSTED_ORIGINS.

ROOT_URLCONF = 'safetaxi_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'safetaxi_backend.wsgi.application'

_postgres_host = os.getenv('POSTGRES_HOST')
_postgres_port = os.getenv('POSTGRES_PORT')
_postgres_db = os.getenv('POSTGRES_DB')
_postgres_user = os.getenv('POSTGRES_USER')
_postgres_password = os.getenv('POSTGRES_PASSWORD')

if _postgres_host and _postgres_db and _postgres_user and _postgres_password:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _postgres_db,
            'USER': _postgres_user,
            'PASSWORD': _postgres_password,
            'HOST': _postgres_host,
            'PORT': _postgres_port or '5432',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

REDIS_URL = os.getenv('REDIS_URL', '')
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

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

LANGUAGE_CODE = 'fr-cm'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.getenv('DJANGO_STATIC_ROOT', '/var/www/static')

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'users.CustomUser'

# DRF + JWT basic setup
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'safetaxi_backend.exceptions.custom_exception_handler',
}

# Throttling / Rate limiting
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = (
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
    'rest_framework.throttling.ScopedRateThrottle',
)
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': os.getenv('THROTTLE_ANON', '100/day'),
    'user': os.getenv('THROTTLE_USER', '1000/hour'),
    'otp_send': os.getenv('THROTTLE_OTP_SEND', '5/hour'),
    'otp_verify': os.getenv('THROTTLE_OTP_VERIFY', '20/hour'),
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(seconds=int(os.getenv('SIMPLE_JWT_ACCESS_TOKEN_LIFETIME', '3600'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(seconds=int(os.getenv('SIMPLE_JWT_REFRESH_TOKEN_LIFETIME', '86400'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

def normalize_origin(origin: str) -> str:
    origin = origin.strip()
    if not origin:
        return ''
    if origin.startswith(('http://', 'https://')):
        return origin
    return f'http://{origin}'

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG
cors_origins = os.getenv('DJANGO_CORS_ALLOWED_ORIGINS')
if cors_origins:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [normalize_origin(o) for o in cors_origins.split(',') if normalize_origin(o)]

CSRF_TRUSTED_ORIGINS = [normalize_origin(o) for o in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if normalize_origin(o)]

# drf-spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'SAFETAXI API',
    'DESCRIPTION': 'API for SAFETAXI backend',
    'VERSION': '0.1.0',
}

# AWS S3 / MinIO storage settings (optional)
USE_S3 = os.getenv('USE_S3', '0') == '1'
if USE_S3:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME')
    AWS_S3_ADDRESSING_STYLE = os.getenv('AWS_S3_ADDRESSING_STYLE', 'path')
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
