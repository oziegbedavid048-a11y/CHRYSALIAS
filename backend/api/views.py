"""
System level API endpoints — Dashboard stats & health check
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Sum, Count
from transactions.models import Transaction
from accounts.models import User


class SystemStatsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        total_tx = Transaction.objects.count()
        completed_tx = Transaction.objects.filter(status='Completed').count()
        ongoing_tx = Transaction.objects.filter(status__in=['Draft', 'Funded', 'In Inspection', 'In Progress']).count()
        volume = Transaction.objects.filter(status='Completed').aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'status': 'online',
            'platform': 'Chrysalias.com',
            'total_users': User.objects.count(),
            'total_transactions': total_tx,
            'completed_transactions': completed_tx,
            'ongoing_transactions': ongoing_tx,
            'protected_volume': float(volume),
        })
