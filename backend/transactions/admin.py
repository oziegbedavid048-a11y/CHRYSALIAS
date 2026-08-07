"""
Chrysalias Transactions Admin
Comprehensive transaction management, inline partnered payments, documents & activity logs.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Transaction, PartneredPayment, TransactionDocument, TransactionActivity


class PartneredPaymentInline(admin.StackedInline):
    model = PartneredPayment
    can_delete = False
    verbose_name = 'Partnered / Co-Funding Payment Details'
    verbose_name_plural = 'Partnered Payment Details'
    fieldsets = (
        ('Partner Details & Contribution Balances', {
            'fields': ('partner_email', 'split_type', 'partner_amount', 'partner_status', 'payment_token', 'paid_at'),
        }),
    )
    readonly_fields = ('payment_token',)


class TransactionDocumentInline(admin.TabularInline):
    model = TransactionDocument
    extra = 1
    fields = ('name', 'file', 'uploaded_by', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class TransactionActivityInline(admin.TabularInline):
    model = TransactionActivity
    extra = 0
    fields = ('action', 'performed_by', 'notes', 'timestamp')
    readonly_fields = ('timestamp',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    inlines = [PartneredPaymentInline, TransactionDocumentInline, TransactionActivityInline]
    list_display = (
        'tx_id_col',
        'title_col',
        'parties_col',
        'amount_col',
        'category',
        'status_badge_col',
        'is_partnered_col',
        'created_at'
    )
    list_filter = ('status', 'currency', 'category', 'is_partnered', 'created_at')
    search_fields = ('tx_id', 'title', 'buyer_email', 'seller_email', 'buyer__email', 'seller__email', 'buyer__full_name', 'seller__full_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20

    fieldsets = (
        ('Transaction Identity & Agreement Details', {
            'fields': ('tx_id', 'title', 'category', 'status', 'description'),
        }),
        ('Parties Involved', {
            'fields': ('initiator_role', 'buyer', 'buyer_email', 'seller', 'seller_email'),
        }),
        ('Financial Terms & Contribution Balances', {
            'fields': ('currency', 'amount', 'inspection_period', 'is_partnered', 'primary_amount_paid', 'partner_amount_paid'),
        }),
        ('Chrysalias Service Fees (Editable Figures)', {
            'fields': ('escrow_fee', 'processing_fee', 'total_fee'),
        }),
        ('Payment Receipts & Verification Uploads', {
            'fields': ('primary_receipt', 'partner_receipt'),
        }),
        ('Administrative & Agreement Notes', {
            'fields': ('admin_notes', 'created_at', 'updated_at', 'completed_at'),
        }),
    )

    actions = ['verify_payment', 'mark_as_funded', 'mark_as_inspection', 'mark_as_completed', 'mark_as_cancelled', 'mark_as_disputed']

    @admin.display(description='Transaction ID', ordering='tx_id')
    def tx_id_col(self, obj):
        return format_html(
            '<strong style="color:#002b49;font-family:monospace;font-size:0.9rem;">{}</strong>',
            obj.tx_id
        )

    @admin.display(description='Title / Item')
    def title_col(self, obj):
        desc = f'<div style="font-size:0.75rem;color:#64748b;">{obj.description[:50]}...</div>' if obj.description else ''
        return format_html(
            '<div style="max-width:220px;">'
            '<strong style="color:#0f172a;display:block;">{}</strong>{}'
            '</div>',
            obj.title, format_html(desc)
        )

    @admin.display(description='Buyer / Seller')
    def parties_col(self, obj):
        buyer_str = obj.buyer.email if obj.buyer else (obj.buyer_email or 'Buyer Unknown')
        seller_str = obj.seller.email if obj.seller else (obj.seller_email or 'Seller Unknown')
        return format_html(
            '<div style="font-size:0.8rem;line-height:1.4;">'
            '<div><span style="color:#64748b;">Buyer:</span> <strong>{}</strong></div>'
            '<div><span style="color:#64748b;">Seller:</span> <strong>{}</strong></div>'
            '</div>',
            buyer_str, seller_str
        )

    @admin.display(description='Amount', ordering='amount')
    def amount_col(self, obj):
        val = f'{obj.amount:,.2f}' if obj.amount is not None else '0.00'
        return format_html(
            '<strong style="color:#002b49;font-size:0.92rem;">{} {}</strong>',
            obj.currency, val
        )

    @admin.display(description='Status')
    def status_badge_col(self, obj):
        colours = {
            'Draft':                ('#94a3b8', '#f8fafc',  'Draft'),
            'Pending Verification': ('#d97706', '#fef3c7',  '⏳ Pending Verification'),
            'Funded':               ('#0284c7', '#e0f2fe',  'Funded'),
            'In Inspection':        ('#d97706', '#fef3c7',  'In Inspection'),
            'In Progress':          ('#0284c7', '#e0f2fe',  'In Progress'),
            'Completed':            ('#166534', '#dcfce7',  'Completed'),
            'Cancelled':            ('#991b1b', '#fee2e2',  'Cancelled'),
            'Disputed':             ('#c2410c', '#ffedd5',  'Disputed'),
        }
        c, bg, label = colours.get(obj.status, ('#475569', '#f1f5f9', obj.status))
        return format_html(
            '<span style="background:{};color:{};padding:4px 10px;border-radius:12px;'
            'font-size:0.75rem;font-weight:700;display:inline-block;">{}</span>',
            bg, c, label
        )

    @admin.display(description='Partnered')
    def is_partnered_col(self, obj):
        if obj.is_partnered:
            return format_html(
                '<span style="background:#e0f2fe;color:#075985;padding:2px 8px;border-radius:10px;'
                'font-size:0.72rem;font-weight:700;">Co-Fund</span>'
            )
        return format_html('<span style="color:#cbd5e1;">—</span>')

    # ─── Admin Actions ──────────────────────────────────────────────
    @admin.action(description='✓ Verify Payment Receipt → Mark as Funded')
    def verify_payment(self, request, queryset):
        from accounts.emails import send_payment_verified_email
        verified = 0
        for tx in queryset.filter(status='Pending Verification'):
            tx.status = 'Funded'
            tx.save()
            TransactionActivity.objects.create(
                transaction=tx,
                action='funded',
                performed_by=request.user,
                notes='Payment receipt verified and confirmed by Admin. Transaction funded.',
            )
            # Email primary user (buyer)
            if tx.buyer:
                send_payment_verified_email(
                    user_email=tx.buyer.email,
                    user_name=tx.buyer.display_name,
                    tx_id=tx.tx_id,
                    amount_paid=float(tx.amount),
                )
            elif tx.buyer_email:
                send_payment_verified_email(
                    user_email=tx.buyer_email,
                    user_name='Valued Customer',
                    tx_id=tx.tx_id,
                    amount_paid=float(tx.amount),
                )
            verified += 1
        skipped = queryset.count() - verified
        msg = f'{verified} transaction(s) verified and marked as Funded.'
        if skipped:
            msg += f' {skipped} skipped (not in Pending Verification status).'
        self.message_user(request, msg)

    @admin.action(description='Mark selected transactions as Funded')
    def mark_as_funded(self, request, queryset):
        updated = queryset.update(status='Funded')
        self.message_user(request, f'{updated} transaction(s) marked as Funded.')

    @admin.action(description='Mark selected transactions as In Inspection')
    def mark_as_inspection(self, request, queryset):
        updated = queryset.update(status='In Inspection')
        self.message_user(request, f'{updated} transaction(s) marked as In Inspection.')

    @admin.action(description='Mark selected transactions as Completed (Release Funds)')
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='Completed')
        self.message_user(request, f'{updated} transaction(s) marked as Completed.')

    @admin.action(description='Mark selected transactions as Cancelled')
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='Cancelled')
        self.message_user(request, f'{updated} transaction(s) marked as Cancelled.')

    @admin.action(description='Mark selected transactions as Disputed')
    def mark_as_disputed(self, request, queryset):
        updated = queryset.update(status='Disputed')
        self.message_user(request, f'{updated} transaction(s) marked as Disputed.')


@admin.register(PartneredPayment)
class PartneredPaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'partner_email', 'split_type', 'partner_amount', 'partner_status', 'created_at')
    list_filter = ('partner_status', 'split_type', 'created_at')
    search_fields = ('transaction__tx_id', 'partner_email', 'payment_token')
    readonly_fields = ('payment_token', 'created_at', 'paid_at')


@admin.register(TransactionDocument)
class TransactionDocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'transaction', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('name', 'transaction__tx_id', 'uploaded_by__email')


@admin.register(TransactionActivity)
class TransactionActivityAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'action', 'performed_by', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('transaction__tx_id', 'notes', 'performed_by__email')
