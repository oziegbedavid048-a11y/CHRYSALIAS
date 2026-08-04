"""
Management command: ensure_profiles
Creates missing UserProfile records for all existing users.
Run automatically on every deploy via build.sh.
"""
from django.core.management.base import BaseCommand
from accounts.models import User, UserProfile


class Command(BaseCommand):
    help = 'Ensure every User has a UserProfile — creates missing ones.'

    def handle(self, *args, **options):
        users = User.objects.all()
        created = 0
        for user in users:
            _, was_created = UserProfile.objects.get_or_create(user=user)
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  Created profile for {user.email}'))

        if created == 0:
            self.stdout.write(self.style.SUCCESS('All UserProfiles already exist — nothing to do.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Done. Created {created} missing UserProfile(s).'))
