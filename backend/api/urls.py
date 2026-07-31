"""
Chrysalias API Helper URLs
"""
from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('stats/', views.SystemStatsView.as_view(), name='stats'),
]
