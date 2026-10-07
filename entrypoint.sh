#!/bin/sh
set -e

echo "========================================"
echo "SaluTaxi - Starting backend"
echo "========================================"

echo "Environment variables:"
echo "PORT=${PORT:-8000}"
echo "DATABASE_URL=${DATABASE_URL:+[SET]}"
echo "DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY:+[SET]}"
echo "DJANGO_DEBUG=${DJANGO_DEBUG}"

echo "Waiting for DB to be ready..."
sleep 5

echo "Apply database migrations"
python manage.py migrate --noinput || echo "Migration failed (continuing anyway)"

echo "Collect static files"
python manage.py collectstatic --noinput || echo "Collectstatic failed (continuing anyway)"

echo "Starting Gunicorn on port ${PORT:-8000}"
exec gunicorn safetaxi_backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output
