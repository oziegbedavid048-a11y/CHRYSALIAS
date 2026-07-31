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
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Transaction.objects.all()[:10]  # Public fallback list for demo
        return Transaction.objects.filter(
            Q(buyer=user) | Q(seller=user) | Q(buyer_email=user.email) | Q(seller_email=user.email)
        )

    def perform_create(self, serializer):
        role = self.request.data.get('initiator_role', 'Buyer')
        user = self.request.user if self.request.user.is_authenticated else None

        kwargs = {'initiator_role': role}
        if role == 'Buyer' and user:
            kwargs['buyer'] = user
            kwargs['seller_email'] = self.request.data.get('seller_email', '')
        elif role == 'Seller' and user:
            kwargs['seller'] = user
            kwargs['buyer_email'] = self.request.data.get('buyer_email', '')

        tx = serializer.save(**kwargs)

        # Log activity
        TransactionActivity.objects.create(
            transaction=tx,
            action='created',
            performed_by=user,
            notes=f'Transaction {tx.tx_id} created'
        )

        # Check if partnered payment details provided
        if self.request.data.get('is_partnered'):
            partner_email = self.request.data.get('partner_email', '')
            split_type = self.request.data.get('partner_split', '50_50')
            if partner_email:
                partner_amount = tx.amount / 2 if split_type == '50_50' else tx.amount
                PartneredPayment.objects.create(
                    transaction=tx,
                    partner_email=partner_email,
                    split_type=split_type,
                    partner_amount=partner_amount
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
