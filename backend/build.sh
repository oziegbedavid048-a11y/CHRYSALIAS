#!/usr/bin/env bash
# Chrysalias.com — Build Script (Render)
# Runs on every deploy. Installs deps, migrates DB, fixes data, creates superuser.
set -o errexit

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running database migrations..."
python manage.py migrate --run-syncdb

echo "==> Ensuring all users have a UserProfile..."
python manage.py ensure_profiles

# Auto-create Django admin superuser if env vars are set
# Set DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD in Render Dashboard
if [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "==> Creating superuser: $DJANGO_SUPERUSER_EMAIL"
    python manage.py createsuperuser --noinput 2>/dev/null || echo "Superuser already exists — skipping."
fi

echo "==> Build complete!"
