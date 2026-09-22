SAFETAXI backend (Django)

Quick start (development):

1. Copy `.env.example` to `.env` and adjust values.

2. Build and run with docker-compose:

```bash
docker-compose up --build
```

3. Create migrations and superuser (inside the container):

```bash
docker-compose exec web python manage.py migrate

docker-compose exec web python manage.py createsuperuser
```

Next steps:
- Create apps: `users`, `taxis`, `trips`, `sos`, `ai` and implement models + serializers + viewsets.
- Configure CI and tests.
