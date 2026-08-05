"""
Chrysalias Transactions REST API Views
"""
import json
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Transaction, PartneredPayment, TransactionActivity
from .serializers import TransactionSerializer, PartneredPaymentSerializer


class TransactionListCreateView(generics.ListCreateAPIView):
    """List current user's transactions or create a new transaction"""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(
            Q(buyer=user) | Q(seller=user) | Q(buyer_email=user.email) | Q(seller_email=user.email)
        )

    def perform_create(self, serializer):
        role = self.request.data.get('initiator_role', 'Buyer')
        user = self.request.user

        # Pull write-only fields that aren't on Transaction model
        my_contrib    = float(self.request.data.get('my_contribution', 0) or 0)
        partner_contrib = float(self.request.data.get('partner_contribution', 0) or 0)
        partner_email = self.request.data.get('partner_email', '').strip()
        seller_phone  = self.request.data.get('seller_phone', '').strip()
        description   = self.request.data.get('description', '').strip()
        is_partnered  = bool(self.request.data.get('is_partnered', False))

        kwargs = {
            'initiator_role': role,
            'description': description,
        }
        if role == 'Buyer':
            kwargs['buyer'] = user
            kwargs['seller_email'] = self.request.data.get('seller_email', '').strip()
        elif role == 'Seller':
            kwargs['seller'] = user
            kwargs['buyer_email'] = self.request.data.get('buyer_email', '').strip()

        # Exclude write-only fields from serializer.save()
        serializer.validated_data.pop('my_contribution', None)
        serializer.validated_data.pop('partner_contribution', None)
        serializer.validated_data.pop('seller_phone', None)
        serializer.validated_data.pop('partner_email', None)

        tx = serializer.save(**kwargs)

        # Log activity
        TransactionActivity.objects.create(
            transaction=tx,
            action='created',
            performed_by=user,
            notes=f'Transaction {tx.tx_id} created via Chrysalias dashboard'
        )

        # Create PartneredPayment record with actual custom amounts
        if is_partnered and partner_email:
            tx.is_partnered = True
            tx.save(update_fields=['is_partnered'])
            total = float(tx.amount)
            p_amt = partner_contrib if partner_contrib > 0 else (total - my_contrib if my_contrib > 0 else total / 2)
            PartneredPayment.objects.create(
                transaction=tx,
                partner_email=partner_email,
                split_type='custom' if (my_contrib > 0 or partner_contrib > 0) else '50_50',
                partner_amount=round(p_amt, 2),
            )


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or cancel a specific transaction by tx_id or pk"""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'tx_id'

    def get_queryset(self):
        return Transaction.objects.all()


class PartneredPaymentDetailView(APIView):
    """Retrieve or submit payment for a partnered payment link token"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        pp = get_object_or_404(PartneredPayment, payment_token=token)
        tx = pp.transaction
        return Response({
            'transaction_id': tx.tx_id,
            'title': tx.title,
            'amount': tx.amount,
            'currency': tx.currency,
            'partner_email': pp.partner_email,
            'partner_amount': pp.partner_amount,
            'split_type': pp.get_split_type_display(),
            'status': pp.partner_status,
            'created_at': pp.created_at,
        })

    def post(self, request, token):
        pp = get_object_or_404(PartneredPayment, payment_token=token)
        pp.partner_status = 'paid'
        pp.save()

        tx = pp.transaction
        tx.status = 'Funded'
        tx.save()

        TransactionActivity.objects.create(
            transaction=tx,
            action='partner_paid',
            notes=f'Partner ({pp.partner_email}) completed co-funding payment.'
        )

        return Response({'success': True, 'message': 'Partnered payment completed successfully!'})


class UploadReceiptView(APIView):
    """
    POST /api/transactions/<tx_id>/upload-receipt/
    Accepts multipart/form-data with a 'receipt' file.
    Marks the transaction as Pending Verification and records the upload.
    Optional field: 'receipt_type' = 'primary' | 'partner' (defaults to 'primary')
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, tx_id):
        tx = get_object_or_404(Transaction, tx_id=tx_id)

        receipt_file = request.FILES.get('receipt')
        if not receipt_file:
            return Response({'error': 'No receipt file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file type (accept images and PDFs only)
        allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
        if receipt_file.content_type not in allowed_types:
            return Response(
                {'error': 'Invalid file type. Please upload a JPG, PNG, WEBP, or PDF file.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Max 10 MB
        if receipt_file.size > 10 * 1024 * 1024:
            return Response({'error': 'File too large. Maximum size is 10 MB.'}, status=status.HTTP_400_BAD_REQUEST)

        receipt_type = request.data.get('receipt_type', 'primary')
        half_amount = float(tx.amount) / 2 if (tx.is_partnered or tx.is_joint) else float(tx.amount)

        if receipt_type == 'partner':
            tx.partner_receipt = receipt_file
            tx.partner_amount_paid = half_amount
        else:
            tx.primary_receipt = receipt_file
            tx.primary_amount_paid = half_amount

        # Check if both have paid
        both_paid = (tx.primary_amount_paid > 0 and tx.partner_amount_paid > 0) if (tx.is_partnered or tx.is_joint) else True

        # Advance status to Pending Verification if still in Draft
        if tx.status == Transaction.STATUS_DRAFT:
            tx.status = Transaction.STATUS_RECEIPT_PENDING

        tx.save()

        # Log activity
        uploader_label = 'Partner' if receipt_type == 'partner' else 'Primary User'
        TransactionActivity.objects.create(
            transaction=tx,
            action='funded',
            performed_by=request.user if request.user.is_authenticated else None,
            notes=f'{uploader_label} uploaded payment receipt. Awaiting admin verification.',
        )

        # Dispatch emails (async, non-blocking)
        try:
            import threading
            from accounts.emails import send_receipt_submitted_email, send_joint_partner_paid_email

            buyer_name = tx.buyer.display_name if tx.buyer else (tx.buyer_email or 'Customer')

            # Notify uploader
            threading.Thread(
                target=send_receipt_submitted_email,
                kwargs=dict(
                    user_email=request.user.email if request.user.is_authenticated else (tx.buyer_email or 'customer@email.com'),
                    user_name=buyer_name,
                    tx_id=tx.tx_id,
                    amount_paid=float(half_amount),
                ),
                daemon=True,
            ).start()

            # Cross-notify joint partner if applicable
            if tx.is_partnered or tx.is_joint:
                if receipt_type == 'primary':
                    partner_email = tx.partner_email or (tx.partnered_payments.first().partner_email if tx.partnered_payments.exists() else '')
                    if partner_email:
                        threading.Thread(
                            target=send_joint_partner_paid_email,
                            kwargs=dict(
                                recipient_email=partner_email,
                                recipient_name='Partner',
                                payer_name=buyer_name,
                                tx_id=tx.tx_id,
                                tx_title=tx.title,
                                amount_paid=float(half_amount),
                                remaining_amount=float(half_amount),
                                both_paid=both_paid,
                            ),
                            daemon=True,
                        ).start()
                elif receipt_type == 'partner':
                    primary_email = tx.buyer_email or (tx.buyer.email if tx.buyer else '')
                    if primary_email:
                        threading.Thread(
                            target=send_joint_partner_paid_email,
                            kwargs=dict(
                                recipient_email=primary_email,
                                recipient_name=buyer_name,
                                payer_name='Partner',
                                tx_id=tx.tx_id,
                                tx_title=tx.title,
                                amount_paid=float(half_amount),
                                remaining_amount=float(half_amount),
                                both_paid=both_paid,
                            ),
                            daemon=True,
                        ).start()

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to dispatch payment notifications: {e}")

        return Response({
            'success': True,
            'message': 'Receipt uploaded successfully. Our team will verify your payment within 1–2 business hours.',
            'tx_id': tx.tx_id,
            'status': tx.status,
            'both_paid': both_paid,
        })

