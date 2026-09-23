#!/bin/sh
set -e

echo "========================================"
echo "SaluTaxi - Starting backend"
echo "========================================"

echo "Waiting for DB to be ready..."
sleep 2

echo "Apply database migrations"
python manage.py migrate --noinput

echo "Collect static files"
python manage.py collectstatic --noinput || true

echo "Starting Celery Worker"
celery -A safetaxi_backend.celery worker --loglevel=INFO --pool=solo --concurrency=1 --without-gossip --without-mingle --without-heartbeat &

echo "Starting Celery Beat"
celery -A safetaxi_backend.celery beat --loglevel=INFO --pidfile=/tmp/celerybeat.pid &

echo "Starting Gunicorn"
exec gunicorn safetaxi_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}
