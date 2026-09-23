import os
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv
import dj_database_url

load_dotenv()

# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

if not SECRET_KEY:
    from django.core.management.utils import get_random_secret_key
    SECRET_KEY = get_random_secret_key()

DEBUG = os.getenv('DJANGO_DEBUG', '0') == '1'


# ============================================================
# ALLOWED HOSTS
# ============================================================

_allowed_hosts_env = os.getenv('DJANGO_ALLOWED_HOSTS', '')

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
]

if _allowed_hosts_env:
    for _host in _allowed_hosts_env.split(','):
        _host = _host.strip()

        if _host and _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [

    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # REST API
    'rest_framework',

    # CORS
    'corsheaders',
]


# ============================================================
# LOCAL APPS
# ============================================================

INSTALLED_APPS += [
    'users',
    'taxis',
    'trips',
    'sos',
    'api',
    'ocr',
    'verification',
    'notifications',
    'biometric',
    'documents',
    'ratings',
    'rotations',
    'ai',
]


# ============================================================
# JWT BLACKLIST
# ============================================================

INSTALLED_APPS += [
    'rest_framework_simplejwt.token_blacklist',
]


# ============================================================
# API DOCUMENTATION
# ============================================================

INSTALLED_APPS += [
    'drf_spectacular',
]


# ============================================================
# CHANNELS
# ============================================================

INSTALLED_APPS += [
    'channels',
]


# ============================================================
# CELERY
# ============================================================

try:
    import django_celery_results

    INSTALLED_APPS += [
        'django_celery_results',
    ]

except ImportError:
    pass


try:
    import django_celery_beat

    INSTALLED_APPS += [
        'django_celery_beat',
    ]

except ImportError:
    pass


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    # Middleware CORS personnalisé du projet
    'safetaxi_backend.middleware.CORSMiddleware',

    # django-cors-headers
    'corsheaders.middleware.CorsMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',

    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ============================================================
# URL CONFIGURATION
# ============================================================

ROOT_URLCONF = 'safetaxi_backend.urls'


# ============================================================
# TEMPLATES
# ============================================================

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


# ============================================================
# WSGI / ASGI
# ============================================================

WSGI_APPLICATION = 'safetaxi_backend.wsgi.application'

ASGI_APPLICATION = 'safetaxi_backend.asgi.application'


# ============================================================
# DATABASE
# ============================================================
#
# PRODUCTION :
# Supabase PostgreSQL avec DATABASE_URL
#
# LOCAL :
# SQLite si DATABASE_URL n'est pas définie
#
# ============================================================

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:

    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }

else:

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ============================================================
# REDIS
# ============================================================

REDIS_URL = os.getenv('REDIS_URL', '')

if REDIS_URL:

    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',

            'CONFIG': {
                'hosts': [
                    REDIS_URL,
                ],
            },
        },
    }

else:

    # Utilisé uniquement en développement local
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }


# ============================================================
# CACHE
# ============================================================

if REDIS_URL:

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }

else:

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'safetaxi-local-cache',
        }
    }


# ============================================================
# CELERY
# ============================================================

CELERY_BROKER_URL = os.getenv(
    'CELERY_BROKER_URL',
    REDIS_URL
)

CELERY_RESULT_BACKEND = os.getenv(
    'CELERY_RESULT_BACKEND',
    'django-db'
)

CELERY_ACCEPT_CONTENT = [
    'json',
]

CELERY_TASK_SERIALIZER = 'json'

CELERY_RESULT_SERIALIZER = 'json'

CELERY_TIMEZONE = 'Africa/Douala'

CELERY_ENABLE_UTC = True


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [

    {
        'NAME':
            'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.MinimumLengthValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.CommonPasswordValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = 'fr-cm'

TIME_ZONE = 'Africa/Douala'

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = '/static/'

STATIC_ROOT = os.getenv(
    'DJANGO_STATIC_ROOT',
    str(BASE_DIR / 'staticfiles')
)


# ============================================================
# MEDIA FILES
# ============================================================

MEDIA_URL = '/media/'

MEDIA_ROOT = os.path.join(
    BASE_DIR,
    'media'
)


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================
# CUSTOM USER MODEL
# ============================================================

AUTH_USER_MODEL = 'users.CustomUser'


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {

    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),

    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),

    'DEFAULT_SCHEMA_CLASS':
        'drf_spectacular.openapi.AutoSchema',

    'EXCEPTION_HANDLER':
        'safetaxi_backend.exceptions.custom_exception_handler',

}


# ============================================================
# API THROTTLING
# ============================================================

REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = (

    'rest_framework.throttling.AnonRateThrottle',

    'rest_framework.throttling.UserRateThrottle',

    'rest_framework.throttling.ScopedRateThrottle',

)


REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {

    'anon':
        os.getenv(
            'THROTTLE_ANON',
            '100/day'
        ),

    'user':
        os.getenv(
            'THROTTLE_USER',
            '1000/hour'
        ),

    'otp_send':
        os.getenv(
            'THROTTLE_OTP_SEND',
            '5/hour'
        ),

    'otp_verify':
        os.getenv(
            'THROTTLE_OTP_VERIFY',
            '20/hour'
        ),

}


# ============================================================
# JWT
# ============================================================

SIMPLE_JWT = {

    'ACCESS_TOKEN_LIFETIME':
        timedelta(
            seconds=int(
                os.getenv(
                    'SIMPLE_JWT_ACCESS_TOKEN_LIFETIME',
                    '3600'
                )
            )
        ),

    'REFRESH_TOKEN_LIFETIME':
        timedelta(
            seconds=int(
                os.getenv(
                    'SIMPLE_JWT_REFRESH_TOKEN_LIFETIME',
                    '86400'
                )
            )
        ),

    'ROTATE_REFRESH_TOKENS':
        True,

    'BLACKLIST_AFTER_ROTATION':
        True,

    'AUTH_HEADER_TYPES':
        ('Bearer',),

}


# ============================================================
# CORS
# ============================================================

def normalize_origin(origin: str) -> str:

    origin = origin.strip()

    if not origin:
        return ''

    if origin.startswith(
        ('http://', 'https://')
    ):
        return origin

    return f'http://{origin}'


CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = DEBUG


cors_origins = os.getenv(
    'DJANGO_CORS_ALLOWED_ORIGINS'
)

if cors_origins:

    CORS_ALLOW_ALL_ORIGINS = False

    CORS_ALLOWED_ORIGINS = [
        normalize_origin(origin)

        for origin in cors_origins.split(',')

        if normalize_origin(origin)
    ]


# ============================================================
# CSRF
# ============================================================

CSRF_TRUSTED_ORIGINS = [

    normalize_origin(origin)

    for origin in os.getenv(
        'DJANGO_CSRF_TRUSTED_ORIGINS',
        ''
    ).split(',')

    if normalize_origin(origin)

]


# ============================================================
# DRF SPECTACULAR
# ============================================================

SPECTACULAR_SETTINGS = {

    'TITLE':
        'SAFETAXI API',

    'DESCRIPTION':
        'API for SAFETAXI backend',

    'VERSION':
        '0.1.0',

}


# ============================================================
# AWS S3 / MINIO
# ============================================================

USE_S3 = os.getenv(
    'USE_S3',
    '0'
) == '1'


if USE_S3:

    DEFAULT_FILE_STORAGE = (
        'storages.backends.s3boto3.S3Boto3Storage'
    )

    AWS_ACCESS_KEY_ID = os.getenv(
        'AWS_ACCESS_KEY_ID'
    )

    AWS_SECRET_ACCESS_KEY = os.getenv(
        'AWS_SECRET_ACCESS_KEY'
    )

    AWS_STORAGE_BUCKET_NAME = os.getenv(
        'AWS_STORAGE_BUCKET_NAME'
    )

    AWS_S3_ENDPOINT_URL = os.getenv(
        'AWS_S3_ENDPOINT_URL'
    )

    AWS_S3_REGION_NAME = os.getenv(
        'AWS_S3_REGION_NAME'
    )

    AWS_S3_ADDRESSING_STYLE = os.getenv(
        'AWS_S3_ADDRESSING_STYLE',
        'path'
    )

    AWS_S3_FILE_OVERWRITE = False

    AWS_DEFAULT_ACL = None

    AWS_QUERYSTRING_AUTH = False


# ============================================================
# SECURITY SETTINGS - PRODUCTION
# ============================================================

if not DEBUG:

    SECURE_PROXY_SSL_HEADER = (
        'HTTP_X_FORWARDED_PROTO',
        'https'
    )

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

    SECURE_BROWSER_XSS_FILTER = True

    SECURE_CONTENT_TYPE_NOSNIFF = True

    X_FRAME_OPTIONS = 'DENY'

    SECURE_HSTS_SECONDS = int(
        os.getenv(
            'SECURE_HSTS_SECONDS',
            '0'
        )
    )

    SECURE_HSTS_INCLUDE_SUBDOMAINS = False

    SECURE_HSTS_PRELOAD = False