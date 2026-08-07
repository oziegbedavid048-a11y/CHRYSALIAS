"""
Chrysalias Accounts Admin
Full-featured admin for user management, KYC controls, and transaction oversight.
All display columns are wrapped in try/except to prevent 500 errors on Render.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import User, UserProfile


# ─── Custom Auth Forms ───────────────────────────────────────

class ChrysaliasUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class ChrysaliasUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'username', 'full_name')


# ─── UserProfile Inline ──────────────────────────────────────

class UserProfileInline(admin.StackedInline):
    model        = UserProfile
    can_delete   = False
    verbose_name = 'Extended Profile'
    extra        = 0
    max_num      = 1
    fieldsets    = (
        ('Personal Info', {
            'fields': ('bio', 'address', 'country'),
        }),
        ('Joint Account', {
            'fields': ('is_joint_account', 'joint_partner_name', 'joint_partner_email'),
            'description': 'Co-managed account settings.',
        }),
        ('KYC Documents', {
            'fields': ('id_document', 'selfie_photo'),
            'classes': ('collapse',),
        }),
        ('Admin Notes', {
            'fields': ('notes',),
        }),
    )
    readonly_fields = ()

    def get_queryset(self, request):
        return super().get_queryset(request)


# ─── UserAdmin ───────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form     = ChrysaliasUserChangeForm
    add_form = ChrysaliasUserCreationForm
    inlines  = [UserProfileInline]

    list_display        = ('edit_btn', 'email', 'display_name_col', 'phone', 'kyc_badge_col', 'verified_badge_col', 'joint_badge_col', 'is_active', 'is_staff', 'created_at')
    list_display_links  = ('email', 'display_name_col')
    list_filter         = ('kyc_status', 'is_verified', 'is_active', 'is_staff', 'created_at')
    search_fields       = ('email', 'full_name', 'username', 'phone')
    ordering            = ('-created_at',)
    readonly_fields     = ('created_at', 'updated_at', 'last_login', 'date_joined')
    list_per_page       = 25

    # Django BaseUserAdmin REQUIRES 'password' in fieldsets or it raises FieldError.
    fieldsets = (
        ('Account Identity', {
            'fields': ('email', 'username', 'full_name', 'phone'),
        }),
        ('Password', {
            'fields': ('password',),
            'classes': ('collapse',),
        }),
        ('KYC & Verification', {
            'fields': ('kyc_status', 'is_verified'),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': ('email', 'username', 'full_name', 'password1', 'password2'),
        }),
    )

    actions = [
        'approve_kyc_level1',
        'approve_kyc_level2',
        'reject_kyc',
        'activate_accounts',
        'deactivate_accounts',
    ]

    def get_queryset(self, request):
        """
        Use select_related to avoid N+1 queries and prevent
        RelatedObjectDoesNotExist errors when accessing user.profile.
        """
        qs = super().get_queryset(request)
        return qs.select_related('profile')

    def save_model(self, request, obj, form, change):
        """Auto-ensure a UserProfile exists whenever a user is saved from admin."""
        super().save_model(request, obj, form, change)
        UserProfile.objects.get_or_create(user=obj)

    def get_object(self, request, object_id, from_field=None):
        """Ensure UserProfile exists before admin renders the inline."""
        obj = super().get_object(request, object_id, from_field)
        if obj is not None:
            UserProfile.objects.get_or_create(user=obj)
        return obj

    # ── Display Columns ──────────────────────────────────────

    @admin.display(description='Actions')
    def edit_btn(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.pk])
        return format_html(
            '<a href="{}" style="background:#002b49;color:#ffffff;padding:5px 12px;border-radius:6px;'
            'font-weight:700;font-size:0.78rem;text-decoration:none;display:inline-flex;align-items:center;gap:4px;">'
            '✏️ Edit User</a>',
            url
        )

    @admin.display(description='Name', ordering='full_name')
    def display_name_col(self, obj):
        try:
            initials = obj.initials or 'U'
            name     = obj.display_name or obj.email
        except Exception:
            initials, name = 'U', obj.email
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="width:32px;height:32px;border-radius:50%;'
            'background:linear-gradient(135deg,#002b49,#3cb95d);'
            'color:#fff;display:flex;align-items:center;justify-content:center;'
            'font-weight:700;font-size:0.75rem;flex-shrink:0;">{}</div>'
            '<strong>{}</strong></div>',
            initials, name
        )

    @admin.display(description='KYC Status')
    def kyc_badge_col(self, obj):
        try:
            status = obj.kyc_status or 'pending'
        except Exception:
            status = 'pending'
        colours = {
            'pending':  ('#fffbeb', '#b45309', 'Pending'),
            'level_1':  ('#eff6ff', '#1d4ed8', 'Level 1'),
            'level_2':  ('#f0fdf4', '#166534', 'Level 2'),
            'rejected': ('#fef2f2', '#991b1b', 'Rejected'),
        }
        bg, c, label = colours.get(status, ('#f8fafc', '#475569', status))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;'
            'font-size:0.78rem;font-weight:700;">{}</span>',
            bg, c, label
        )

    @admin.display(description='Verified', ordering='is_verified')
    def verified_badge_col(self, obj):
        try:
            verified = obj.is_verified
        except Exception:
            verified = False
        if verified:
            return format_html(
                '<span style="background:#f0fdf4;color:#166534;padding:3px 10px;'
                'border-radius:12px;font-size:0.78rem;font-weight:700;">Verified</span>'
            )
        return format_html(
            '<span style="background:#fef2f2;color:#991b1b;padding:3px 10px;'
            'border-radius:12px;font-size:0.78rem;font-weight:700;">Unverified</span>'
        )

    @admin.display(description='Account Type')
    def joint_badge_col(self, obj):
        try:
            profile = getattr(obj, 'profile', None)
            is_joint = profile.is_joint_account if profile else False
        except Exception:
            is_joint = False
        if is_joint:
            return format_html(
                '<span style="background:#eff6ff;color:#1d4ed8;padding:3px 10px;'
                'border-radius:12px;font-size:0.78rem;font-weight:700;">Joint</span>'
            )
        return format_html(
            '<span style="background:#f8fafc;color:#64748b;padding:3px 10px;'
            'border-radius:12px;font-size:0.78rem;font-weight:700;">Personal</span>'
        )

    # ── Admin Actions ────────────────────────────────────────

    @admin.action(description='Approve KYC — Level 1 (Email Verified)')
    def approve_kyc_level1(self, request, queryset):
        updated = queryset.update(kyc_status='level_1', is_verified=True)
        self.message_user(request, f'{updated} user(s) approved for KYC Level 1.')

    @admin.action(description='Approve KYC — Level 2 (Full KYC Verified)')
    def approve_kyc_level2(self, request, queryset):
        updated = queryset.update(kyc_status='level_2', is_verified=True)
        self.message_user(request, f'{updated} user(s) approved for KYC Level 2.')

    @admin.action(description='Reject KYC Verification')
    def reject_kyc(self, request, queryset):
        updated = queryset.update(kyc_status='rejected', is_verified=False)
        self.message_user(request, f'{updated} user(s) KYC rejected.')

    @admin.action(description='Activate selected accounts')
    def activate_accounts(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, 'Selected accounts activated.')

    @admin.action(description='Deactivate selected accounts')
    def deactivate_accounts(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, 'Selected accounts deactivated.')


# ─── UserProfile Admin ───────────────────────────────────────

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('edit_btn', 'user', 'country', 'is_joint_account', 'joint_partner_email', 'created_at')
    list_display_links = ('user',)
    list_filter   = ('is_joint_account', 'country', 'created_at')
    search_fields = ('user__email', 'user__full_name', 'joint_partner_email', 'country')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at',)

    @admin.display(description='Actions')
    def edit_btn(self, obj):
        url = reverse('admin:accounts_userprofile_change', args=[obj.pk])
        return format_html(
            '<a href="{}" style="background:#0284c7;color:#ffffff;padding:4px 10px;border-radius:6px;'
            'font-weight:700;font-size:0.75rem;text-decoration:none;display:inline-block;">✏️ Edit Profile</a>',
            url
        )
