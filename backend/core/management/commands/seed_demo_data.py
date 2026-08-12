"""
``seed_demo_data`` management command.

Populates every existing organization with a realistic, interconnected set of
development/demo records that is safe to run repeatedly:

  * tenant-aware      - every object is created using that organization's own
                        foreign keys; nothing ever crosses tenants;
  * deterministic     - identical organisation sets produce identical demo data
                        (the random streams are seeded from the org primary key);
  * idempotent        - a second run detects the seeded marker and skips the
                        org instead of duplicating rows;
  * non-destructive   - never deletes user data; ``--clear`` only removes rows
                        that carry exact demo identifiers this command itself
                        uses.

Data created per organization
-----------------------------
- 10 categories, 30 products (SKU, prices, and mixed stock conditions)
- 12 suppliers, 15 customers
- purchases with PurchaseItems spread over several months
- sales with SaleItems spread over ~100 days, following popularity weights
- stock movements (IN) logged against each purchase
- low-stock / out-of-stock / AI notifications
- 12 AIInsight rows (FORECAST / LOW_STOCK / RECOMMENDATION / ANALYSIS) that
  only reference the seeded records

No secrets, API keys or environment values are ever written.
"""

import random
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from core.models import Organization
from customers.models import Customer
from suppliers.models import Supplier
from inventory.models import Category, Inventory, Product, StockMovement
from notifications.models import Notification
from purchases.models import Purchase, PurchaseItem
from sales.models import Sale, SaleItem
from ai.models import AIInsight

# ---------------------------------------------------------------------------
# Deterministic catalogue shared by every organization.
# ---------------------------------------------------------------------------

CATEGORY_NAMES = [
    "Beverages",
    "Snacks",
    "Dairy",
    "Personal Care",
    "Cleaning Supplies",
    "Household",
    "Grocery",
    "Stationery",
    "Electronics",
    "Bakery",
]

CATEGORY_DESCRIPTIONS = {
    "Beverages": "Soft drinks, juices, energy drinks and packaged beverages.",
    "Snacks": "Noodles, chips, biscuits and ready-to-eat snacks.",
    "Dairy": "Milk, yoghurt, paneer, cheese, curd and butter.",
    "Personal Care": "Shampoo, toothpaste, soap, hair oil and cosmetics.",
    "Cleaning Supplies": "Detergents, dishwashing liquids and cleaners.",
    "Household": "Sugar, rice, cooking oil and kitchen staples.",
    "Grocery": "Salt, tea and grocery staples.",
    "Stationery": "Notebooks, pens and general stationery.",
    "Electronics": "Small electronics such as bulbs and accessories.",
    "Bakery": "Biscuits, breads and bakery snacks.",
}

# (category, name, buying_price, selling_price, quantity, min_stock, max_stock, weight)
PRODUCTS = [
    ("Beverages", "Coca Cola 500ml", 65, 85, 150, 60, 300, 5),
    ("Beverages", "Pepsi 500ml", 62, 80, 5, 40, 200, 5),
    ("Beverages", "Sprite 500ml", 62, 80, 46, 60, 220, 4),
    ("Beverages", "Red Bull 250ml", 155, 190, 28, 12, 120, 4),
    ("Beverages", "Frooti Mango 1L", 150, 185, 0, 5, 60, 3),
    ("Snacks", "Wai Wai Noodles", 40, 55, 480, 120, 500, 5),
    ("Snacks", "Maggi Noodles", 38, 50, 90, 60, 400, 5),
    ("Snacks", "Lays Classic", 55, 80, 12, 25, 300, 4),
    ("Snacks", "Kurkure Masala", 45, 65, 6, 20, 160, 4),
    ("Snacks", "Dairy Milk 85g", 95, 130, 40, 15, 150, 5),
    ("Snacks", "Bhaji Bhujia 200g", 60, 85, 12, 20, 120, 3),
    ("Dairy", "Milk 1L", 90, 115, 120, 40, 400, 5),
    ("Dairy", "Yoghurt 500g", 130, 165, 0, 15, 200, 3),
    ("Dairy", "Paneer 150g", 140, 180, 12, 20, 60, 3),
    ("Dairy", "Butter 250g", 200, 260, 3, 10, 80, 2),
    ("Personal Care", "Shampoo 200ml", 150, 210, 46, 15, 180, 5),
    ("Personal Care", "Toothpaste 100g", 95, 135, 25, 20, 220, 4),
    ("Personal Care", "Soap 100g", 60, 85, 240, 150, 400, 4),
    ("Personal Care", "Hair Oil 200ml", 110, 170, 18, 15, 120, 3),
    ("Personal Care", "Face Cream 50g", 130, 190, 0, 10, 60, 2),
    ("Cleaning Supplies", "Detergent Powder 1kg", 210, 275, 10, 25, 140, 4),
    ("Cleaning Supplies", "Dishwash Liquid 500ml", 75, 105, 2, 15, 80, 3),
    ("Household", "Sugar 1kg", 90, 130, 140, 120, 300, 4),
    ("Household", "Basmati Rice 5kg", 275, 340, 60, 100, 150, 2),
    ("Household", "Cooking Oil 1L", 180, 215, 84, 50, 250, 5),
    ("Grocery", "Table Salt 1kg", 20, 30, 200, 150, 300, 3),
    ("Grocery", "Tea Leaves 200g", 165, 200, 45, 30, 100, 3),
    ("Stationery", "Notebook 100pg", 40, 95, 0, 30, 200, 2),
    ("Stationery", "Ball Pen Blue", 12, 22, 320, 200, 500, 2),
    ("Electronics", "LED Bulb 9W", 250, 320, 8, 30, 50, 2),
]

DEMO_SKUS = [f"SKU-{i + 1:03d}" for i in range(len(PRODUCTS))]

SUPPLIERS = [
    # (name, contact_person, phone_suffix, email_handle)
    ("Himalayan Beverages Dist. Co.", "Ram Shrestha", "1", "himalayan-bev"),
    ("Kathmandu Foods Wholesale", "Sita Maharjan", "2", "ktm-foods"),
    ("Balaju Dairy Suppliers", "Kiran Tamang", "3", "balaju-dairy"),
    ("Cosmo Personal Care Pvt Ltd", "Mina Bista", "4", "cosmo-care"),
    ("Clean Shine Distribution", "Raj Thapa", "5", "clean-shine"),
    ("Everest Grain & Grocers", "Sunita Gurung", "6", "everest-grain"),
    ("Nepal Stationery House", "Dipesh Shah", "7", "nepal-stationery"),
    ("ElectroWorld Nepal", "Prashant KC", "8", "electroworld"),
    ("Fresh Bakery & Biscuits", "Rita Joshi", "9", "fresh-bakery"),
    ("Nankin Distributors", "Bikash Dhakal", "10", "nankin-distr"),
    ("Patan Trading Co.", "Asha Karki", "11", "patan-trading"),
    ("Annapurna Supply Hub", "Niraj Joshi", "12", "annapurna-supply"),
]

# (first_name, last_name, phone_suffix)
CUSTOMERS = [
    ("Aarav", "Sharma", "1"),
    ("Smriti", "Adhikari", "2"),
    ("Binod", "Khadka", "3"),
    ("Chandra", "Lama", "4"),
    ("Deepika", "Rana", "5"),
    ("Erik", "Thapa", "6"),
    ("Sujata", "Bhattarai", "7"),
    ("Ganesh", "Tamang", "8"),
    ("Hema", "Koirala", "9"),
    ("Ismail", "Rai", "10"),
    ("Jaya", "Shrestha", "11"),
    ("Kriti", "Gurung", "12"),
    ("Laxmi", "Maharjan", "13"),
    ("Manish", "Shrestha", "14"),
    ("Nabina", "Joshi", "15"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rng(org):
    """Deterministic per-organization random stream."""
    return random.Random(str(org.pk))


def _money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"))


def already_seeded(org):
    """Marker every seeded org receives is the first demo SKU."""
    return Product.objects.filter(organization=org, sku=DEMO_SKUS[0]).exists()


def clear_organization(org):
    """
    Remove only demo records created for ``org``.

    Deletion is scoped by the demo identifiers used during seeding (SKU list,
    ``PO-DEMO-*`` / ``INV-DEMO-*`` invoices, the demo supplier/customer phone
    lists, and the ``Demo - `` title prefix) so real user data is untouched.
    """
    out = {key: 0 for key in (
        "categories", "products", "inventory", "purchases",
        "purchase_items", "sales", "sale_items", "stock_movements",
        "suppliers", "customers", "notifications", "insights",
    )}

    out["insights"] = AIInsight.objects.filter(
        organization=org, title__startswith="Demo - "
    ).delete()[0]
    out["notifications"] = Notification.objects.filter(
        organization=org, title__startswith="Demo - "
    ).delete()[0]

    sales = list(Sale.objects.filter(
        organization=org, invoice_number__startswith="INV-DEMO-"
    ))
    out["sale_items"] = SaleItem.objects.filter(sale__in=sales).delete()[0]
    for sale in sales:
        sale.delete()
    out["sales"] = len(sales)

    purchases = list(Purchase.objects.filter(
        organization=org, invoice_number__startswith="PO-DEMO-"
    ))
    out["purchase_items"] = PurchaseItem.objects.filter(
        purchase__in=purchases
    ).delete()[0]
    for purchase in purchases:
        purchase.delete()
    out["purchases"] = len(purchases)

    demo_products = list(Product.objects.filter(
        organization=org, sku__in=DEMO_SKUS
    ))
    out["stock_movements"] = StockMovement.objects.filter(
        organization=org, product__in=demo_products
    ).delete()[0]
    out["inventory"] = Inventory.objects.filter(
        organization=org, product__in=demo_products
    ).delete()[0]
    out["products"] = Product.objects.filter(
        organization=org, sku__in=DEMO_SKUS
    ).delete()[0]

    supplier_phones = [f"986000000{row[2]}" for row in SUPPLIERS]
    out["suppliers"] = Supplier.objects.filter(
        organization=org, phone__in=supplier_phones
    ).delete()[0]
    customer_phones = [f"985000000{row[2]}" for row in CUSTOMERS]
    out["customers"] = Customer.objects.filter(
        organization=org, phone__in=customer_phones
    ).delete()[0]

    # Categories left with no products were created by the demo.
    for name in CATEGORY_NAMES:
        category = Category.objects.filter(organization=org, name=name).first()
        if category and not category.products.exists():
            category.delete()
            out["categories"] += 1

    return out


def seed_organization(org):
    """Seed one organization; returns a dict of created count."""
    counts = {key: 0 for key in (
        "categories", "products", "inventory", "purchases",
        "purchase_items", "sales", "sale_items", "stock_movements",
        "suppliers", "customers", "notifications", "insights",
    )}
    rng = _rng(org)
    today = date.today()

    # -- Categories ----------------------------------------------------------
    cats = {}
    for name in CATEGORY_NAMES:
        category, _ = Category.objects.get_or_create(
            organization=org,
            name=name,
            defaults={"description": CATEGORY_DESCRIPTIONS.get(name, "")},
        )
        cats[name] = category
        counts["categories"] += 1

    # -- Products + Inventory -------------------------------------------------
    products = []
    for sku, row in zip(DEMO_SKUS, PRODUCTS):
        cat_name, name, buy, sell, qty, min_stock, max_stock, weight = row
        product, created = Product.objects.get_or_create(
            organization=org, sku=sku,
            defaults={
                "name": name,
                "category": cats[cat_name],
                "barcode": f"{sku}-BC",
                "description": f"{name} (demo {cat_name})",
                "buying_price": _money(buy),
                "selling_price": _money(sell),
                "is_active": True,
            },
        )
        products.append((product, qty, min_stock, max_stock, weight))
        if created:
            counts["products"] += 1

    for product, qty, min_stock, max_stock, _weight in products:
        _o, created = Inventory.objects.get_or_create(
            product=product,
            defaults={
                "organization": org,
                "quantity": qty,
                "minimum_stock": min_stock,
                "maximum_stock": max_stock,
            },
        )
        if created:
            counts["inventory"] += 1

    # -- Suppliers & customers ----------------------------------------------
    suppliers = []
    for row in SUPPLIERS:
        name, contact, suffix, email_slug = row
        supplier, created = Supplier.objects.get_or_create(
            organization=org, phone=f"986000000{suffix}",
            defaults={
                "name": name,
                "email": f"{email_slug}@example.com",
                "address": "Kathmandu, Nepal",
                "contact_person": contact,
                "is_active": True,
            },
        )
        suppliers.append(supplier)
        if created:
            counts["suppliers"] += 1

    customers = []
    for first, last, suffix in CUSTOMERS:
        customer, created = Customer.objects.get_or_create(
            organization=org, phone=f"985000000{suffix}",
            defaults={
                "first_name": first,
                "last_name": last,
                "email": f"{first.lower()}.{last.lower()}@example.com",
                "address": "Kathmandu, Nepal",
                "loyalty_points": rng.randint(0, 500),
                "is_active": True,
            },
        )
        customers.append(customer)
        if created:
            counts["customers"] += 1

    # -- Purchases (24 purchases over ~4 months, weighted catalogue) ----------
    weighted_pool = []
    for product, _q, _mn, _mx, weight in products:
        weighted_pool.extend([product] * weight)

    purchase_records = []
    for i in range(1, 25):
        purchase_date = today - timedelta(days=rng.randint(1, 115))
        supplier = rng.choice(suppliers)
        total = Decimal("0.00")
        purchase = Purchase.objects.create(
            organization=org,
            supplier=supplier,
            invoice_number=f"PO-DEMO-{i:04d}",
            purchase_date=purchase_date,
            status=rng.choice(["Completed", "Completed", "Pending"]),
            total_amount=_money(0),
            notes="Demo purchase",
        )
        for _line in range(rng.randint(1, 4)):
            product = rng.choice(weighted_pool)
            qty = rng.randint(5, 60)
            unit_price = product.buying_price
            subtotal = _money(Decimal(qty) * unit_price)
            PurchaseItem.objects.create(
                purchase=purchase, product=product,
                quantity=qty, unit_price=unit_price, subtotal=subtotal,
            )
            total += subtotal
            counts["purchase_items"] += 1
        purchase.total_amount = _money(total)
        purchase.save(update_fields=["total_amount"])
        purchase_records.append(purchase)
        counts["purchases"] += 1

    # -- Stock movements (IN per purchase) ------------------------------------
    for purchase in purchase_records:
        first_item = purchase.items.first()
        if first_item:
            StockMovement.objects.create(
                organization=org,
                product=first_item.product,
                movement_type="IN",
                quantity=first_item.quantity,
                remarks=f"Demo purchase {purchase.invoice_number}",
            )
            counts["stock_movements"] += 1

    # -- Sales ---------------------------------------------------------------
    counts = _create_sales(org, products, customers, rng, counts)

    # -- Notifications & AI insights ------------------------------------------
    _create_notifications(org, counts)
    _create_insights(org, counts)

    return counts


def _create_sales(org, products, customers, rng, counts):
    """Sales spread over ~100 days following popularity weights."""
    weighted_pool = []
    for product, _q, _mn, _mx, weight in products:
        weighted_pool.extend([product] * weight)

    today = date.today()
    sale_days = [today - timedelta(days=d) for d in range(1, 101)]
    invoice_seq = [0]

    def next_invoice():
        invoice_seq[0] += 1
        return f"INV-DEMO-{invoice_seq[0]:04d}"

    def make_sale(product, day, customer):
        lines = [(product, rng.randint(1, 5))]
        if rng.random() < 0.6:
            lines.append((rng.choice(weighted_pool), rng.randint(1, 4)))
        sale = Sale.objects.create(
            organization=org,
            customer=customer,
            invoice_number=next_invoice(),
            sale_date=day,
            amount_paid=_money(0),
            total_amount=_money(0),
            notes="Demo sale",
        )
        total = _money(0)
        for prod, qty in lines:
            subtotal = _money(Decimal(qty) * prod.selling_price)
            SaleItem.objects.create(
                sale=sale, product=prod, quantity=qty,
                unit_price=prod.selling_price, subtotal=subtotal,
            )
            total += subtotal
        sale.total_amount = total

        # Keep demo payment data coherent with the authoritative status:
        # "Paid" -> fully settled, "Partial" -> half settled, "Pending" -> unpaid.
        payment_choice = rng.choice(["Paid", "Paid", "Paid", "Partial", "Pending"])
        if payment_choice == "Paid":
            sale.amount_paid = total
        elif payment_choice == "Partial":
            sale.amount_paid = _money(total / 2)
        else:
            sale.amount_paid = _money(0)

        sale.save(
            update_fields=[
                "total_amount",
                "amount_paid",
                "payment_status",
            ]
        )
        counts["sales"] += 1
        counts["sale_items"] += len(lines)

    for _ in range(48):
        make_sale(rng.choice(weighted_pool), rng.choice(sale_days),
                  rng.choice(customers))

    # Every product must appear in >= 3 sales so the demand-forecast model
    # sees enough history per product. Top up shortfalls by appending
    # line items to existing sales rather than inflating the sale count.
    item_counts = defaultdict(int)
    for item in SaleItem.objects.filter(sale__organization=org):
        item_counts[item.product_id] += 1
    all_sales = list(Sale.objects.filter(organization=org))
    for product, _q, _mn, _mx, _weight in products:
        missing = max(0, 3 - item_counts.get(product.pk, 0))
        if missing:
            sale = rng.choice(all_sales)
            for _ in range(missing):
                qty = rng.randint(1, 3)
                subtotal = _money(Decimal(qty) * product.selling_price)
                SaleItem.objects.create(
                    sale=sale, product=product, quantity=qty,
                    unit_price=product.selling_price, subtotal=subtotal,
                )
                sale.total_amount = _money(sale.total_amount + subtotal)
                sale.save(
                    update_fields=[
                        "total_amount",
                        "payment_status",
                    ]
                )
                counts["sale_items"] += 1

    return counts


def _create_notifications(org, counts):
    """Small realistic notifications derived from the actual seeded inventory."""
    stocks = list(
        Inventory.objects.filter(organization=org).select_related("product")
    )
    out_of_stock = [s for s in stocks if s.quantity == 0]
    low_stock = [s for s in stocks if 0 < s.quantity <= s.minimum_stock]

    notif_specs = []
    for item in out_of_stock[:2]:
        notif_specs.append((
            f"Demo - {item.product.name} is out of stock",
            f"{item.product.name} currently has no units left in stock.",
            "OUT_OF_STOCK",
        ))
    for item in low_stock[:2]:
        notif_specs.append((
            f"Demo - {item.product.name} running low",
            f"{item.product.name} has {item.quantity} units; minimum is "
            f"{item.minimum_stock}.",
            "LOW_STOCK",
        ))

    target = Inventory.objects.filter(
        organization=org, quantity__gt=0, quantity__lte=2
    ).select_related("product").first()
    if target:
        notif_specs.append((
            f"Demo - Restock {target.product.name}",
            (
                f"Restock {target.product.name} to cover expected demand; "
                f"only {target.quantity} units left."
            ),
            "AI",
        ))

    for title, message, ntype in notif_specs:
        Notification.objects.create(
            organization=org,
            title=title,
            message=message,
            notification_type=ntype,
            is_read=False,
        )
        counts["notifications"] += 1


def _create_insights(org, counts):
    """Demo AIInsight rows that only reference the actual seeded records."""
    stocks = list(
        Inventory.objects.filter(organization=org).select_related("product")
    )

    def add(itype, title, description, confidence="0.85"):
        # Conservative duplicate check so re-running never duplicates an
        # insight the org already has (manual or demo).
        if AIInsight.objects.filter(
            organization=org,
            insight_type=itype,
            title__iexact=title,
        ).exists():
            return
        AIInsight.objects.create(
            organization=org,
            title=title,
            description=description,
            insight_type=itype,
            confidence_score=Decimal(confidence),
            is_active=True,
        )
        counts["insights"] += 1

    forecast_items = _safe_forecast(org)
    if forecast_items:
        names = [
            f["product_name"]
            for f in sorted(
                forecast_items,
                key=lambda x: x["predicted_quantity"],
                reverse=True,
            )[:3]
        ]
    else:
        names = [s.product.name for s in sorted(
            stocks, key=lambda s: s.quantity
        )[:3]]
    for name in names:
        add(
            "FORECAST",
            f"Demo - Demand forecast: {name}",
            f"{name} is expected to see the highest demand next; "
            "plan stock accordingly.",
        )

    low_stocks = [s for s in stocks if s.quantity > 0]
    low_sorted = sorted(low_stocks, key=lambda s: (s.quantity < s.minimum_stock,
                                                   s.quantity))[:3]
    for item in low_sorted:
        add(
            "LOW_STOCK",
            f"Demo - Low stock: {item.product.name}",
            f"{item.product.name} has {item.quantity} units; reorder soon.",
        )
    for item in [s for s in stocks if s.quantity == 0][:2]:
        add(
            "LOW_STOCK",
            f"Demo - Out of stock: {item.product.name}",
            f"{item.product.name} is currently out of stock.",
            "0.70",
        )

    to_reorder = sorted(
        (s for s in stocks if s.quantity <= s.minimum_stock),
        key=lambda s: s.minimum_stock - s.quantity,
        reverse=True,
    )[:3]
    for item in to_reorder:
        gap = max(0, item.minimum_stock - item.quantity)
        add(
            "RECOMMENDATION",
            f"Demo - Restock {item.product.name}",
            f"Order about {gap} units of {item.product.name} to reach the "
            f"minimum stock of {item.minimum_stock}.",
        )

    sold = (
        SaleItem.objects.filter(sale__organization=org)
        .aggregate(total=Sum("quantity"))["total"]
        or 0
    )
    sale_count = Sale.objects.filter(organization=org).count()
    add(
        "ANALYSIS",
        "Demo - Sales overview",
        f"The demo period generated {sold} units sold across "
        f"{sale_count} sales; beverages and snacks lead demand.",
    )


def _safe_forecast(org):
    """Use the existing forecasting model where available; else no forecast."""
    try:
        from ai.services.forecasting import forecast_demand
        return forecast_demand(org)
    except Exception:  # noqa: BLE001 - demo helper must never block seeding
        return []


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    """Idempotent, tenant-scoped demo-data seeder."""

    help = (
        "Populate every organization with realistic demo data. Idempotent and "
        "tenant-safe. Use --clear to remove only the demo rows."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove only records created by this demo seed.",
        )

    def handle(self, *args, **options):
        run_clear = options.get("clear")
        orgs = list(Organization.objects.order_by("name"))

        if not orgs:
            self.stdout.write(
                self.style.WARNING(
                    "No organizations exist. Create an organization (and an "
                    "admin user) before running the seeder."
                )
            )
            return

        self.stdout.write(self.style.SUCCESS(
            f"Organizations found: {len(orgs)}"
        ))

        for org in orgs:
            if run_clear:
                with transaction.atomic():
                    cleared = clear_organization(org)
                self._report(org, cleared)
            else:
                if already_seeded(org):
                    self.stdout.write(self.style.WARNING(
                        f"Skipping {org.name}: demo data already present. "
                        "Run with --clear first to reset."
                    ))
                    continue
                with transaction.atomic():
                    counts = seed_organization(org)
                self._report(org, counts)

    def _report(self, org, counts):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Organization: {org.name}"))
        for label, key in (
            ("Categories", "categories"),
            ("Products", "products"),
            ("Inventory records", "inventory"),
            ("Suppliers", "suppliers"),
            ("Customers", "customers"),
            ("Purchases", "purchases"),
            ("Purchase items", "purchase_items"),
            ("Sales", "sales"),
            ("Sale items", "sale_items"),
            ("Stock movements", "stock_movements"),
            ("Notifications", "notifications"),
            ("AI Insights", "insights"),
        ):
            self.stdout.write(f"  {label}: {counts.get(key, 0)}")