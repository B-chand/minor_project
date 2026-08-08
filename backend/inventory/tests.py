from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization
from .models import Product, Inventory, StockMovement

User = get_user_model()


class InventoryTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name="InvCo", email="inv@test.com", phone="3"
        )
        cls.admin = User.objects.create_user(
            username="invadmin", email="invadmin@test.com",
            password="pass-123", organization=cls.org, role="ADMIN",
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def _create_product(self, name="Widget"):
        res = self.client.post(
            "/api/inventory/products/",
            {
                "name": name,
                "sku": name.upper(),
                "buying_price": "10.00",
                "selling_price": "20.00",
                "category": None,
            },
            format="json",
        )
        return res

    def test_create_product(self):
        res = self._create_product("Widget")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_product_rejects_selling_below_buying(self):
        res = self.client.post(
            "/api/inventory/products/",
            {
                "name": "Loss",
                "sku": "LOSS1",
                "buying_price": "15.00",
                "selling_price": "10.00",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_product_partial_update_without_prices(self):
        res = self._create_product("Widget")
        pid = res.data["id"]
        # PATCH with only name should not crash
        res = self.client.patch(
            f"/api/inventory/products/{pid}/",
            {"name": "Widget Renamed"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Widget Renamed")

    def test_stock_movement_adjusts_inventory(self):
        res = self._create_product("Widget")
        pid = res.data["id"]

        # Stock IN increases quantity
        res = self.client.post(
            "/api/inventory/stock-movements/",
            {"product": pid, "movement_type": "IN", "quantity": 25, "remarks": "restock"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        inv = Inventory.objects.get(product_id=pid)
        self.assertEqual(inv.quantity, 25)

        # Stock OUT decreases
        res = self.client.post(
            "/api/inventory/stock-movements/",
            {"product": pid, "movement_type": "OUT", "quantity": 10},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        inv.refresh_from_db()
        self.assertEqual(inv.quantity, 15)

        # Excessive OUT is rejected
        res = self.client.post(
            "/api/inventory/stock-movements/",
            {"product": pid, "movement_type": "OUT", "quantity": 500},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        inv.refresh_from_db()
        self.assertEqual(inv.quantity, 15)

        self.assertEqual(
            StockMovement.objects.filter(product_id=pid).count(), 2
        )