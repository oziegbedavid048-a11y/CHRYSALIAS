import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

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

def _send_email_safe(subject, recipient_email, text_content, html_content):
    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Chrysalias Support <info@chrysalias.com>')
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[recipient_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info(f"Email '{subject}' sent successfully to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        print(f"[Email Error] {str(e)}")
        return False


def send_account_confirmation_email(user_email, user_name):
    """Sent to new user immediately after registration — prompts them to verify"""
    subject = "Confirm Your Chrysalias Account"

    text_content = f"""
Hello {user_name},

Your Chrysalias.com account has been created successfully.

Please note that your account is now active and ready to use. You can sign in immediately at:
https://chrysalias.com/login.html

If you did not create this account, please contact us at info@chrysalias.com.

Best regards,
The Chrysalias Team
"""

    html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px;">
  {EMAIL_HEADER_HTML}
  <div style="padding: 32px 24px; background: #ffffff;">
    <h2 style="color: #002b49; font-size: 1.35rem; margin-top: 0;">Account Created Successfully!</h2>
    <p style="font-size: 0.95rem; line-height: 1.6; color: #334155;">
      Hello <strong>{user_name}</strong>,<br><br>
      Welcome to <strong>Chrysalias.com</strong>! Your account has been created and is ready to use.
    </p>
    <div style="background: #f0fdf4; border-left: 4px solid #3cb95d; padding: 16px; margin: 20px 0; border-radius: 4px;">
      <strong style="color: #166534;">Your account is now active. You can:</strong>
      <ul style="margin: 8px 0 0 0; padding-left: 20px; font-size: 0.88rem; color: #166534;">
        <li>Create and manage secure escrow transactions</li>
        <li>Set up partnered co-funding payments</li>
        <li>Track all your deals in real time</li>
      </ul>
    </div>
    <div style="text-align: center; margin-top: 28px;">
      <a href="https://chrysalias.com/login.html" style="background-color: #3cb95d; color: #ffffff; padding: 12px 32px; text-decoration: none; font-weight: 700; border-radius: 6px; display: inline-block; font-size: 1rem;">
        Sign In to Your Account
      </a>
    </div>
    <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 24px; text-align: center;">
      If you did not create this account, please contact <a href="mailto:info@chrysalias.com" style="color: #01426a;">info@chrysalias.com</a>.
    </p>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    return _send_email_safe(subject, user_email, text_content, html_content)


def send_welcome_email(user_email, user_name):
    """Legacy welcome email — kept for compatibility"""
    return send_account_confirmation_email(user_email, user_name)


def send_new_transaction_email(user_email, user_name, tx_data):
    """2. Sent to user when a new transaction is created"""
    tx_id = tx_data.get('id', 'ESC-NEW')
    tx_title = tx_data.get('title', 'Protected Agreement')
    amount = tx_data.get('amount', 0.0)
    role = tx_data.get('role', 'Buyer')
    inspection = tx_data.get('inspectionPeriod', 2)

    subject = f"Transaction Created ({tx_id}) — Chrysalias.com"
    
    text_content = f"""
Hello {user_name},

Your transaction '{tx_title}' ({tx_id}) has been created successfully.

Transaction Details:
- ID: {tx_id}
- Title: {tx_title}
- Total Amount: ${amount:,.2f} USD
- My Role: {role}
- Inspection Period: {inspection} Days

Manage your deal: https://chrysalias.com/dashboard.html

Best regards,
Chrysalias Payment Protection
"""

    html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px;">
  {EMAIL_HEADER_HTML}
  <div style="padding: 32px 24px; background: #ffffff;">
    <span style="background: #e0f2fe; color: #075985; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 12px;">NEW TRANSACTION</span>
    <h2 style="color: #002b49; font-size: 1.3rem; margin: 10px 0 6px 0;">{tx_title}</h2>
    <p style="color: #64748b; font-size: 0.88rem; margin: 0 0 20px 0;">Transaction Reference: <strong>{tx_id}</strong></p>

    <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
      <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 8px 0; color: #64748b;">Agreed Amount:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: 800; color: #002b49;">${amount:,.2f} USD</td>
        </tr>
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 8px 0; color: #64748b;">Your Role:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: 700; color: #002b49;">{role}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #64748b;">Inspection Period:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: 700; color: #002b49;">{inspection} Days</td>
        </tr>
      </table>
    </div>

    <div style="text-align: center; margin-top: 24px;">
      <a href="https://chrysalias.com/dashboard.html" style="background-color: #002b49; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: 700; border-radius: 6px; display: inline-block;">
        View Transaction in Dashboard
      </a>
    </div>
  </div>
  {EMAIL_FOOTER_HTML}
</div>
"""
    return _send_email_safe(subject, user_email, text_content, html_content)


def send_partnered_payment_invitation(partner_email, initiator_name, tx_data, partner_link=""):
    """3. Sent to partner email when a partnered payment transaction is initiated"""
    tx_id = tx_data.get('id', 'ESC-PARTNER')
    tx_title = tx_data.get('title', 'Co-Funding Item')
    total_amount = tx_data.get('amount', 0.0)
    split_info = tx_data.get('partnerContribution', '50% / 50% Co-Funding Split')

    subject = f"Partnered Payment Request from {initiator_name} ({tx_id})"

    text_content = f"""
Hello,

{initiator_name} has created a Partnered Payment co-funding request for '{tx_title}' on Chrysalias.com.

Deal Details:
- Transaction ID: {tx_id}
- Item / Purpose: {tx_title}
- Total Agreement Amount: ${total_amount:,.2f} USD
- Partner Contribution: {split_info}

Please request the dedicated Chrysalias Partnered Payment link from {initiator_name} or use your link below to complete your co-funding payment:
{partner_link}

Best regards,
Chrysalias Payment Protection
"""

    html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: 'Inter', system-ui, sans-serif; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px;">
  {EMAIL_HEADER_HTML}
  <div style="padding: 32px 24px; background: #ffffff;">
    <span style="background: #002b49; color: #ffffff; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 12px;">PARTNERED CO-FUNDING INVITATION</span>
    <h2 style="color: #002b49; font-size: 1.3rem; margin: 12px 0 6px 0;">{initiator_name} invited you to co-fund a purchase</h2>
    <p style="color: #475569; font-size: 0.92rem; line-height: 1.5; margin-top: 0;">
      A partnered payment request has been set up for <strong>{tx_title}</strong> (Ref: {tx_id}).
    </p>

    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 18px; margin: 20px 0;">
      <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
        <tr style="border-bottom: 1px solid #dcfce7;">
          <td style="padding: 8px 0; color: #166534;">Item / Agreement:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: 800; color: #002b49;">{tx_title}</td>
        </tr>
        <tr style="border-bottom: 1px solid #dcfce7;">
          <td style="padding: 8px 0; color: #166534;">Total Amount:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: 800; color: #002b49;">${total_amount:,.2f} USD</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #166534;">Initiated By:</td>
          <td style="padding: 8px 0; text-align: right; font-weight: 700; color: #002b49;">{initiator_name}</td>
        </tr>
      </table>
    </div>

    <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 4px; font-size: 0.86rem; color: #1e3a8a; margin-bottom: 24px;">
      <strong>Action Required:</strong> Please request the direct Partnered Payment Portal link from <strong>{initiator_name}</strong> to complete your share of the payment safely.
    </div>

    {f'<div style="text-align: center;"><a href="{partner_link}" style="background-color: #3cb95d; color: #ffffff; padding: 12px 28px; text-decoration: none; font-weight: 700; border-radius: 6px; display: inline-block;">Open Partnered Payment Portal</a></div>' if partner_link else ''}
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
