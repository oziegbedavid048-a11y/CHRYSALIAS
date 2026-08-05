#!/usr/bin/env bash
# Chrysalias.com — Render Build Script
# Runs on every deploy. Installs deps, migrates DB, seeds data, starts server.
set -o errexit

echo "==> [1/5] Installing Python dependencies..."
pip install -r requirements.txt

echo "==> [2/5] Collecting static files..."
python manage.py collectstatic --no-input

echo "==> [3/5] Running database migrations..."
python manage.py migrate --run-syncdb

echo "==> [4/5] Ensuring all users have a UserProfile..."
python manage.py ensure_profiles

# Auto-create/update Django admin superuser
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "==> [5/5] Creating/updating superuser: $DJANGO_SUPERUSER_EMAIL"
    python manage.py shell << 'PYEOF'
import os, django
from accounts.models import User, UserProfile

email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
pwd   = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
uname = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin_chrysalias')

if email and pwd:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': uname,
            'full_name': 'Chrysalias Admin',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
            'is_verified': True,
        }
    )
    # Always ensure superuser flags are set (in case user existed already)
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.is_verified = True
    user.set_password(pwd)
    user.save()
    UserProfile.objects.get_or_create(user=user)
    print(f"Superuser ready: {email} | created={created}")
else:
    print("Skipping superuser — DJANGO_SUPERUSER_EMAIL not set.")
PYEOF
else
    echo "==> [5/5] Skipping superuser — env vars not set."
fi

echo ""
echo "======================================"
echo "  Build complete — Chrysalias ready!"
echo "======================================"
