"""
Chrysalias Accounts Admin
Full-featured admin for user management with KYC controls.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import User, UserProfile


class ChrysaliasUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class ChrysaliasUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'username', 'full_name')


class UserProfileInline(admin.StackedInline):
    model        = UserProfile
    can_delete   = False
    verbose_name = 'Extended Profile'
    extra        = 1
    max_num      = 1
    fieldsets    = (
        ('Personal Info', {
            'fields': ('bio', 'address', 'country'),
        }),
        ('Joint Account', {
            'fields': ('is_joint_account', 'joint_partner_name', 'joint_partner_email'),
            'description': 'Co-managed account settings — set when user registers as a Joint Account holder.',
        }),
        ('KYC Documents', {
            'fields': ('id_document', 'selfie_photo'),
            'classes': ('collapse',),
        }),
        ('Admin Notes', {
            'fields': ('notes',),
        }),
    )

    def get_queryset(self, request):
        """Ensure profile always exists so inline never errors."""
        qs = super().get_queryset(request)
        return qs

    def save_new_objects(self, form, change):
        """Auto-create profile if inline is empty / missing."""
        return super().save_new_objects(form, change)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form     = ChrysaliasUserChangeForm
    add_form = ChrysaliasUserCreationForm
    inlines  = [UserProfileInline]

    list_display  = ('email', 'display_name_col', 'kyc_badge_col', 'verified_badge_col', 'joint_badge_col', 'is_active', 'transaction_count_col', 'created_at')
    list_filter   = ('kyc_status', 'is_verified', 'is_active', 'is_staff', 'profile__is_joint_account', 'created_at')
    search_fields = ('email', 'full_name', 'username', 'phone', 'profile__joint_partner_email')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'initials_col', 'last_login', 'date_joined')
    list_per_page = 25

    # IMPORTANT: Django's BaseUserAdmin requires 'password' to be present in fieldsets.
    # Without it, the admin change form throws a 500 error when opening a user record.
    fieldsets = (
        ('Account Identity', {
            'fields': ('email', 'username', 'full_name', 'phone'),
            'description': 'Core user account information for Chrysalias.com',
        }),
        ('Password', {
            'fields': ('password',),
            'classes': ('collapse',),
        }),
        ('KYC & Verification', {
            'fields': ('kyc_status', 'is_verified'),
            'classes': ('wide',),
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

    actions = ['approve_kyc_level1', 'approve_kyc_level2', 'reject_kyc', 'activate_accounts', 'deactivate_accounts']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Always ensure a UserProfile exists — prevents inline 500 errors
        UserProfile.objects.get_or_create(user=obj)

    def get_object(self, request, object_id, from_field=None):
        """Ensure UserProfile exists before admin tries to render the inline."""
        obj = super().get_object(request, object_id, from_field)
        if obj:
            UserProfile.objects.get_or_create(user=obj)
        return obj

    @admin.display(description='Name', ordering='full_name')
    def display_name_col(self, obj):
        try:
            initials = obj.initials or 'U'
            name = obj.display_name or obj.email
        except Exception:
            initials, name = 'U', obj.email
        return format_html(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#002b49,#3cb95d);'
            'color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.75rem;">{}</div>'
            '<strong>{}</strong></div>',
            initials, name
        )

    @admin.display(description='KYC Status')
    def kyc_badge_col(self, obj):
        status = obj.kyc_status or 'pending'
        colours = {
            'pending':  ('#f59e0b', '#fffbeb', 'Pending'),
            'level_1':  ('#3b82f6', '#eff6ff', 'Level 1'),
            'level_2':  ('#22c55e', '#f0fdf4', 'Level 2'),
            'rejected': ('#ef4444', '#fef2f2', 'Rejected'),
        }
        c, bg, label = colours.get(status, ('#94a3b8', '#f8fafc', status))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;'
            'font-size:0.78rem;font-weight:700;">{}</span>', bg, c, label
        )

    @admin.display(description='Initials')
    def initials_col(self, obj):
        try:
            initials = obj.initials or 'U'
        except Exception:
            initials = 'U'
        return format_html(
            '<div style="width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,#002b49,#3cb95d);'
            'color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:1rem;">{}</div>',
            initials
        )

    @admin.display(description='Verified', ordering='is_verified')
    def verified_badge_col(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="background:#f0fdf4;color:#166534;padding:3px 10px;border-radius:12px;'
                'font-size:0.78rem;font-weight:700;">Verified</span>'
            )
        return format_html(
            '<span style="background:#fef2f2;color:#991b1b;padding:3px 10px;border-radius:12px;'
            'font-size:0.78rem;font-weight:700;">Unverified</span>'
        )

    @admin.display(description='Account Type')
    def joint_badge_col(self, obj):
        try:
            if obj.profile.is_joint_account:
                return format_html(
                    '<span style="background:#eff6ff;color:#1d4ed8;padding:3px 10px;border-radius:12px;'
                    'font-size:0.78rem;font-weight:700;">Joint</span>'
                )
        except Exception:
            pass
        return format_html(
            '<span style="background:#f8fafc;color:#64748b;padding:3px 10px;border-radius:12px;'
            'font-size:0.78rem;font-weight:700;">Personal</span>'
        )

    @admin.display(description='Transactions')
    def transaction_count_col(self, obj):
        try:
            from transactions.models import Transaction
            count = Transaction.objects.filter(buyer=obj).count() + Transaction.objects.filter(seller=obj).count()
            if count > 0:
                return format_html('<strong style="color:#002b49;">{}</strong>', count)
        except Exception:
            pass
        return format_html('<span style="color:#94a3b8;">0</span>')

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
