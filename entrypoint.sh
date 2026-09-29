#!/bin/sh
set -e

echo "========================================"
echo "SaluTaxi - Starting backend"
echo "========================================"

echo "Waiting for DB to be ready..."
sleep 5

echo "Apply database migrations"
python manage.py migrate --noinput

echo "Collect static files"
python manage.py collectstatic --noinput || true

echo "Starting Gunicorn on port ${PORT:-8000}"
exec gunicorn safetaxi_backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
