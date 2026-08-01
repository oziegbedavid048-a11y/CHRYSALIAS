"""
Chrysalias Data Seeding Script
Populates Superuser, Demo Users, and Initial Transactions in Django DB.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chrysalias.settings')
django.setup()

from accounts.models import User, UserProfile
from transactions.models import Transaction, PartneredPayment, TransactionActivity


def seed():
    print("=== Seeding Chrysalias Database ===")

    # 1. Create Superuser (Admin)
    admin_username = "Chrysalias"
    admin_email = "info@chrysalias.com"
    admin_password = "Chrys@768"

    superuser, created = User.objects.get_or_create(
        username=admin_username,
        defaults={
            'email': admin_email,
            'full_name': "Chrysalias Admin",
            'kyc_status': "level_2",
            'is_verified': True,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
        }
    )
    superuser.set_password(admin_password)
    superuser.email = admin_email
    superuser.is_staff = True
    superuser.is_superuser = True
    superuser.is_active = True
    superuser.save()
    print(f"[OK] Superuser configured: Username '{admin_username}' / Password '{admin_password}'")

    # 2. Create Demo User: Alex Mercer (Seller)
    alex_email = "alex.seller@chrysalias-demo.com"
    if not User.objects.filter(email=alex_email).exists():
        alex = User.objects.create_user(
            username="alexmercer",
            email=alex_email,
            password="Password123!",
            full_name="Alex Mercer",
            phone="+1 (555) 234-5678",
            kyc_status="level_2",
            is_verified=True,
        )
        UserProfile.objects.create(user=alex, country="United States", notes="Primary Demo Seller")
        print(f"[OK] Demo User created: {alex_email}")
    else:
        alex = User.objects.get(email=alex_email)

    # 3. Create Demo User: Sarah Jenkins (Buyer)
    sarah_email = "sarah.buyer@investments.co"
    if not User.objects.filter(email=sarah_email).exists():
        sarah = User.objects.create_user(
            username="sarahbuyer",
            email=sarah_email,
            password="Password123!",
            full_name="Sarah Jenkins",
            phone="+1 (555) 876-5432",
            kyc_status="level_2",
            is_verified=True,
        )
        UserProfile.objects.create(user=sarah, country="United States", notes="Primary Demo Buyer")
        print(f"[OK] Demo User created: {sarah_email}")
    else:
        sarah = User.objects.get(email=sarah_email)

    # 4. Create Initial Transactions
    tx1, created1 = Transaction.objects.get_or_create(
        tx_id="ESC-892401",
        defaults={
            'title': "Premium Domain Transfer (FintechApp.com)",
            'description': "Full transfer of domain name FintechApp.com including ICANN auth code.",
            'seller': alex,
            'buyer': sarah,
            'buyer_email': sarah_email,
            'seller_email': alex_email,
            'initiator_role': "Seller",
            'amount': 15500.00,
            'currency': "USD",
            'category': "Domain Names",
            'inspection_period': 5,
            'status': "Funded",
            'is_partnered': True,
        }
    )
    if created1:
        PartneredPayment.objects.create(
            transaction=tx1,
            partner_email="co-investor@fintech.io",
            split_type="50_50",
            partner_amount=7750.00,
            partner_status="paid"
        )
        TransactionActivity.objects.create(transaction=tx1, action="created", performed_by=alex, notes="Transaction created by Alex Mercer.")
        TransactionActivity.objects.create(transaction=tx1, action="funded", performed_by=sarah, notes="Funds received into Chrysalias Vault.")
        print(f"[OK] Transaction created: {tx1.tx_id}")

    tx2, created2 = Transaction.objects.get_or_create(
        tx_id="ESC-891904",
        defaults={
            'title': "2024 Porsche 911 GT3 (VIN: WP0ZZZ99ZLS88912)",
            'description': "Purchase of 2024 Porsche 911 GT3 with title transfer and physical vehicle delivery inspection.",
            'seller_email': "motorclassics@dealers.com",
            'buyer': sarah,
            'buyer_email': sarah_email,
            'initiator_role': "Buyer",
            'amount': 178000.00,
            'currency': "USD",
            'category': "Motor Vehicles",
            'inspection_period': 3,
            'status': "In Inspection",
            'is_partnered': False,
        }
    )
    if created2:
        TransactionActivity.objects.create(transaction=tx2, action="created", performed_by=sarah, notes="Transaction initiated by Sarah Jenkins.")
        TransactionActivity.objects.create(transaction=tx2, action="inspection_start", notes="Vehicle delivered; 3-day inspection timer started.")
        print(f"[OK] Transaction created: {tx2.tx_id}")

    tx3, created3 = Transaction.objects.get_or_create(
        tx_id="ESC-889021",
        defaults={
            'title': "Bulk Electronics Wholesale Shipment",
            'description': "Pallet shipment of 500 unit refurbished tablets with verified serial numbers.",
            'seller': alex,
            'seller_email': alex_email,
            'buyer_email': "techimports.us@gmail.com",
            'initiator_role': "Seller",
            'amount': 4200.00,
            'currency': "USD",
            'category': "General Merchandise",
            'inspection_period': 7,
            'status': "Completed",
            'is_partnered': False,
        }
    )
    if created3:
        TransactionActivity.objects.create(transaction=tx3, action="created", performed_by=alex)
        TransactionActivity.objects.create(transaction=tx3, action="completed", notes="Buyer inspected and approved. Funds released to seller.")
        print(f"[OK] Transaction created: {tx3.tx_id}")

    print("\n=== Seeding Completed Successfully! ===")


if __name__ == '__main__':
    seed()
