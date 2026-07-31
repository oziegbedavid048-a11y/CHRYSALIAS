"""
Chrysalias Transactions URL Configuration
"""
from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('transactions/', views.TransactionListCreateView.as_view(), name='list_create'),
    path('transactions/<str:tx_id>/', views.TransactionDetailView.as_view(), name='detail'),
    path('partnered/<str:token>/', views.PartneredPaymentDetailView.as_view(), name='partnered_detail'),
]
