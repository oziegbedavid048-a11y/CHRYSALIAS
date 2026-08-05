#!/usr/bin/env bash
# Chrysalias.com — Build Script (Render)
# Runs on every deploy. Installs deps, migrates DB, creates superuser.
set -o errexit

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running database migrations..."
python manage.py migrate --run-syncdb

echo "==> Ensuring all users have a UserProfile..."
python manage.py ensure_profiles

# Auto-create/update Django admin superuser if env vars are set
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "==> Creating/updating superuser: $DJANGO_SUPERUSER_EMAIL"
    python manage.py shell -c "
from accounts.models import User, UserProfile
email = '$DJANGO_SUPERUSER_EMAIL'
pwd   = '$DJANGO_SUPERUSER_PASSWORD'
user, created = User.objects.get_or_create(email=email, defaults={
    'username': '${DJANGO_SUPERUSER_USERNAME:-admin_chrysalias}',
    'full_name': 'Chrysalias Admin',
    'is_staff': True,
    'is_superuser': True,
    'is_active': True,
    'is_verified': True,
})
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.is_verified = True
user.set_password(pwd)
user.save()
UserProfile.objects.get_or_create(user=user)
print('Superuser ready:', email, '| created:', created)
"
fi

echo "==> Build complete!"
