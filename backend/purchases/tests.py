from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization
from inventory.models import Product, Inventory
from suppliers.models import Supplier
from .models import Purchase, PurchaseItem

User = get_user_model()


class PurchaseApiTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name="BuyCo", email="buy@test.com", phone="1"
        )
        cls.admin = User.objects.create_user(
            username="buyadmin", email="buyadmin@test.com",
            password="pass-123", organization=cls.org, role="ADMIN",
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

        self.supplier = Supplier.objects.create(
            name="Nepal Traders", phone="9800000000", organization=self.org
        )
        self.product = Product.objects.create(
            name="Widget", sku="P2", organization=self.org,
            buying_price="10.00", selling_price="20.00",
        )
        self.inventory = Inventory.objects.create(
            product=self.product, organization=self.org, quantity=0
        )

    def _create_purchase(self, invoice, date="2026-07-01", status_="Completed"):
        purchase = Purchase.objects.create(
            organization=self.org,
            supplier=self.supplier,
            invoice_number=invoice,
            purchase_date=date,
            status=status_,
            total_amount=Decimal("100.00"),
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product,
            quantity=10,
            unit_price=Decimal("10.00"),
            subtotal=Decimal("100.00"),
        )
        return purchase

    def test_purchase_search_and_status_filter(self):
        self._create_purchase("PO-ALPHA-001", date="2026-07-01", status_="Completed")
        self._create_purchase("PO-BETA-002", date="2026-07-02", status_="Pending")
        self._create_purchase("PO-OTHER-003", date="2026-07-03", status_="Completed")

        res = self.client.get("/api/purchases/purchases/?search=ALPHA")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        invoices = [r["invoice_number"] for r in res.data["results"]]
        self.assertEqual(invoices, ["PO-ALPHA-001"])

        res = self.client.get("/api/purchases/purchases/?status=Pending")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        invoices = [r["invoice_number"] for r in res.data["results"]]
        self.assertEqual(invoices, ["PO-BETA-002"])

    def test_purchase_total_is_computed_from_items(self):
        res = self.client.post(
            "/api/purchases/purchases/",
            {
                "supplier": self.supplier.id,
                "invoice_number": "PO-COMP-001",
                "purchase_date": "2026-07-05",
                "status": "Completed",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        purchase_id = res.data["id"]

        item_res = self.client.post(
            "/api/purchases/purchase-items/",
            {
                "purchase": purchase_id,
                "product": self.product.id,
                "quantity": 4,
                "unit_price": "12.50",
            },
            format="json",
        )
        self.assertEqual(item_res.status_code, status.HTTP_201_CREATED)

        purchase = Purchase.objects.get(id=purchase_id)
        self.assertEqual(float(purchase.total_amount), 50.00)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 4)