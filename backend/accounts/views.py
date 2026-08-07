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

        email        = data.get('email', '').strip().lower()
        password     = data.get('password', '').strip()
        full_name    = data.get('full_name', '').strip()
        username     = data.get('username', email.split('@')[0])
        is_joint     = bool(data.get('is_joint', False))
        partner_name  = data.get('partner_name', '').strip()
        partner_email = data.get('partner_email', '').strip().lower()

        if not email or not password:
            return json_response({'error': 'Email and password are required.'}, 400)

        if User.objects.filter(email=email).exists():
            return json_response({'error': 'An account with this email already exists.'}, 400)

        if len(password) < 6:
            return json_response({'error': 'Password must be at least 6 characters.'}, 400)

        if is_joint and not partner_email:
            return json_response({'error': 'Joint Account requires a partner email address.'}, 400)

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
            is_verified=False,
            is_active=True,
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # Save joint account details to profile
        if is_joint:
            profile.is_joint_account    = True
            profile.joint_partner_name  = partner_name
            profile.joint_partner_email = partner_email
            profile.save()

        token, _ = Token.objects.get_or_create(user=user)
        login(request, user)

        # Send account confirmation email to primary user (async)
        try:
            from .emails import send_account_confirmation_email, send_joint_partner_notification_email
            from django.conf import settings as django_settings
            base_url = getattr(django_settings, 'FRONTEND_BASE_URL', None)
            send_account_confirmation_email(user, base_url=base_url)
            # Send joint partner notification email
            if is_joint and partner_email:
                send_joint_partner_notification_email(
                    partner_email=partner_email,
                    primary_name=user.display_name,
                    partner_name=partner_name or 'Partner',
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to dispatch email(s): {e}")

        return json_response({
            'success': True,
            'message': 'Account created successfully. Please check your email to verify your account.',
            'email_sent': True,
            'is_joint': is_joint,
            'user': {
                'id':             user.id,
                'email':          user.email,
                'name':           user.display_name,
                'full_name':      user.full_name,
                'initials':       user.initials,
                'kyc':            user.kyc_status,
                'verified':       user.is_verified,
                'is_joint':       is_joint,
                'partner_name':   partner_name,
                'partner_email':  partner_email,
            }
        }, 201)



@method_decorator(csrf_exempt, name='dispatch')
class VerifyEmailView(View):
    """
    Verifies user email token from email link.
    GET /api/auth/verify-email/?uid=<uid>&token=<token>
    """
    def get(self, request):
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        from django.contrib.auth.tokens import default_token_generator

        uidb64 = request.GET.get('uid', '')
        token = request.GET.get('token', '')

        if not uidb64 or not token:
            return json_response({'error': 'Verification UID and token are required.'}, 400)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return json_response({'error': 'Invalid verification link or user does not exist.'}, 400)

        if user.is_verified:
            return json_response({
                'success': True,
                'already_verified': True,
                'message': 'Account is already verified.'
            })

        if default_token_generator.check_token(user, token):
            user.is_verified = True
            if user.kyc_status == 'pending':
                user.kyc_status = 'level_1'
            user.save()
            return json_response({
                'success': True,
                'message': 'Email address verified successfully! You can now access full features.'
            })
        else:
            return json_response({'error': 'Verification link is invalid or has expired.'}, 400)


@method_decorator(csrf_exempt, name='dispatch')
class ResendVerificationView(View):
    """
    Resends account confirmation email to unverified user.
    POST /api/auth/resend-verification/ {'email': '...'}
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
        except Exception:
            return json_response({'error': 'Invalid JSON.'}, 400)

        email = data.get('email', '').strip().lower()
        if not email:
            return json_response({'error': 'Email address is required.'}, 400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Return generic message to prevent email enumeration
            return json_response({'success': True, 'message': 'If an account exists with this email, a verification link has been sent.'})

        if user.is_verified:
            return json_response({'success': True, 'message': 'This account is already verified.'})

        from .emails import send_account_confirmation_email
        origin = request.headers.get('origin') or request.headers.get('referer') or ''
        base_url = origin.rstrip('/') if origin else None
        send_account_confirmation_email(user, base_url=base_url)

        return json_response({
            'success': True,
            'message': 'Verification email dispatched. Please check your inbox and spam folder.'
        })


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
        is_joint = False
        joint_partner_name = ''
        joint_partner_email = ''
        profile_picture = None
        try:
            profile = user.profile
            is_joint = profile.is_joint_account
            joint_partner_name = profile.joint_partner_name or ''
            joint_partner_email = profile.joint_partner_email or ''
            if profile.profile_picture:
                profile_picture = request.build_absolute_uri(profile.profile_picture.url)
        except Exception:
            pass
        return json_response({
            'authenticated': True,
            'user': {
                'id':                  user.id,
                'email':               user.email,
                'name':                user.display_name,
                'full_name':           user.full_name,
                'initials':            user.initials,
                'kyc':                 user.kyc_status,
                'verified':            user.is_verified,
                'is_staff':            user.is_staff,
                'is_joint':            is_joint,
                'joint_partner_name':  joint_partner_name,
                'joint_partner_email': joint_partner_email,
                'profile_picture':     profile_picture,
            }
        })


@method_decorator(csrf_exempt, name='dispatch')
class UploadProfilePictureView(View):
    """Allows authenticated user to upload/update their profile picture"""
    def post(self, request):
        if not request.user.is_authenticated:
            return json_response({'error': 'Authentication required.'}, 401)
        
        file = request.FILES.get('profile_picture') or request.FILES.get('avatar') or request.FILES.get('file')
        if not file:
            return json_response({'error': 'No image file provided.'}, 400)
        
        user = request.user
        from .models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.profile_picture = file
        profile.save()

        avatar_url = request.build_absolute_uri(profile.profile_picture.url) if profile.profile_picture else ''
        return json_response({
            'success': True,
            'message': 'Profile picture uploaded successfully.',
            'profile_picture': avatar_url,
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


@method_decorator(csrf_exempt, name='dispatch')
class TestEmailView(View):
    """Diagnostic endpoint — tests SMTP config from within Render's environment."""
    def get(self, request):
        from django.conf import settings
        import smtplib

        result = {
            'EMAIL_BACKEND': settings.EMAIL_BACKEND,
            'EMAIL_HOST': settings.EMAIL_HOST,
            'EMAIL_PORT': settings.EMAIL_PORT,
            'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
            'EMAIL_HOST_PASSWORD_SET': bool(settings.EMAIL_HOST_PASSWORD),
            'EMAIL_HOST_PASSWORD_LENGTH': len(settings.EMAIL_HOST_PASSWORD or ''),
            'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        }

        # Test SMTP connection
        try:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.quit()
            result['smtp_connection'] = 'SUCCESS'
        except Exception as e:
            result['smtp_connection'] = f'FAILED: {type(e).__name__}: {e}'

        # Test actual Django email send
        try:
            from .emails import send_account_confirmation_email
            test_to = request.GET.get('to', settings.DEFAULT_FROM_EMAIL)
            sent = send_account_confirmation_email(test_to, 'Test User')
            result['email_sent'] = sent
            result['email_sent_to'] = test_to
        except Exception as e:
            import traceback
            result['email_send_error'] = f'{type(e).__name__}: {e}'
            result['email_traceback'] = traceback.format_exc()

        return json_response(result)


@method_decorator(csrf_exempt, name='dispatch')
class SystemDiagnosticsView(View):
    """
    Full system diagnostics endpoint — call this from Render to test everything.
    GET /api/auth/diagnostics/
    """
    def get(self, request):
        from django.conf import settings
        from django.db import connection
        import smtplib

        result = {}

        # 1. Database
        try:
            cursor = connection.cursor()
            cursor.execute('SELECT version();')
            db_version = cursor.fetchone()[0][:80]
            from accounts.models import User, UserProfile
            from transactions.models import Transaction
            user_count = User.objects.count()
            tx_count = Transaction.objects.count()
            users_list = [
                {
                    'email': u.email,
                    'is_staff': u.is_staff,
                    'is_superuser': u.is_superuser,
                    'is_active': u.is_active,
                    'has_profile': UserProfile.objects.filter(user=u).exists(),
                }
                for u in User.objects.all()[:20]
            ]
            result['database'] = {
                'status': 'CONNECTED',
                'version': db_version,
                'total_users': user_count,
                'total_transactions': tx_count,
                'users': users_list,
            }
            # Auto-fix any missing UserProfiles
            fixed = 0
            for u in User.objects.all():
                _, created = UserProfile.objects.get_or_create(user=u)
                if created:
                    fixed += 1
            result['database']['profiles_fixed'] = fixed
        except Exception as e:
            import traceback
            result['database'] = {'status': 'FAILED', 'error': str(e), 'traceback': traceback.format_exc()}

        # 2. SMTP / Email
        result['smtp'] = {
            'EMAIL_HOST': settings.EMAIL_HOST,
            'EMAIL_PORT': settings.EMAIL_PORT,
            'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
            'PASSWORD_SET': bool(settings.EMAIL_HOST_PASSWORD),
            'PASSWORD_LENGTH': len(settings.EMAIL_HOST_PASSWORD or ''),
            'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        }
        try:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=20)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.quit()
            result['smtp']['connection'] = 'SUCCESS'
        except Exception as e:
            result['smtp']['connection'] = f'FAILED: {type(e).__name__}: {e}'

        # 3. Send a real test email if ?send=1&to=email@example.com is passed
        if request.GET.get('send') == '1':
            test_to = request.GET.get('to', settings.DEFAULT_FROM_EMAIL)
            try:
                from .emails import send_account_confirmation_email
                sent = send_account_confirmation_email(test_to, 'Diagnostics Test')
                result['email_send'] = {'sent': sent, 'to': test_to}
            except Exception as e:
                import traceback
                result['email_send'] = {'sent': False, 'error': str(e), 'traceback': traceback.format_exc()}

        # 4. Settings summary
        result['settings'] = {
            'DEBUG': settings.DEBUG,
            'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
            'SECURE_SSL_REDIRECT': settings.SECURE_SSL_REDIRECT,
            'AUTH_USER_MODEL': settings.AUTH_USER_MODEL,
        }

        return json_response(result)
