"""
Chrysalias Accounts Models
Custom User with KYC, phone, and escrow-specific fields.
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended User model for Chrysalias.com"""

    KYC_PENDING  = 'pending'
    KYC_LEVEL_1  = 'level_1'
    KYC_LEVEL_2  = 'level_2'
    KYC_REJECTED = 'rejected'

    KYC_CHOICES = [
        (KYC_PENDING,  'Pending Verification'),
        (KYC_LEVEL_1,  'Level 1 Verified (Email)'),
        (KYC_LEVEL_2,  'Level 2 Verified (Full KYC)'),
        (KYC_REJECTED, 'Verification Rejected'),
    ]

    # Use email as primary identifier
    email       = models.EmailField(unique=True)
    full_name   = models.CharField(max_length=200, blank=True)
    phone       = models.CharField(max_length=30, blank=True)
    kyc_status  = models.CharField(max_length=20, choices=KYC_CHOICES, default=KYC_PENDING)
    is_verified = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name       = 'User'
        verbose_name_plural = 'Users'
        ordering           = ['-created_at']

    def __str__(self):
        return f'{self.full_name or self.email} ({self.email})'

    @property
    def initials(self):
        parts = (self.full_name or self.email).strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return parts[0][:2].upper() if parts else 'U'

    @property
    def display_name(self):
        return self.full_name or self.username or self.email.split('@')[0]

    def get_kyc_badge(self):
        badges = {
            self.KYC_PENDING:  ('⏳', '#f59e0b'),
            self.KYC_LEVEL_1:  ('✓',  '#3b82f6'),
            self.KYC_LEVEL_2:  ('✓✓', '#22c55e'),
            self.KYC_REJECTED: ('✗',  '#ef4444'),
        }
        return badges.get(self.kyc_status, ('?', '#94a3b8'))


class UserProfile(models.Model):
    """Extended profile for Chrysalias users"""
    user                 = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio                  = models.TextField(blank=True)
    address              = models.TextField(blank=True)
    country              = models.CharField(max_length=100, blank=True)
    id_document          = models.FileField(upload_to='kyc_docs/', blank=True, null=True)
    selfie_photo         = models.ImageField(upload_to='kyc_selfies/', blank=True, null=True)
    is_joint_account     = models.BooleanField(default=False)
    joint_partner_name   = models.CharField(max_length=200, blank=True)
    joint_partner_email  = models.EmailField(blank=True)
    notes                = models.TextField(blank=True, help_text='Internal admin notes')
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name       = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'Profile: {self.user.display_name} (Joint: {self.is_joint_account})'


# ─── Signals ────────────────────────────────────────────────
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Guarantees every User in PostgreSQL automatically gets a UserProfile"""
    if created:
        UserProfile.objects.get_or_create(user=instance)

