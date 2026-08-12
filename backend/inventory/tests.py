from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization
from suppliers.models import Supplier
from customers.models import Customer
from .models import Category, Product, Inventory, StockMovement

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


class InventoryAdjustmentAndFilterTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(
            name="InvA", email="inva@test.com", phone="1"
        )
        cls.org_b = Organization.objects.create(
            name="InvB", email="invb@test.com", phone="2"
        )
        cls.admin_a = User.objects.create_user(
            username="invaadmin", email="invaadmin@test.com",
            password="pass-123", organization=cls.org_a, role="ADMIN",
        )

        cls.category = Category.objects.create(
            name="Electronics", organization=cls.org_a
        )

        cls.product_in = Product.objects.create(
            name="Alpha Gear", sku="P-ALPHA", organization=cls.org_a,
            category=cls.category, buying_price=10, selling_price=20,
        )
        cls.product_low = Product.objects.create(
            name="Beta Gear", sku="P-BETA", organization=cls.org_a,
            category=cls.category, buying_price=11, selling_price=21,
        )
        cls.product_out = Product.objects.create(
            name="Gamma Gear", sku="P-GAMMA", organization=cls.org_a,
            buying_price=12, selling_price=22,
        )

        cls.inventory_in = Inventory.objects.create(
            product=cls.product_in, organization=cls.org_a,
            quantity=25, minimum_stock=10, maximum_stock=100,
        )
        cls.inventory_low = Inventory.objects.create(
            product=cls.product_low, organization=cls.org_a,
            quantity=5, minimum_stock=10, maximum_stock=100,
        )
        cls.inventory_out = Inventory.objects.create(
            product=cls.product_out, organization=cls.org_a,
            quantity=0, minimum_stock=10, maximum_stock=100,
        )

        cls.product_b = Product.objects.create(
            name="Intruder", sku="P-INTRUDER", organization=cls.org_b,
            buying_price=10, selling_price=20,
        )
        cls.inventory_b = Inventory.objects.create(
            product=cls.product_b, organization=cls.org_b,
            quantity=10, minimum_stock=5,
        )

    def setUp(self):
        self.client.force_authenticate(self.admin_a)

    def _adjust(self, pk, payload=None):
        return self.client.post(
            f"/api/inventory/inventory/{pk}/adjust/",
            payload or {},
            format="json",
        )

    def _movement_count(self):
        return StockMovement.objects.count()

    # ---------------- adjustment behavior ----------------

    def test_adjust_increases_quantity(self):
        res = self._adjust(self.inventory_in.pk, {
            "adjustment": 7, "reason": "Found",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["previous_quantity"], 25)
        self.assertEqual(res.data["adjustment"], 7)
        self.assertEqual(res.data["new_quantity"], 32)

        self.inventory_in.refresh_from_db()
        self.assertEqual(self.inventory_in.quantity, 32)

        movement = StockMovement.objects.get(product=self.product_in)
        self.assertEqual(movement.movement_type, "ADJUSTMENT")
        self.assertEqual(movement.quantity, 7)
        self.assertEqual(movement.remarks, "Found")
        self.assertEqual(movement.created_by, self.admin_a)
        self.assertEqual(movement.organization, self.org_a)

    def test_adjust_decreases_quantity(self):
        res = self._adjust(self.inventory_in.pk, {
            "adjustment": -5, "reason": "Correction",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["new_quantity"], 20)

        self.inventory_in.refresh_from_db()
        self.assertEqual(self.inventory_in.quantity, 20)

        movement = StockMovement.objects.get(product=self.product_in)
        self.assertEqual(movement.quantity, 5)

    def test_adjust_records_reason_with_note(self):
        res = self._adjust(self.inventory_in.pk, {
            "adjustment": 3, "reason": "Damaged", "note": "Returned by courier",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        movement = StockMovement.objects.get(product=self.product_in)
        self.assertEqual(movement.remarks, "Damaged: Returned by courier")

    def test_adjust_rejects_negative_result_and_stays_atomic(self):
        before = self._movement_count()
        res = self._adjust(self.inventory_in.pk, {
            "adjustment": -500, "reason": "Correction",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("below zero", res.data["adjustment"][0].lower())

        self.inventory_in.refresh_from_db()
        self.assertEqual(self.inventory_in.quantity, 25)
        self.assertEqual(self._movement_count(), before)

    def test_adjust_exact_removal_to_zero_is_allowed(self):
        res = self._adjust(self.inventory_low.pk, {
            "adjustment": -5, "reason": "Lost",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.inventory_low.refresh_from_db()
        self.assertEqual(self.inventory_low.quantity, 0)

    def test_adjust_rejects_zero_adjustment(self):
        before = self._movement_count()
        res = self._adjust(self.inventory_in.pk, {
            "adjustment": 0, "reason": "Correction",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot be zero", res.data["adjustment"][0].lower())
        self.inventory_in.refresh_from_db()
        self.assertEqual(self.inventory_in.quantity, 25)
        self.assertEqual(self._movement_count(), before)

    def test_adjust_rejects_boolean_adjustment(self):
        res = self._adjust(self.inventory_in.pk, {
            "adjustment": True, "reason": "Correction",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.inventory_in.refresh_from_db()
        self.assertEqual(self.inventory_in.quantity, 25)

    def test_adjust_rejects_invalid_reason(self):
        res = self._adjust(self.inventory_in.pk, {
            "adjustment": 1, "reason": "Nonsense",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.inventory_in.refresh_from_db()
        self.assertEqual(self.inventory_in.quantity, 25)

    def test_adjust_other_reason_requires_note(self):
        res = self._adjust(self.inventory_in.pk, {
            "adjustment": 1, "reason": "Other", "note": "",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        res = self._adjust(self.inventory_in.pk, {
            "adjustment": 1, "reason": "Other", "note": "ab",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.inventory_in.refresh_from_db()
        self.assertEqual(self.inventory_in.quantity, 25)

    def test_adjust_other_reason_with_meaningful_note_succeeds(self):
        res = self._adjust(self.inventory_in.pk, {
            "adjustment": 2, "reason": "Other",
            "note": "Found extra boxes in storage.",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        movement = StockMovement.objects.get(product=self.product_in)
        self.assertEqual(movement.remarks, "Found extra boxes in storage.")

    # ---------------- tenant isolation ----------------

    def test_adjust_rejects_cross_tenant_inventory(self):
        before = self._movement_count()
        res = self._adjust(self.inventory_b.pk, {
            "adjustment": 1, "reason": "Correction",
        })
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.inventory_b.refresh_from_db()
        self.assertEqual(self.inventory_b.quantity, 10)
        self.assertEqual(self._movement_count(), before)

    def test_adjust_missing_inventory_returns_404(self):
        res = self._adjust(999999, {
            "adjustment": 1, "reason": "Correction",
        })
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ---------------- search & filtering ----------------

    def test_inventory_search_by_product_name(self):
        res = self.client.get(
            "/api/inventory/inventory/", {"search": "Alpha"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["product_name"], "Alpha Gear")

    def test_inventory_search_by_sku(self):
        res = self.client.get(
            "/api/inventory/inventory/", {"search": "P-BETA"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(
            res.data["results"][0]["product_name"], "Beta Gear"
        )

    def test_inventory_filter_by_category(self):
        res = self.client.get(
            "/api/inventory/inventory/",
            {"product__category": self.category.id},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)
        names = {row["product_name"] for row in res.data["results"]}
        self.assertEqual(names, {"Alpha Gear", "Beta Gear"})

    def test_inventory_stock_status_out(self):
        res = self.client.get(
            "/api/inventory/inventory/", {"stock_status": "out"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(
            res.data["results"][0]["id"], self.inventory_out.pk
        )

    def test_inventory_stock_status_low(self):
        res = self.client.get(
            "/api/inventory/inventory/", {"stock_status": "low"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(
            res.data["results"][0]["id"], self.inventory_low.pk
        )

    def test_inventory_stock_status_in(self):
        res = self.client.get(
            "/api/inventory/inventory/", {"stock_status": "in"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(
            res.data["results"][0]["id"], self.inventory_in.pk
        )

    def test_inventory_stock_status_unknown_is_ignored(self):
        res = self.client.get(
            "/api/inventory/inventory/", {"stock_status": "bogus"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 3)

    def test_inventory_list_exposes_sku_and_category(self):
        res = self.client.get("/api/inventory/inventory/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        row = next(
            r for r in res.data["results"]
            if r["product_name"] == "Alpha Gear"
        )
        self.assertEqual(row["product_sku"], "P-ALPHA")
        self.assertEqual(row["category_name"], "Electronics")

        gamma = next(
            r for r in res.data["results"]
            if r["product_name"] == "Gamma Gear"
        )
        self.assertIsNone(gamma["category_name"])


class InventoryStockIntegrityTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name="StockIntegrity", email="si@test.com", phone="5"
        )
        cls.admin = User.objects.create_user(
            username="siadmin", email="siadmin@test.com",
            password="pass-123", organization=cls.org, role="ADMIN",
        )
        cls.supplier = Supplier.objects.create(
            name="Integrity Traders", phone="9800000001",
            organization=cls.org,
        )
        cls.customer = Customer.objects.create(
            organization=cls.org, first_name="Int", last_name="Buyer",
            phone="9800000002",
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def _product_with_stock(self, quantity=25):
        product = Product.objects.create(
            name="Integrity Widget", sku="SIW1", organization=self.org,
            buying_price=10, selling_price=20,
        )
        inventory = Inventory.objects.create(
            product=product, organization=self.org,
            quantity=quantity, minimum_stock=10, maximum_stock=100,
        )
        return product, inventory

    def _movement_count(self):
        return StockMovement.objects.count()

    # -------- direct quantity writes are rejected --------

    def test_direct_quantity_update_is_rejected(self):
        product, inventory = self._product_with_stock()
        before = self._movement_count()

        res = self.client.patch(
            f"/api/inventory/inventory/{inventory.pk}/",
            {"quantity": 100},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "cannot be set directly", res.data["quantity"][0].lower()
        )
        inventory.refresh_from_db()
        self.assertEqual(inventory.quantity, 25)
        self.assertEqual(self._movement_count(), before)

    def test_direct_quantity_patch_rejected_even_if_value_matches(self):
        product, inventory = self._product_with_stock()
        res = self.client.patch(
            f"/api/inventory/inventory/{inventory.pk}/",
            {"quantity": 25},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "cannot be set directly", res.data["quantity"][0].lower()
        )
        inventory.refresh_from_db()
        self.assertEqual(inventory.quantity, 25)

    def test_direct_quantity_create_is_rejected(self):
        product = Product.objects.create(
            name="Fresh", sku="SIW2", organization=self.org,
            buying_price=10, selling_price=20,
        )
        before = StockMovement.objects.count()

        res = self.client.post(
            "/api/inventory/inventory/",
            {"product": product.pk, "quantity": 50},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "cannot be set directly", res.data["quantity"][0].lower()
        )
        self.assertFalse(Inventory.objects.filter(product=product).exists())
        self.assertEqual(StockMovement.objects.count(), before)

    def test_rejected_direct_update_creates_no_stock_movement(self):
        product, inventory = self._product_with_stock()
        before = self._movement_count()

        self.client.patch(
            f"/api/inventory/inventory/{inventory.pk}/",
            {"quantity": 100},
            format="json",
        )
        self.assertEqual(
            StockMovement.objects.filter(product=product).count(), 0
        )
        self.assertEqual(self._movement_count(), before)

    def test_threshold_update_remains_allowed(self):
        product, inventory = self._product_with_stock()
        res = self.client.patch(
            f"/api/inventory/inventory/{inventory.pk}/",
            {"minimum_stock": 30},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        inventory.refresh_from_db()
        self.assertEqual(inventory.quantity, 25)
        self.assertEqual(inventory.minimum_stock, 30)

    # -------- legitimate stock workflows remain intact --------

    def test_opening_stock_in_movement_still_works(self):
        product = Product.objects.create(
            name="Fresh SKU", sku="SIW3", organization=self.org,
            buying_price=10, selling_price=20,
        )
        res = self.client.post(
            "/api/inventory/stock-movements/",
            {
                "product": product.pk,
                "movement_type": "IN",
                "quantity": 40,
                "remarks": "Opening stock",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        inventory = Inventory.objects.get(product=product)
        self.assertEqual(inventory.quantity, 40)

        movement = StockMovement.objects.get(product=product)
        self.assertEqual(movement.movement_type, "IN")
        self.assertEqual(movement.quantity, 40)

    def test_adjustment_still_works(self):
        product, inventory = self._product_with_stock()
        res = self.client.post(
            f"/api/inventory/inventory/{inventory.pk}/adjust/",
            {"adjustment": 5, "reason": "Correction"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        inventory.refresh_from_db()
        self.assertEqual(inventory.quantity, 30)
        self.assertEqual(
            StockMovement.objects.get(product=product).movement_type,
            "ADJUSTMENT",
        )

    def test_purchase_still_increases_stock(self):
        product = Product.objects.create(
            name="Buy Widget", sku="SIW4", organization=self.org,
            buying_price=10, selling_price=20,
        )
        res = self.client.post(
            "/api/purchases/purchases/",
            {
                "supplier": self.supplier.pk,
                "invoice_number": "SI-PO-1",
                "purchase_date": "2026-08-01",
                "status": "Completed",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        res = self.client.post(
            "/api/purchases/purchase-items/",
            {
                "purchase": res.data["id"],
                "product": product.pk,
                "quantity": 8,
                "unit_price": "12.00",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        inventory = Inventory.objects.get(product=product)
        self.assertEqual(inventory.quantity, 8)
        self.assertEqual(
            StockMovement.objects.get(product=product).movement_type, "IN"
        )

    def test_sale_still_decreases_stock(self):
        product, inventory = self._product_with_stock(quantity=50)
        res = self.client.post(
            "/api/sales/sales/",
            {
                "invoice_number": "SI-INV-1",
                "sale_date": "2026-08-01",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        res = self.client.post(
            "/api/sales/sale-items/",
            {
                "sale": res.data["id"],
                "product": product.pk,
                "quantity": 6,
                "unit_price": "20.00",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        inventory.refresh_from_db()
        self.assertEqual(inventory.quantity, 44)
        self.assertEqual(
            StockMovement.objects.get(product=product).movement_type, "OUT"
        )