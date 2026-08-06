import logging
import threading
import sys
import socket
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

logger = logging.getLogger(__name__)

EMAIL_HEADER_HTML = """
<div style="background-color: #002b49; padding: 24px; text-align: center; border-radius: 8px 8px 0 0;">
  <span style="font-family: 'Inter', sans-serif; font-weight: 800; font-size: 1.6rem; color: #ffffff; letter-spacing: -0.5px;">
    CHRYSALIAS<span style="color: #3cb95d;">.COM</span>
  </span>
  <div style="color: #cbd5e1; font-size: 0.8rem; margin-top: 4px;">Licensed Payment Protection Platform</div>
</div>
"""

EMAIL_FOOTER_HTML = """
<div style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0; border-radius: 0 0 8px 8px; color: #64748b; font-size: 0.8rem;">
  <p style="margin: 0 0 6px 0;">&copy; 2026 Chrysalias.com. All rights reserved.</p>
  <p style="margin: 0; font-size: 0.75rem;">This is an automated operational email. For assistance, contact support@chrysalias.com.</p>
</div>
"""


def generate_verification_url(user, base_url=None):
    """Generates cryptographically signed verification link for user"""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    if not base_url:
        base_url = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:8080')
    return f"{base_url.rstrip('/')}/verify-email.html?uid={uid}&token={token}"


def _send_worker(subject, recipient_email, text_content, html_content):
    """Worker function executed in background thread to avoid blocking HTTP responses"""
    socket.setdefaulttimeout(10)
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Chrysalias Support <info@chrysalias.com>')

    # Attempt 1: Standard Django EmailMultiAlternatives (using settings config)
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[recipient_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info(f"Email '{subject}' sent successfully to {recipient_email}")
        print(f"[Email Success] Sent '{subject}' to {recipient_email}", flush=True)
        return True
    except Exception as e:
        logger.warning(f"Standard Django email send failed ({type(e).__name__}: {e}). Trying SSL Port 465 failover...")

    # Attempt 2: Fallback to Port 465 SSL via smtplib
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        host_user = getattr(settings, 'EMAIL_HOST_USER', 'emailapikey')
        host_pass = getattr(settings, 'EMAIL_HOST_PASSWORD', '')

        with smtplib.SMTP_SSL('smtp.zeptomail.com', 465, timeout=10) as server:
            server.ehlo()
            server.login(host_user, host_pass)
            server.sendmail(from_email, [recipient_email], msg.as_string())
        logger.info(f"Email '{subject}' sent via Port 465 SSL to {recipient_email}")
        print(f"[Email Success] Sent '{subject}' to {recipient_email} via Port 465 SSL failover", flush=True)
        return True
    except Exception as e2:
        logger.warning(f"Port 465 SSL fallback failed ({type(e2).__name__}: {e2}). Trying Port 2525 TLS...")

    # Attempt 3: Fallback to Port 2525 TLS via smtplib
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        host_user = getattr(settings, 'EMAIL_HOST_USER', 'emailapikey')
        host_pass = getattr(settings, 'EMAIL_HOST_PASSWORD', '')

        with smtplib.SMTP('smtp.zeptomail.com', 2525, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(host_user, host_pass)
            server.sendmail(from_email, [recipient_email], msg.as_string())
        logger.info(f"Email '{subject}' sent via Port 2525 TLS to {recipient_email}")
        print(f"[Email Success] Sent '{subject}' to {recipient_email} via Port 2525 TLS failover", flush=True)
        return True
    except Exception as e3:
        logger.error(f"All SMTP delivery methods failed for {recipient_email}: {e3}")
        print(f"[Email Error] All SMTP connection attempts failed for {recipient_email}: {e3}", flush=True)
        return False


def _send_email_safe(subject, recipient_email, text_content, html_content, async_send=True):
    """Fail-safe email sender — dispatches asynchronously in background thread"""
    if async_send:
        t = threading.Thread(
            target=_send_worker,
            args=(subject, recipient_email, text_content, html_content),
            daemon=True
        )
        t.start()
        return True
    else:
        return _send_worker(subject, recipient_email, text_content, html_content)


def send_account_confirmation_email(user, base_url=None):
    """Sent to new user immediately after registration — contains token verification link"""
    if isinstance(user, str):
        # Fallback if email string was passed instead of User instance
        from accounts.models import User
        try:
            user = User.objects.get(email=user)
        except User.DoesNotExist:
            return False

    user_email = user.email
    user_name = user.display_name
    verification_url = generate_verification_url(user, base_url=base_url)

    # Print verification URL directly to console for instant local development & testing
    print(f"\n=======================================================", flush=True)
    print(f"[VERIFICATION EMAIL LINK FOR {user_email}]", flush=True)
    print(f"URL: {verification_url}", flush=True)
    print(f"=======================================================\n", flush=True)

    subject = "Confirm Your Chrysalias Account"

    text_content = f"""
Hello {user_name},

Your Chrysalias.com account has been created successfully.

Please click the link below to verify your email address and activate your account:
{verification_url}

If you did not create this account, please contact us at info@chrysalias.com.

Best regards,
The Chrysalias Team
"""

    html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px;">
  {EMAIL_HEADER_HTML}
  <div style="padding: 32px 24px; background: #ffffff;">
    <h2 style="color: #002b49; font-size: 1.35rem; margin-top: 0;">Confirm Your Email Address</h2>
    <p style="font-size: 0.95rem; line-height: 1.6; color: #334155;">
      Hello <strong>{user_name}</strong>,<br><br>
      Welcome to <strong>Chrysalias.com</strong>! Please confirm your email address to complete your account setup and access payment protection features.
    </p>
    <div style="text-align: center; margin: 28px 0;">
      <a href="{verification_url}" style="background-color: #3cb95d; color: #ffffff; padding: 14px 36px; text-decoration: none; font-weight: 700; border-radius: 6px; display: inline-block; font-size: 1rem; box-shadow: 0 4px 12px rgba(60,185,93,0.3);">
        Verify Email Address
      </a>
    </div>
    <p style="font-size: 0.85rem; color: #64748b; line-height: 1.4; text-align: center;">
      Or copy and paste this link into your browser:<br>
      <a href="{verification_url}" style="color: #01426a; word-break: break-all;">{verification_url}</a>
    </p>
    <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 24px; text-align: center;">
      If you did not create this account, please contact <a href="mailto:info@chrysalias.com" style="color: #01426a;">info@chrysalias.com</a>.
    </p>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    return _send_email_safe(subject, user_email, text_content, html_content, async_send=True)


def send_welcome_email(user_email, user_name):
    """Legacy welcome email — kept for compatibility"""
    return send_account_confirmation_email(user_email, user_name)


def send_new_transaction_email(user_email, user_name, tx_data):
    """Sent to primary creator when a new transaction is created"""
    tx_id       = tx_data.get('id', 'ESC-NEW')
    tx_title    = tx_data.get('title', 'Protected Agreement')
    total_amt   = float(tx_data.get('amount', tx_data.get('price', 0.0)))
    role        = tx_data.get('role', 'Buyer').capitalize()
    inspection  = tx_data.get('inspectionPeriod', 2)
    category    = tx_data.get('category', 'Domain Names')

    is_partnered = bool(tx_data.get('isPartneredPayment', False))
    my_contrib   = float(tx_data.get('myContribution', total_amt / 2 if is_partnered else total_amt))
    pt_contrib   = float(tx_data.get('partnerContribution', total_amt - my_contrib if is_partnered else 0.0))
    partner_email = tx_data.get('partnerEmail', '')

    subject = f"Transaction Created: {tx_title} ({tx_id}) — Chrysalias.com"

    contrib_rows_text = ""
    contrib_rows_html = ""
    if is_partnered:
        contrib_rows_text = f"""- My Agreed Contribution: ${my_contrib:,.2f} USD
- Partner Contribution ({partner_email}): ${pt_contrib:,.2f} USD"""
        contrib_rows_html = f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 10px 0; color: #475569; font-weight: 600;">My Agreed Contribution:</td>
          <td style="padding: 10px 0; text-align: right; font-weight: 800; color: #002b49;">${my_contrib:,.2f} USD</td>
        </tr>
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 10px 0; color: #475569; font-weight: 600;">Partner Contribution ({partner_email}):</td>
          <td style="padding: 10px 0; text-align: right; font-weight: 800; color: #166534;">${pt_contrib:,.2f} USD</td>
        </tr>
"""

    text_content = f"""
Hello {user_name},

Your transaction '{tx_title}' ({tx_id}) has been created successfully on Chrysalias.com.

Transaction Summary:
- Reference ID: {tx_id}
- Item / Agreement: {tx_title} ({category})
- Total Agreement Amount: ${total_amt:,.2f} USD
{contrib_rows_text}
- My Role: {role}
- Inspection Period: {inspection} Days

Manage your deal and complete payment:
https://chrysalias.com/dashboard.html

Best regards,
The Chrysalias Payment Protection Team
"""

    html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, -apple-system, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.04);">
  {EMAIL_HEADER_HTML}
  <div style="padding: 36px 28px; background: #ffffff;">
    <div style="margin-bottom: 14px;">
      <span style="background: #e0f2fe; color: #0369a1; font-size: 0.72rem; font-weight: 800; padding: 5px 12px; border-radius: 12px; letter-spacing: 0.05em; text-transform: uppercase;">TRANSACTION CREATED</span>
    </div>
    <h2 style="color: #002b49; font-size: 1.35rem; font-weight: 800; margin: 0 0 6px 0; letter-spacing: -0.3px;">{tx_title}</h2>
    <p style="color: #64748b; font-size: 0.86rem; margin: 0 0 22px 0;">Reference ID: <strong style="color: #002b49;">{tx_id}</strong></p>

    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; margin-bottom: 24px;">
      <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem;">
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 10px 0; color: #475569; font-weight: 600;">Category / Type:</td>
          <td style="padding: 10px 0; text-align: right; font-weight: 700; color: #002b49;">{category}</td>
        </tr>
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 10px 0; color: #475569; font-weight: 600;">Total Agreement Price:</td>
          <td style="padding: 10px 0; text-align: right; font-weight: 900; color: #002b49; font-size: 1.05rem;">${total_amt:,.2f} USD</td>
        </tr>
        {contrib_rows_html}
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 10px 0; color: #475569; font-weight: 600;">Your Role:</td>
          <td style="padding: 10px 0; text-align: right; font-weight: 700; color: #002b49;">{role}</td>
        </tr>
        <tr>
          <td style="padding: 10px 0; color: #475569; font-weight: 600;">Inspection Period:</td>
          <td style="padding: 10px 0; text-align: right; font-weight: 700; color: #002b49;">{inspection} Days</td>
        </tr>
      </table>
    </div>

    <div style="background: #eff6ff; border-left: 4px solid #002b49; padding: 14px 16px; border-radius: 6px; font-size: 0.85rem; color: #1e3a8a; margin-bottom: 24px;">
      <strong>Next Step:</strong> You can view this deal and complete your contribution payment of <strong>${my_contrib:,.2f} USD</strong> directly from your Chrysalias dashboard.
    </div>

    <div style="text-align: center; margin-top: 28px;">
      <a href="https://chrysalias.com/dashboard.html" style="background-color: #002b49; color: #ffffff; padding: 14px 36px; text-decoration: none; font-weight: 800; border-radius: 8px; display: inline-block; font-size: 0.95rem; box-shadow: 0 4px 14px rgba(0,43,73,0.25);">
        Open Dashboard & Complete Payment
      </a>
    </div>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    return _send_email_safe(subject, user_email, text_content, html_content)


def send_partnered_payment_invitation(partner_email, initiator_name, tx_data, partner_link=""):
    """Sent to joint/co-funding partner when a co-funded payment transaction is initiated"""
    tx_id        = tx_data.get('id', 'ESC-PARTNER')
    tx_title     = tx_data.get('title', 'Co-Funding Item')
    total_amt    = float(tx_data.get('amount', tx_data.get('price', 0.0)))
    category     = tx_data.get('category', 'General Merchandise')
    inspection   = tx_data.get('inspectionPeriod', 2)

    my_contrib   = float(tx_data.get('myContribution', total_amt / 2))
    pt_contrib   = float(tx_data.get('partnerContribution', total_amt - my_contrib))

    if not partner_link:
        partner_link = f"https://chrysalias.com/checkout.html?tx_id={tx_id}&role=partner"

    subject = f"Co-Funded Payment Request from {initiator_name} ({tx_id}) — Chrysalias.com"

    text_content = f"""
Hello,

{initiator_name} has created a Co-Funded Payment agreement for '{tx_title}' on Chrysalias.com and designated you as the co-funding partner.

Deal Details:
- Reference ID: {tx_id}
- Item / Agreement: {tx_title} ({category})
- Total Agreement Amount: ${total_amt:,.2f} USD
- Your Agreed Contribution: ${pt_contrib:,.2f} USD
- {initiator_name}'s Contribution: ${my_contrib:,.2f} USD
- Inspection Period: {inspection} Days

Please click the link below to review and pay your contribution of ${pt_contrib:,.2f} USD:
{partner_link}

Best regards,
The Chrysalias Joint Payments Team
https://chrysalias.com
"""

    html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, -apple-system, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.04);">
  {EMAIL_HEADER_HTML}
  <div style="padding: 36px 28px; background: #ffffff;">
    <div style="margin-bottom: 14px;">
      <span style="background: #dcfce7; color: #166534; font-size: 0.72rem; font-weight: 800; padding: 5px 12px; border-radius: 12px; letter-spacing: 0.05em; text-transform: uppercase;">CO-FUNDED PAYMENT INVITATION</span>
    </div>
    <h2 style="color: #002b49; font-size: 1.35rem; font-weight: 800; margin: 0 0 6px 0; letter-spacing: -0.3px;">
      {initiator_name} Invited You to Co-Fund an Agreement
    </h2>
    <p style="color: #475569; font-size: 0.92rem; line-height: 1.6; margin-top: 0;">
      A co-funded payment transaction has been created for <strong>{tx_title}</strong> (Ref: <strong style="color: #002b49;">{tx_id}</strong>) by <strong>{initiator_name}</strong>.
    </p>

    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; margin: 22px 0;">
      <div style="font-size: 0.84rem; font-weight: 800; color: #002b49; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.04em;">Financial & Deal Breakdown</div>
      <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem;">
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 9px 0; color: #475569; font-weight: 600;">Item / Agreement:</td>
          <td style="padding: 9px 0; text-align: right; font-weight: 700; color: #002b49;">{tx_title}</td>
        </tr>
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 9px 0; color: #475569; font-weight: 600;">Category:</td>
          <td style="padding: 9px 0; text-align: right; font-weight: 700; color: #002b49;">{category}</td>
        </tr>
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 9px 0; color: #475569; font-weight: 600;">Total Agreement Price:</td>
          <td style="padding: 9px 0; text-align: right; font-weight: 900; color: #002b49; font-size: 1.05rem;">${total_amt:,.2f} USD</td>
        </tr>
        <tr style="border-bottom: 1px solid #bbf7d0; background: #f0fdf4;">
          <td style="padding: 10px 8px; color: #166534; font-weight: 800;">Your Agreed Contribution:</td>
          <td style="padding: 10px 8px; text-align: right; font-weight: 900; color: #166534; font-size: 1.05rem;">${pt_contrib:,.2f} USD</td>
        </tr>
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 9px 0; color: #475569; font-weight: 600;">{initiator_name}'s Contribution:</td>
          <td style="padding: 9px 0; text-align: right; font-weight: 700; color: #002b49;">${my_contrib:,.2f} USD</td>
        </tr>
        <tr>
          <td style="padding: 9px 0; color: #475569; font-weight: 600;">Inspection Period:</td>
          <td style="padding: 9px 0; text-align: right; font-weight: 700; color: #002b49;">{inspection} Days</td>
        </tr>
      </table>
    </div>

    <div style="background: #f0fdf4; border-left: 4px solid #3cb95d; padding: 14px 16px; border-radius: 6px; font-size: 0.86rem; color: #166534; margin-bottom: 24px;">
      <strong>Action Required:</strong> Click below to review this agreement and pay your contribution of <strong>${pt_contrib:,.2f} USD</strong> securely via Chrysalias.
    </div>

    <div style="text-align: center; margin-top: 28px;">
      <a href="{partner_link}" style="background-color: #3cb95d; color: #ffffff; padding: 14px 36px; text-decoration: none; font-weight: 800; border-radius: 8px; display: inline-block; font-size: 0.98rem; box-shadow: 0 4px 14px rgba(60,185,93,0.3);">
        Pay Your Contribution (${pt_contrib:,.2f} USD)
      </a>
    </div>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    return _send_email_safe(subject, partner_email, text_content, html_content)


def send_payment_confirmation_email(user_email, user_name, tx_data, amount_paid):
    """4. Sent when user makes a payment / uploads receipt"""
    tx_id = tx_data.get('id', 'ESC-PAY')
    tx_title = tx_data.get('title', 'Protected Item')

    subject = f"Payment Received for {tx_id} — Pending Seller Confirmation"

    text_content = f"""
Hello {user_name},

We have received your payment submission of ${amount_paid:,.2f} USD for transaction '{tx_title}' ({tx_id}).

Your payment is safely held in Chrysalias protection. The next step is for the seller to verify and confirm the transaction to initiate delivery/transfer.

Transaction ID: {tx_id}
Amount Paid: ${amount_paid:,.2f} USD

Best regards,
Chrysalias Payment Protection Team
"""

    html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px;">
  {EMAIL_HEADER_HTML}
  <div style="padding: 32px 24px; background: #ffffff;">
    <span style="background: #dcfce7; color: #166534; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 12px;">PAYMENT SUBMITTED</span>
    <h2 style="color: #002b49; font-size: 1.3rem; margin: 12px 0 6px 0;">Payment Received (${amount_paid:,.2f} USD)</h2>
    <p style="color: #475569; font-size: 0.92rem; line-height: 1.5; margin-top: 0;">
      Your payment for <strong>{tx_title}</strong> (Ref: {tx_id}) has been submitted and secured in Chrysalias protection.
    </p>

    <div style="background: #fef3c7; border: 1px solid #fde68a; border-radius: 8px; padding: 16px; margin: 20px 0; color: #92400e;">
      <strong>⏳ Next Step: Seller Confirmation</strong>
      <p style="margin: 4px 0 0 0; font-size: 0.86rem;">
        Your funds are safely protected. What is left is for the seller to confirm and execute delivery, after which your transaction will be completed.
      </p>
    </div>

    <div style="text-align: center; margin-top: 24px;">
      <a href="https://chrysalias.com/dashboard.html" style="background-color: #002b49; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: 700; border-radius: 6px; display: inline-block;">
        Track Status in Dashboard
      </a>
    </div>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    return _send_email_safe(subject, user_email, text_content, html_content)


def send_joint_partner_notification_email(partner_email, primary_name, partner_name="Partner"):
    """Sent to joint account partner informing them that a joint account has been set up with them"""
    subject = f"Joint Account Partner Invitation — Chrysalias.com"

    text_content = f"""
Hello {partner_name},

{primary_name} has created a Joint Account on Chrysalias.com and designated you ({partner_email}) as their official Joint Account Partner.

As a Joint Partner on Chrysalias.com, you can:
- Co-manage protected payment agreements with {primary_name}
- Contribute custom-agreed funding amounts directly to transactions
- Track transaction status, verification, and payment protection in real-time

Access your Chrysalias Joint Portal at:
https://chrysalias.com/login.html

Note: No email verification is required from you. Your partner ({primary_name}) has initiated the joint account setup.

Best regards,
The Chrysalias Joint Accounts Team
https://chrysalias.com
"""

    html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, -apple-system, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.04);">
  {EMAIL_HEADER_HTML}
  <div style="padding: 36px 28px; background: #ffffff;">
    <div style="margin-bottom: 16px;">
      <span style="background: #e0f2fe; color: #0369a1; font-size: 0.72rem; font-weight: 800; padding: 5px 12px; border-radius: 12px; letter-spacing: 0.05em; text-transform: uppercase;">JOINT PARTNER INVITATION</span>
    </div>
    <h2 style="color: #002b49; font-size: 1.4rem; font-weight: 800; margin: 0 0 10px 0; letter-spacing: -0.3px;">
      You Have Been Added as a Joint Account Partner
    </h2>
    <p style="color: #475569; font-size: 0.93rem; line-height: 1.6; margin-top: 0;">
      Hello <strong>{partner_name}</strong>,<br><br>
      <strong>{primary_name}</strong> has registered a Joint Account on <strong>Chrysalias.com</strong> and designated your email address (<strong>{partner_email}</strong>) as their official Joint Account Partner.
    </p>

    <div style="background: linear-gradient(135deg, #f0fdf4 0%, #eff6ff 100%); border: 1px solid #bbf7d0; border-radius: 10px; padding: 20px; margin: 24px 0;">
      <div style="font-size: 0.88rem; font-weight: 800; color: #166534; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        As a Joint Account Partner, you can:
      </div>
      <ul style="margin: 0; padding-left: 20px; font-size: 0.86rem; color: #1e3a8a; line-height: 1.6;">
        <li style="margin-bottom: 6px;">Co-manage protected payment agreements with <strong>{primary_name}</strong></li>
        <li style="margin-bottom: 6px;">Contribute custom-agreed funding portions directly via secure payment portals</li>
        <li>Monitor deal progress, admin receipt verification, and payment protection in real-time</li>
      </ul>
    </div>

    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; font-size: 0.82rem; color: #64748b; margin-bottom: 24px;">
      <strong style="color: #002b49;">Note:</strong> No email verification step is required on your part. Your partner (<strong>{primary_name}</strong>) has initiated the account registration and receives the account verification email.
    </div>

    <div style="text-align: center; margin-top: 28px;">
      <a href="https://chrysalias.com/login.html" style="background-color: #002b49; color: #ffffff; padding: 14px 36px; text-decoration: none; font-weight: 800; border-radius: 8px; display: inline-block; font-size: 0.95rem; box-shadow: 0 4px 14px rgba(0,43,73,0.25);">
        Sign In to Chrysalias Joint Portal
      </a>
    </div>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    return _send_email_safe(subject, partner_email, text_content, html_content)


def send_receipt_submitted_email(user_email, user_name, tx_id, amount_paid):
    """Sent when user uploads a payment receipt — pending admin verification"""
    subject = f"Payment Receipt Submitted ({tx_id}) — Pending Verification"

    text_content = f"""
Hello {user_name},

Your payment receipt of ${amount_paid:,.2f} USD for transaction '{tx_id}' has been uploaded successfully.

Status: Pending Admin Verification
Our compliance team is verifying your payment submission. You will receive a confirmation email once verified.

Track status: https://chrysalias.com/dashboard.html

Best regards,
Chrysalias Verification Team
"""

    html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px;">
  {EMAIL_HEADER_HTML}
  <div style="padding: 32px 24px; background: #ffffff;">
    <span style="background: #fef3c7; color: #92400e; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 12px;">RECEIPT SUBMITTED — PENDING VERIFICATION</span>
    <h2 style="color: #002b49; font-size: 1.3rem; margin: 12px 0 6px 0;">Payment Receipt Received (${amount_paid:,.2f} USD)</h2>
    <p style="color: #475569; font-size: 0.92rem; line-height: 1.5; margin-top: 0;">
      Hello <strong>{user_name}</strong>, your payment receipt for transaction <strong>{tx_id}</strong> has been uploaded and is undergoing verification by our team.
    </p>
    <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 16px; margin: 20px 0; color: #92400e;">
      <strong>⏳ What Happens Next?</strong>
      <p style="margin: 4px 0 0 0; font-size: 0.86rem;">
        Once our compliance admin verifies the transaction receipt, your payment status will update to <strong>Payment Confirmed / Active</strong>.
      </p>
    </div>
    <div style="text-align: center; margin-top: 24px;">
      <a href="https://chrysalias.com/dashboard.html" style="background-color: #002b49; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: 700; border-radius: 6px; display: inline-block;">
        Track Status in Dashboard
      </a>
    </div>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    return _send_email_safe(subject, user_email, text_content, html_content)


def send_payment_verified_email(user_email, user_name, tx_id, amount_paid):
    """Sent when Admin confirms payment receipt in Django Admin"""
    subject = f"Payment Confirmed & Verified ({tx_id}) — Chrysalias Protection"

    text_content = f"""
Hello {user_name},

Great news! Your payment of ${amount_paid:,.2f} USD for transaction '{tx_id}' has been verified and confirmed by Chrysalias Admin.

Status: Payment Confirmed / Protected
Your funds are safely held in Chrysalias protection.

View transaction: https://chrysalias.com/dashboard.html

Best regards,
Chrysalias Payment Protection
"""

    html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px;">
  {EMAIL_HEADER_HTML}
  <div style="padding: 32px 24px; background: #ffffff;">
    <span style="background: #dcfce7; color: #166534; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 12px;">PAYMENT VERIFIED & CONFIRMED</span>
    <h2 style="color: #002b49; font-size: 1.3rem; margin: 12px 0 6px 0;">Payment Verified (${amount_paid:,.2f} USD)</h2>
    <p style="color: #475569; font-size: 0.92rem; line-height: 1.5; margin-top: 0;">
      Hello <strong>{user_name}</strong>, your payment for transaction <strong>{tx_id}</strong> has been officially verified and confirmed by Chrysalias Administration.
    </p>
    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; margin: 20px 0; color: #166534;">
      <strong>✓ Payment Active & Secured</strong>
      <p style="margin: 4px 0 0 0; font-size: 0.86rem;">
        Your transaction is active and protected under Chrysalias payment policies.
      </p>
    </div>
    <div style="text-align: center; margin-top: 24px;">
      <a href="https://chrysalias.com/dashboard.html" style="background-color: #3cb95d; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: 700; border-radius: 6px; display: inline-block;">
        View Transaction in Dashboard
      </a>
    </div>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    return _send_email_safe(subject, user_email, text_content, html_content)


def send_joint_partner_paid_email(recipient_email, recipient_name, payer_name, tx_id, tx_title, amount_paid, remaining_amount, both_paid=False, checkout_url=None):
    """
    Sent to a joint partner when their co-funding partner submits a payment or uploads a receipt.
    Informs recipient of partner's payment and what is outstanding on their end.
    """
    if both_paid:
        subject = f"Joint Payment Complete for {tx_id} — Both Partners Have Paid"
    else:
        subject = f"Joint Payment Update ({tx_id}) — {payer_name} Paid Their Share"

    if not checkout_url:
        checkout_url = f"https://chrysalias.com/checkout.html?tx_id={tx_id}"

    if both_paid:
        text_content = f"""
Hello {recipient_name},

Great news! {payer_name} has paid their share of ${amount_paid:,.2f} USD for transaction '{tx_title}' ({tx_id}).

Both partner shares (100% total) are now paid and submitted. The transaction is pending final Chrysalias admin verification.

View status: https://chrysalias.com/dashboard.html

Best regards,
Chrysalias Joint Payment Service
"""
        html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px;">
  {EMAIL_HEADER_HTML}
  <div style="padding: 32px 24px; background: #ffffff;">
    <span style="background: #dcfce7; color: #166534; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 12px;">BOTH SHARES PAID</span>
    <h2 style="color: #002b49; font-size: 1.3rem; margin: 12px 0 6px 0;">{payer_name} Paid — Joint Funding Complete</h2>
    <p style="color: #475569; font-size: 0.92rem; line-height: 1.5; margin-top: 0;">
      Hello <strong>{recipient_name}</strong>, <strong>{payer_name}</strong> has successfully submitted their agreed contribution of <strong>${amount_paid:,.2f} USD</strong> for transaction <strong>{tx_title}</strong> ({tx_id}).
    </p>
    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; margin: 20px 0; color: #166534;">
      <strong>All Partner Contributions Received</strong>
      <p style="margin: 4px 0 0 0; font-size: 0.86rem;">
        100% of the joint payment is submitted. Our admin team will verify the payment receipts and activate your Chrysalias protection.
      </p>
    </div>
    <div style="text-align: center; margin-top: 24px;">
      <a href="https://chrysalias.com/dashboard.html" style="background-color: #3cb95d; color: #ffffff; padding: 12px 28px; text-decoration: none; font-weight: 700; border-radius: 6px; display: inline-block;">
        Track Status in Dashboard
      </a>
    </div>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    else:
        text_content = f"""
Hello {recipient_name},

{payer_name} has successfully submitted their contribution of ${amount_paid:,.2f} USD for co-funded transaction '{tx_title}' ({tx_id}).

Your share of ${remaining_amount:,.2f} USD is still remaining.

Complete your payment here: {checkout_url}

Best regards,
Chrysalias Joint Payment Service
"""
        html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px;">
  {EMAIL_HEADER_HTML}
  <div style="padding: 32px 24px; background: #ffffff;">
    <span style="background: #e0f2fe; color: #075985; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 12px;">JOINT PAYMENT UPDATE</span>
    <h2 style="color: #002b49; font-size: 1.3rem; margin: 12px 0 6px 0;">{payer_name} Paid Their Share (${amount_paid:,.2f} USD)</h2>
    <p style="color: #475569; font-size: 0.92rem; line-height: 1.5; margin-top: 0;">
      Hello <strong>{recipient_name}</strong>, your partner <strong>{payer_name}</strong> has submitted their share for joint agreement <strong>{tx_title}</strong> ({tx_id}).
    </p>

    <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 16px; margin: 20px 0; color: #92400e;">
      <strong>Action Required: Pay Your Remaining Share (${remaining_amount:,.2f} USD)</strong>
      <p style="margin: 4px 0 0 0; font-size: 0.86rem;">
        Your share of <strong>${remaining_amount:,.2f} USD</strong> is currently outstanding. Click below to pay your portion and activate Chrysalias protection.
      </p>
    </div>

    <div style="text-align: center; margin-top: 24px;">
      <a href="{checkout_url}" style="background-color: #3cb95d; color: #ffffff; padding: 12px 32px; text-decoration: none; font-weight: 700; border-radius: 6px; display: inline-block;">
        Pay Your Share (${remaining_amount:,.2f} USD)
      </a>
    </div>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    return _send_email_safe(subject, recipient_email, text_content, html_content)


def send_joint_partner_notification_email(partner_email, primary_name, partner_name='Partner'):
    """
    Dispatched when a Joint Account is created on Chrysalias.com.
    Sends an official, professional notification email to the partner letting them know
    a co-managed Joint Account has been created on the website.
    """
    if not partner_email:
        return False

    subject = f"Joint Account Established by {primary_name} — Chrysalias.com"

    text_content = f"""
Hello {partner_name},

{primary_name} has registered a co-managed Joint Account on Chrysalias.com and designated you as their official Joint Account Partner ({partner_email}).

With Chrysalias Joint Account features, both account holders can co-manage protected payment agreements, view side-by-side contribution breakdowns (Amount To Be Paid, Amount Paid, and Pending Balance), and fund agreed settlement shares.

To sign in or access your co-managed account, visit:
https://chrysalias.com/login.html

If you have any questions, contact our support team at info@chrysalias.com.

Best regards,
The Chrysalias Team
"""

    html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, -apple-system, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 4px 14px rgba(0,0,0,0.03); overflow: hidden;">
  {EMAIL_HEADER_HTML}
  <div style="padding: 32px 24px; background: #ffffff;">
    <div style="display: inline-block; background: #dcfce7; color: #166534; font-size: 0.75rem; font-weight: 800; padding: 4px 12px; border-radius: 12px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 14px;">
      Joint Account Co-Management
    </div>

    <h2 style="color: #002b49; font-size: 1.35rem; margin-top: 0; margin-bottom: 12px; font-weight: 800;">Co-Managed Joint Account Established</h2>
    
    <p style="font-size: 0.95rem; line-height: 1.6; color: #334155; margin-bottom: 20px;">
      Hello <strong>{partner_name}</strong>,<br><br>
      <strong>{primary_name}</strong> has registered a co-managed Joint Account on <strong>Chrysalias.com</strong> and designated you as their official Joint Account Partner.
    </p>

    <div style="background: #f8fafc; border: 1.5px solid #e2e8f0; border-left: 4px solid #002b49; border-radius: 8px; padding: 20px; margin: 24px 0;">
      <div style="font-size: 0.9rem; font-weight: 800; color: #002b49; margin-bottom: 10px;">Co-Managed Features Included:</div>
      <ul style="margin: 0; padding-left: 20px; font-size: 0.86rem; color: #475569; line-height: 1.65;">
        <li>Co-funded payment agreements &amp; custom party split tracking</li>
        <li>Dual-pillar financial summary (Amount To Be Paid, Amount Paid &amp; Pending Balance)</li>
        <li>Direct Chrysalias payment protection portal access</li>
      </ul>
    </div>

    <div style="text-align: center; margin: 28px 0;">
      <a href="https://chrysalias.com/login.html" style="background-color: #002b49; color: #ffffff; padding: 14px 36px; text-decoration: none; font-weight: 800; border-radius: 6px; display: inline-block; font-size: 0.95rem; box-shadow: 0 4px 12px rgba(0,43,73,0.25);">
        Sign In to Chrysalias Account
      </a>
    </div>

    <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 24px; text-align: center; line-height: 1.4;">
      If you have questions regarding this joint account, please contact our support team at <a href="mailto:info@chrysalias.com" style="color: #01426a; font-weight: 600;">info@chrysalias.com</a>.
    </p>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    return _send_email_safe(subject, partner_email, text_content, html_content, async_send=True)
