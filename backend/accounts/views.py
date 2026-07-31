"""
Chrysalias Accounts API Views — Register, Login, Logout, Me
"""
import json
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from .models import User, UserProfile


def json_response(data, status=200):
    return JsonResponse(data, status=status)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(View):
    """Returns CSRF cookie + token for frontend to use in POST requests"""
    def get(self, request):
        return json_response({'csrfToken': get_token(request)})


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, Exception):
            return json_response({'error': 'Invalid JSON body.'}, 400)

        email     = data.get('email', '').strip().lower()
        password  = data.get('password', '').strip()
        full_name = data.get('full_name', '').strip()
        username  = data.get('username', email.split('@')[0])

        if not email or not password:
            return json_response({'error': 'Email and password are required.'}, 400)

        if User.objects.filter(email=email).exists():
            return json_response({'error': 'An account with this email already exists.'}, 400)

        if len(password) < 6:
            return json_response({'error': 'Password must be at least 6 characters.'}, 400)

        # Make username unique
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}{counter}'
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            kyc_status='level_1',
            is_verified=False,  # User must verify email before full access
            is_active=True,     # Account is active so login can work after verification
        )
        UserProfile.objects.get_or_create(user=user)

        token, _ = Token.objects.get_or_create(user=user)
        login(request, user)

        # Trigger account confirmation email via ZeptoMail
        try:
            from .emails import send_account_confirmation_email
            send_account_confirmation_email(user.email, user.display_name)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Confirmation email failed: {e}")

        return json_response({
            'success': True,
            'message': 'Account created successfully. Please check your email to verify your account.',
            'user': {
                'id':        user.id,
                'email':     user.email,
                'name':      user.display_name,
                'full_name': user.full_name,
                'initials':  user.initials,
                'kyc':       user.kyc_status,
                'verified':  user.is_verified,
            }
        }, 201)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
        except Exception:
            return json_response({'error': 'Invalid JSON body.'}, 400)

        email    = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()

        if not email or not password:
            return json_response({'error': 'Email and password are required.'}, 400)

        user = authenticate(request, username=email, password=password)
        if user is None:
            # Try authenticating by email directly
            try:
                u = User.objects.get(email=email)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                pass

        if user is None:
            return json_response({'error': 'Invalid email or password.'}, 401)

        if not user.is_active:
            return json_response({'error': 'This account has been deactivated.'}, 403)

        login(request, user)
        token, _ = Token.objects.get_or_create(user=user)

        return json_response({
            'success': True,
            'token': token.key,
            'user': {
                'id':        user.id,
                'email':     user.email,
                'name':      user.display_name,
                'full_name': user.full_name,
                'initials':  user.initials,
                'kyc':       user.kyc_status,
                'verified':  user.is_verified,
            }
        })


class LogoutView(View):
    def post(self, request):
        logout(request)
        return json_response({'success': True, 'message': 'Logged out successfully.'})


class MeView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return json_response({'authenticated': False}, 401)
        user = request.user
        return json_response({
            'authenticated': True,
            'user': {
                'id':        user.id,
                'email':     user.email,
                'name':      user.display_name,
                'full_name': user.full_name,
                'initials':  user.initials,
                'kyc':       user.kyc_status,
                'verified':  user.is_verified,
                'is_staff':  user.is_staff,
            }
        })


@method_decorator(csrf_exempt, name='dispatch')
class SendEmailNotificationView(View):
    """API Endpoint to dispatch system emails (welcome, tx_created, partnered_invitation, payment_confirmed)"""
    def post(self, request):
        try:
            data = json.loads(request.body)
        except Exception:
            return json_response({'error': 'Invalid JSON.'}, 400)

        email_type = data.get('type')
        email = data.get('email')
        name = data.get('name', 'Valued Customer')
        tx_data = data.get('tx_data', {})

        if not email_type or not email:
            return json_response({'error': 'type and email are required.'}, 400)

        from .emails import (
            send_welcome_email,
            send_new_transaction_email,
            send_partnered_payment_invitation,
            send_payment_confirmation_email,
        )

        sent = False
        if email_type == 'welcome':
            sent = send_welcome_email(email, name)
        elif email_type == 'tx_created':
            sent = send_new_transaction_email(email, name, tx_data)
        elif email_type == 'partnered_invitation':
            initiator = data.get('initiator_name', 'A Chrysalias User')
            partner_link = data.get('partner_link', '')
            sent = send_partnered_payment_invitation(email, initiator, tx_data, partner_link)
        elif email_type == 'payment_confirmed':
            amount_paid = data.get('amount_paid', tx_data.get('amount', 0.0))
            sent = send_payment_confirmation_email(email, name, tx_data, amount_paid)
        else:
            return json_response({'error': 'Unknown email type.'}, 400)

        return json_response({'success': sent, 'email': email, 'type': email_type})

