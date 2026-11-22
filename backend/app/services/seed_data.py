import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from backend.app.models.customer import Customer
from backend.app.models.product import Product
from backend.app.models.order import OrderHistory


def seed_database(db: Session) -> None:
    """Seed the database with sample customers, products, and order history."""

    # 1. Seed Products if empty
    if db.query(Product).count() == 0:
        products = [
            Product(
                id="PROD-001",
                sku="KB-MECH-RGB",
                name="Pro Mechanical RGB Gaming Keyboard",
                description="Tactile mechanical switches with per-key RGB backlighting.",
                price=Decimal("99.99"),
                stock_quantity=45,
                substitute_sku="KB-ERG-WRL",
                category="Peripherals",
                is_active=True,
            ),
            Product(
                id="PROD-002",
                sku="KB-ERG-WRL",
                name="Ergonomic Split Wireless Keyboard",
                description="Cushioned palm rest and split layout for natural posture.",
                price=Decimal("89.99"),
                stock_quantity=30,
                substitute_sku="KB-MECH-RGB",
                category="Peripherals",
                is_active=True,
            ),
            Product(
                id="PROD-003",
                sku="MON-4K-27",
                name="Ultra HD 27-inch 4K Designer Monitor",
                description="IPS panel, 99% sRGB color accuracy, USB-C 65W power delivery.",
                price=Decimal("349.99"),
                stock_quantity=18,
                substitute_sku="MON-CRV-32",
                category="Displays",
                is_active=True,
            ),
            Product(
                id="PROD-004",
                sku="MON-CRV-32",
                name="Curved 32-inch 165Hz Ultrawide Monitor",
                description="Immersive 1500R curvature with high refresh rate gaming display.",
                price=Decimal("399.99"),
                stock_quantity=0,  # Zero stock to test substitute recommendations & backorders!
                substitute_sku="MON-4K-27",
                category="Displays",
                is_active=True,
            ),
            Product(
                id="PROD-005",
                sku="HUB-USBC-8P",
                name="8-in-1 Aluminium USB-C Multiport Hub",
                description="Dual 4K HDMI, Gigabit Ethernet, 100W PD pass-through.",
                price=Decimal("49.99"),
                stock_quantity=120,
                substitute_sku=None,
                category="Accessories",
                is_active=True,
            ),
            Product(
                id="PROD-006",
                sku="AUD-NC-HD7",
                name="Audiophile Noise-Cancelling Wireless Headphones",
                description="Hybrid active noise cancellation with 40-hour battery life.",
                price=Decimal("199.99"),
                stock_quantity=4,  # Low stock
                substitute_sku=None,
                category="Audio",
                is_active=True,
            ),
        ]
        db.add_all(products)
        db.commit()

    # 2. Seed Customers if empty
    if db.query(Customer).count() == 0:
        customers = [
            Customer(
                id="CUST-001",
                name="John Verified",
                email="john.verified@example.com",
                phone="+1-555-0101",
                address="742 Evergreen Terrace, Springfield, OR 97477, USA",
                billing_address="742 Evergreen Terrace, Springfield, OR 97477, USA",
                status="ACTIVE",
            ),
            Customer(
                id="CUST-002",
                name="Sarah Flagged",
                email="sarah.flagged@example.com",
                phone="+1-555-0102",
                address="1200 Market Street, San Francisco, CA 94102, USA",
                billing_address="450 Lexington Ave, New York, NY 10017, USA",  # Billing address mismatch
                status="FLAGGED",
            ),
            Customer(
                id="CUST-003",
                name="Alex Risky",
                email="alex.risky99@disposablemail.org",
                phone="+1-555-0199",
                address="PO Box 9999, Unknown Island, FL 33040, USA",
                billing_address="PO Box 111, Anchorage, AK 99501, USA",
                status="FLAGGED",
            ),
            Customer(
                id="CUST-004",
                name="Emma Newcomer",
                email="emma.new@university.edu",
                phone="+1-555-0104",
                address="100 University Ave, Cambridge, MA 02138, USA",
                billing_address="100 University Ave, Cambridge, MA 02138, USA",
                status="ACTIVE",
            ),
        ]
        db.add_all(customers)
        db.commit()

    # 3. Seed Order History for Customers if empty
    if db.query(OrderHistory).count() == 0:
        history_records = [
            # CUST-001: Model Good Customer (high volume, 0 suspicious, clean record)
            OrderHistory(
                id="HIST-001",
                customer_id="CUST-001",
                order_id="ORD-PAST-101",
                status="DELIVERED",
                amount=Decimal("120.50"),
                is_suspicious=False,
                failed_payment_attempts=0,
                notes="Delivered on time, standard ground.",
                created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=120),
            ),
            OrderHistory(
                id="HIST-002",
                customer_id="CUST-001",
                order_id="ORD-PAST-102",
                status="DELIVERED",
                amount=Decimal("89.99"),
                is_suspicious=False,
                failed_payment_attempts=0,
                notes="Delivered without incident.",
                created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90),
            ),
            OrderHistory(
                id="HIST-003",
                customer_id="CUST-001",
                order_id="ORD-PAST-103",
                status="DELIVERED",
                amount=Decimal("245.00"),
                is_suspicious=False,
                failed_payment_attempts=0,
                notes="Express delivery, repeat customer.",
                created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=35),
            ),
            OrderHistory(
                id="HIST-004",
                customer_id="CUST-001",
                order_id="ORD-PAST-104",
                status="DELIVERED",
                amount=Decimal("150.00"),
                is_suspicious=False,
                failed_payment_attempts=0,
                notes="Standard ground.",
                created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10),
            ),

            # CUST-002: Medium Risk Customer (1 suspicious dispute / chargeback)
            OrderHistory(
                id="HIST-005",
                customer_id="CUST-002",
                order_id="ORD-PAST-201",
                status="DELIVERED",
                amount=Decimal("75.00"),
                is_suspicious=False,
                failed_payment_attempts=0,
                notes="Normal first purchase.",
                created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=60),
            ),
            OrderHistory(
                id="HIST-006",
                customer_id="CUST-002",
                order_id="ORD-PAST-202",
                status="CHARGEBACK",
                amount=Decimal("380.00"),
                is_suspicious=True,
                failed_payment_attempts=1,
                notes="Customer filed dispute stating card was misused.",
                created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20),
            ),

            # CUST-003: High Risk / Fraud Profile (Multiple suspicious transactions & failed attempts)
            OrderHistory(
                id="HIST-007",
                customer_id="CUST-003",
                order_id="ORD-PAST-301",
                status="SUSPICIOUS",
                amount=Decimal("890.00"),
                is_suspicious=True,
                failed_payment_attempts=3,
                notes="Rapid card retries with mismatched CVVs.",
                created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14),
            ),
            OrderHistory(
                id="HIST-008",
                customer_id="CUST-003",
                order_id="ORD-PAST-302",
                status="CHARGEBACK",
                amount=Decimal("1250.00"),
                is_suspicious=True,
                failed_payment_attempts=2,
                notes="Bank confirmed fraudulent stolen card transaction.",
                created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5),
            ),

            # CUST-004: Brand New Customer (0 past orders)
        ]
        db.add_all(history_records)
        db.commit()
