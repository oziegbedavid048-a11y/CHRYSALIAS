"""
Chrysalias Transactions Serializers
"""
from rest_framework import serializers
from accounts.models import User
from .models import Transaction, PartneredPayment, TransactionDocument, TransactionActivity


class PartneredPaymentSerializer(serializers.ModelSerializer):
    payment_link = serializers.ReadOnlyField()

    class Meta:
        model = PartneredPayment
        fields = [
            'id', 'partner_email', 'split_type', 'partner_amount',
            'partner_status', 'payment_token', 'payment_link', 'created_at', 'paid_at'
        ]


class TransactionDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.ReadOnlyField(source='uploaded_by.email')

    class Meta:
        model = TransactionDocument
        fields = ['id', 'name', 'file', 'uploaded_by_email', 'uploaded_at']


class TransactionActivitySerializer(serializers.ModelSerializer):
    performed_by_email = serializers.ReadOnlyField(source='performed_by.email')

    class Meta:
        model = TransactionActivity
        fields = ['id', 'action', 'performed_by_email', 'notes', 'timestamp']


class TransactionSerializer(serializers.ModelSerializer):
    partnered_payment = PartneredPaymentSerializer(read_only=True)
    documents = TransactionDocumentSerializer(many=True, read_only=True)
    activities = TransactionActivitySerializer(many=True, read_only=True)
    buyer_email_display = serializers.SerializerMethodField()
    seller_email_display = serializers.SerializerMethodField()

    # Write-only fields from frontend (not stored on Transaction model directly)
    my_contribution = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, write_only=True, default=0
    )
    partner_contribution = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, write_only=True, default=0
    )
    seller_phone = serializers.CharField(
        required=False, write_only=True, allow_blank=True, default=''
    )
    partner_email = serializers.EmailField(
        required=False, write_only=True, allow_blank=True, default=''
    )

    class Meta:
        model = Transaction
        fields = [
            'id', 'tx_id', 'title', 'description', 'buyer', 'seller',
            'buyer_email', 'seller_email', 'buyer_email_display', 'seller_email_display',
            'initiator_role', 'amount', 'currency', 'category', 'inspection_period',
            'status', 'is_partnered', 'escrow_fee', 'processing_fee', 'total_fee',
            'primary_amount_paid', 'partner_amount_paid',
            'partnered_payment', 'documents', 'activities',
            'created_at', 'updated_at', 'completed_at',
            # write-only
            'my_contribution', 'partner_contribution', 'seller_phone', 'partner_email',
        ]
        read_only_fields = [
            'id', 'tx_id', 'escrow_fee', 'processing_fee', 'total_fee',
            'primary_amount_paid', 'partner_amount_paid',
            'created_at', 'updated_at'
        ]

    def get_buyer_email_display(self, obj):
        return obj.buyer.email if obj.buyer else obj.buyer_email

    def get_seller_email_display(self, obj):
        return obj.seller.email if obj.seller else obj.seller_email
