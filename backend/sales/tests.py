from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization
from customers.models import Customer
from inventory.models import Product, Inventory
from .models import Sale, SaleItem

User = get_user_model()


class SaleFlowTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name="SalesCo", email="sales@test.com", phone="4"
        )
        cls.admin = User.objects.create_user(
            username="salesadmin", email="salesadmin@test.com",
            password="pass-123", organization=cls.org, role="ADMIN",
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

        self.product = Product.objects.create(
            name="Widget", sku="W1", organization=self.org,
            buying_price="10.00", selling_price="20.00",
        )
        self.inventory = Inventory.objects.create(
            product=self.product, organization=self.org, quantity=50
        )

    def _create_sale_with_item(self, qty=5):
        sale_res = self.client.post(
            "/api/sales/sales/",
            {
                "invoice_number": "INV-1001",
                "sale_date": "2026-08-01",
                "payment_status": "Paid",
            },
            format="json",
        )
        self.assertEqual(sale_res.status_code, status.HTTP_201_CREATED)
        sale_id = sale_res.data["id"]

        item_res = self.client.post(
            "/api/sales/sale-items/",
            {
                "sale": sale_id,
                "product": self.product.id,
                "quantity": qty,
                "unit_price": "20.00",
            },
            format="json",
        )
        self.assertEqual(item_res.status_code, status.HTTP_201_CREATED)
        return sale_id

    def test_sale_deducts_stock_and_sets_total(self):
        sale_id = self._create_sale_with_item(5)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 45)

        sale = Sale.objects.get(id=sale_id)
        self.assertEqual(float(sale.total_amount), 100.00)

    def test_sale_rejects_insufficient_stock(self):
        sale_res = self.client.post(
            "/api/sales/sales/",
            {"invoice_number": "INV-1002", "sale_date": "2026-08-01"},
            format="json",
        )
        sale_id = sale_res.data["id"]

        item_res = self.client.post(
            "/api/sales/sale-items/",
            {
                "sale": sale_id,
                "product": self.product.id,
                "quantity": 999,
                "unit_price": "20.00",
            },
            format="json",
        )
        self.assertEqual(item_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 50)

    def test_deleting_sale_restores_stock(self):
        sale_id = self._create_sale_with_item(5)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 45)

        res = self.client.delete(f"/api/sales/sales/{sale_id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 50)