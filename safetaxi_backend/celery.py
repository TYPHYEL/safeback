import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safetaxi_backend.settings')

app = Celery('safetaxi_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
app.conf.broker_url = redis_url
app.conf.result_backend = os.getenv('CELERY_RESULT_BACKEND', redis_url)

app.autodiscover_tasks([
    'users',
    'taxis',
    'trips',
    'sos',
    'ratings',
    'notifications',
    'ai',
])

app.conf.beat_schedule = {
    'recalculate_all_trust_scores_every_hour': {
        'task': 'ai.tasks.recalculate_all_trust_scores',
        'schedule': crontab(minute=0, hour='*'),
    },
    'cleanup_expired_alerts_every_30_min': {
        'task': 'sos.tasks.cleanup_expired_alerts',
        'schedule': crontab(minute='*/30'),
    },
    'cleanup_inactive_trips_every_8_hours': {
        'task': 'trips.tasks.cleanup_inactive_trips',
        'schedule': crontab(minute=0, hour='*/8'),
    },
}

app.conf.timezone = 'Africa/Douala'
