"""
Chrysalias Accounts URL Configuration
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('csrf/',                views.CSRFTokenView.as_view(),            name='csrf'),
    path('register/',            views.RegisterView.as_view(),             name='register'),
    path('verify-email/',        views.VerifyEmailView.as_view(),          name='verify-email'),
    path('resend-verification/', views.ResendVerificationView.as_view(),   name='resend-verification'),
    path('login/',               views.LoginView.as_view(),                name='login'),
    path('logout/',              views.LogoutView.as_view(),               name='logout'),
    path('me/',                  views.MeView.as_view(),                   name='me'),
    path('send-email/',          views.SendEmailNotificationView.as_view(), name='send-email'),
    path('test-email/',          views.TestEmailView.as_view(),            name='test-email'),
    path('diagnostics/',         views.SystemDiagnosticsView.as_view(),    name='diagnostics'),
]
