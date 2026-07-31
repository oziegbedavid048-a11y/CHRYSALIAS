"""
Chrysalias Transactions Models
Complete escrow transaction lifecycle management.
"""
import uuid
import random
import string
from django.db import models
from django.conf import settings


def generate_tx_id():
    """Generate unique Chrysalias transaction ID: ESC-XXXXXX"""
    digits = ''.join(random.choices(string.digits, k=6))
    return f'ESC-{digits}'


def generate_partner_token():
    """Generate unique token for partnered payment links"""
    return uuid.uuid4().hex


class Transaction(models.Model):
    """
    Core Chrysalias escrow transaction.
    Represents a full payment protection agreement between buyer and seller.
    """
    STATUS_DRAFT       = 'Draft'
    STATUS_FUNDED      = 'Funded'
    STATUS_INSPECTION  = 'In Inspection'
    STATUS_IN_PROGRESS = 'In Progress'
    STATUS_COMPLETED   = 'Completed'
    STATUS_CANCELLED   = 'Cancelled'
    STATUS_DISPUTED    = 'Disputed'

    STATUS_CHOICES = [
        (STATUS_DRAFT,       'Draft — Awaiting Funding'),
        (STATUS_FUNDED,      'Funded — Payment Held'),
        (STATUS_INSPECTION,  'In Inspection Period'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED,   'Completed — Funds Released'),
        (STATUS_CANCELLED,   'Cancelled'),
        (STATUS_DISPUTED,    'Disputed — Under Review'),
    ]

    CATEGORY_CHOICES = [
        ('Domain Names',              'Domain Names'),
        ('Motor Vehicles',            'Motor Vehicles (Cars, Boats, Aircraft)'),
        ('Estate & Real Estate',      'Estate & Real Estate'),
        ('General Merchandise',       'General Merchandise'),
        ('Jewelry & Watches',         'Jewelry & Watches'),
        ('Antiques & Collectibles',   'Antiques & Collectibles'),
        ('Milestone Services',        'Milestone Services & Contracts'),
        ('IPv4 Addresses',            'IPv4 Addresses'),
        ('Software & Digital Assets', 'Software & Digital Assets'),
    ]

    CURRENCY_CHOICES = [
        ('USD', 'USD — US Dollar ($)'),
        ('EUR', 'EUR — Euro (€)'),
        ('GBP', 'GBP — British Pound (£)'),
        ('CAD', 'CAD — Canadian Dollar'),
        ('AUD', 'AUD — Australian Dollar'),
    ]

    ROLE_CHOICES = [
        ('Buyer',  'Buyer'),
        ('Seller', 'Seller'),
        ('Broker', 'Broker'),
    ]

    # Identifiers
    tx_id          = models.CharField(max_length=20, unique=True, default=generate_tx_id, editable=False)
    title          = models.CharField(max_length=300)
    description    = models.TextField(blank=True)

    # Parties
    buyer          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='buyer_transactions')
    seller         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='seller_transactions')
    buyer_email    = models.EmailField(blank=True, help_text='Used if buyer not registered')
    seller_email   = models.EmailField(blank=True, help_text='Used if seller not registered')
    initiator_role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Buyer')

    # Transaction Details
    amount            = models.DecimalField(max_digits=18, decimal_places=2)
    currency          = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    category          = models.CharField(max_length=60, choices=CATEGORY_CHOICES, default='General Merchandise')
    inspection_period = models.PositiveIntegerField(default=2, help_text='Inspection period in days')
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # Partnered Payment
    is_partnered       = models.BooleanField(default=False)

    # Fees (calculated on save)
    escrow_fee         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    processing_fee     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_fee          = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Timestamps
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)
    completed_at       = models.DateTimeField(null=True, blank=True)

    # Admin Notes
    admin_notes        = models.TextField(blank=True)

    class Meta:
        verbose_name       = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering           = ['-created_at']

    def __str__(self):
        return f'{self.tx_id} — {self.title} ({self.currency} {self.amount})'

    def save(self, *args, **kwargs):
        # Auto-calculate fees on save
        amount = float(self.amount or 0)
        if amount > 25000:
            fee_rate = 0.0125
        elif amount > 5000:
            fee_rate = 0.022
        else:
            fee_rate = 0.0325

        self.escrow_fee     = round(max(25, amount * fee_rate), 2)
        self.processing_fee = round(amount * 0.015, 2)
        self.total_fee      = round(float(self.escrow_fee) + float(self.processing_fee), 2)
        super().save(*args, **kwargs)

    @property
    def counterparty_email(self):
        """Return the other party's email"""
        if self.initiator_role == 'Buyer':
            return self.seller_email or (self.seller.email if self.seller else '')
        return self.buyer_email or (self.buyer.email if self.buyer else '')

    @property
    def status_colour(self):
        colours = {
            'Draft':         '#94a3b8',
            'Funded':        '#3b82f6',
            'In Inspection': '#f59e0b',
            'In Progress':   '#3b82f6',
            'Completed':     '#22c55e',
            'Cancelled':     '#ef4444',
            'Disputed':      '#f97316',
        }
        return colours.get(self.status, '#94a3b8')


class PartneredPayment(models.Model):
    """Partnered / Co-funded payment configuration for a transaction"""

    SPLIT_CHOICES = [
        ('50_50',        '50% / 50% Equal Split'),
        ('partner_full', 'Partner Pays Full Remaining Balance'),
        ('custom',       'Custom Contribution Amount'),
    ]

    PARTNER_STATUS_CHOICES = [
        ('pending',   'Payment Link Sent — Awaiting Partner'),
        ('paid',      'Partner Payment Received'),
        ('expired',   'Link Expired'),
        ('cancelled', 'Cancelled'),
    ]

    transaction     = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='partnered_payment')
    partner_email   = models.EmailField()
    split_type      = models.CharField(max_length=20, choices=SPLIT_CHOICES, default='50_50')
    partner_amount  = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    partner_status  = models.CharField(max_length=20, choices=PARTNER_STATUS_CHOICES, default='pending')
    payment_token   = models.CharField(max_length=64, unique=True, default=generate_partner_token, editable=False)
    created_at      = models.DateTimeField(auto_now_add=True)
    paid_at         = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name       = 'Partnered Payment'
        verbose_name_plural = 'Partnered Payments'

    def __str__(self):
        return f'Partnered Payment for {self.transaction.tx_id} → {self.partner_email}'

    @property
    def payment_link(self):
        return f'/partnered-payment.html?token={self.payment_token}'


class TransactionDocument(models.Model):
    """Documents/attachments uploaded for a transaction"""
    transaction  = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='documents')
    name         = models.CharField(max_length=200)
    file         = models.FileField(upload_to='tx_documents/')
    uploaded_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name       = 'Transaction Document'
        verbose_name_plural = 'Transaction Documents'
        ordering           = ['-uploaded_at']

    def __str__(self):
        return f'{self.name} — {self.transaction.tx_id}'


class TransactionActivity(models.Model):
    """Activity log for each transaction — every state change is recorded"""

    ACTION_CHOICES = [
        ('created',         'Transaction Created'),
        ('funded',          'Payment Funded'),
        ('inspection_start','Inspection Period Started'),
        ('inspection_end',  'Inspection Period Ended'),
        ('partner_invited', 'Partner Payment Invited'),
        ('partner_paid',    'Partner Payment Received'),
        ('approved',        'Buyer Approved Release'),
        ('completed',       'Transaction Completed'),
        ('cancelled',       'Transaction Cancelled'),
        ('disputed',        'Dispute Raised'),
        ('resolved',        'Dispute Resolved'),
        ('admin_note',      'Admin Note Added'),
    ]

    transaction  = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='activities')
    action       = models.CharField(max_length=30, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes        = models.TextField(blank=True)
    timestamp    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name       = 'Activity Log Entry'
        verbose_name_plural = 'Activity Log'
        ordering           = ['-timestamp']

    def __str__(self):
        return f'{self.transaction.tx_id} — {self.get_action_display()} @ {self.timestamp:%Y-%m-%d %H:%M}'
