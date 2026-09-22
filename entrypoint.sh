#!/bin/sh
set -e

echo "Waiting for DB to be ready..."
sleep 2

echo "Apply database migrations"
python manage.py migrate --noinput

echo "Collect static files"
python manage.py collectstatic --noinput || true

echo "Starting gunicorn"
exec gunicorn safetaxi_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}
