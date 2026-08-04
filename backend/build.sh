#!/usr/bin/env bash
# Chrysalias.com — Build Script (Render / LayerBase)
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate --run-syncdb

# Create superuser if DJANGO_SUPERUSER_EMAIL is set (set these in Render env vars)
# DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD, DJANGO_SUPERUSER_USERNAME
if [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Creating superuser: $DJANGO_SUPERUSER_EMAIL"
    python manage.py createsuperuser --noinput || echo "Superuser already exists — skipping."
fi
