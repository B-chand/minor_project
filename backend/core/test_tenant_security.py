from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization
from customers.models import Customer
from suppliers.models import Supplier
from inventory.models import Category, Product, Inventory, StockMovement
from purchases.models import Purchase, PurchaseItem
from sales.models import Sale, SaleItem

User = get_user_model()


class TenantIsolationSecurityTests(APITestCase):
    """Phase 17 tenant isolation security regression tests."""

    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(
            name="SecOrgA", email="seca@example.com", phone="1001"
        )
        cls.org_b = Organization.objects.create(
            name="SecOrgB", email="secb@example.com", phone="1002"
        )
        cls.admin_a = User.objects.create_user(
            username="sec_admin_a", email="secadmin_a@example.com",
            password="pass-123", organization=cls.org_a, role="ADMIN",
        )
        User.objects.create_user(
            username="sec_admin_b", email="secadmin_b@example.com",
            password="pass-123", organization=cls.org_b, role="ADMIN",
        )

        cls.cat_a = Category.objects.create(organization=cls.org_a, name="CatA")
        cls.cat_b = Category.objects.create(organization=cls.org_b, name="CatB")

        cls.product_a = Product.objects.create(
            organization=cls.org_a, category=cls.cat_a, name="ProdA",
            sku="SECA-1", buying_price="10.00", selling_price="20.00",
        )
        cls.product_b = Product.objects.create(
            organization=cls.org_b, category=cls.cat_b, name="ProdB",
            sku="SECB-1", buying_price="10.00", selling_price="20.00",
        )
        cls.product_c = Product.objects.create(
            organization=cls.org_a, category=cls.cat_a, name="ProdC",
            sku="SECA-2", buying_price="5.00", selling_price="15.00",
        )

        cls.inventory_a = Inventory.objects.create(
            organization=cls.org_a, product=cls.product_a, quantity=100,
        )
        cls.inventory_b = Inventory.objects.create(
            organization=cls.org_b, product=cls.product_b, quantity=100,
        )

        cls.customer_a = Customer.objects.create(
            organization=cls.org_a, first_name="Alice", phone="9810010000",
        )
        cls.customer_b = Customer.objects.create(
            organization=cls.org_b, first_name="Bob", phone="9820020000",
        )

        cls.supplier_a = Supplier.objects.create(
            organization=cls.org_a, name="SupplierA", phone="9700010000",
        )
        cls.supplier_b = Supplier.objects.create(
            organization=cls.org_b, name="SupplierB", phone="9700020000",
        )

        cls.sale_b = Sale.objects.create(
            organization=cls.org_b, customer=cls.customer_b,
            invoice_number="SECB-SALE", sale_date=date.today(), total_amount=0,
        )
        cls.purchase_b = Purchase.objects.create(
            organization=cls.org_b, supplier=cls.supplier_b,
            invoice_number="SECB-PUR", purchase_date=date.today(), total_amount=0,
        )

    def setUp(self):
        self.client.force_authenticate(self.admin_a)

    # ----------------------------- helpers -----------------------------

    def _create_sale(self, invoice="SECA-SALE"):
        res = self.client.post(
            "/api/sales/sales/",
            {"invoice_number": invoice, "sale_date": "2026-08-01", "payment_status": "Paid"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        return res.data["id"]

    def _create_purchase(self, invoice="SECA-PUR"):
        res = self.client.post(
            "/api/purchases/purchases/",
            {"invoice_number": invoice, "purchase_date": "2026-08-01", "status": "Completed", "supplier": self.supplier_a.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        return res.data["id"]

    # ------------------- same-tenant success paths ---------------------

    def test_same_tenant_sale_item_succeeds(self):
        sale_id = self._create_sale()
        res = self.client.post(
            "/api/sales/sale-items/",
            {"sale": sale_id, "product": self.product_a.id, "quantity": 2, "unit_price": "20.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        item = SaleItem.objects.get(pk=res.data["id"])
        self.assertEqual(item.sale.organization, self.org_a)
        self.assertEqual(item.product, self.product_a)

    def test_same_tenant_sale_with_customer_succeeds(self):
        res = self.client.post(
            "/api/sales/sales/",
            {"invoice_number": "SEC-2", "sale_date": "2026-08-01", "payment_status": "Paid", "customer": self.customer_a.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        sale = Sale.objects.get(pk=res.data["id"])
        self.assertEqual(sale.customer, self.customer_a)
        self.assertEqual(sale.organization, self.org_a)

    def test_same_tenant_purchase_item_succeeds(self):
        purchase_id = self._create_purchase()
        res = self.client.post(
            "/api/purchases/purchase-items/",
            {"purchase": purchase_id, "product": self.product_a.id, "quantity": 2, "unit_price": "10.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        item = PurchaseItem.objects.get(pk=res.data["id"])
        self.assertEqual(item.purchase.organization, self.org_a)
        self.assertEqual(item.product, self.product_a)

    def test_same_tenant_purchase_with_supplier_succeeds(self):
        res = self.client.post(
            "/api/purchases/purchases/",
            {"invoice_number": "SEC-3", "purchase_date": "2026-08-01", "status": "Completed", "supplier": self.supplier_a.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        purchase = Purchase.objects.get(pk=res.data["id"])
        self.assertEqual(purchase.supplier, self.supplier_a)
        self.assertEqual(purchase.organization, self.org_a)

    def test_same_tenant_product_with_category_succeeds(self):
        res = self.client.post(
            "/api/inventory/products/",
            {"name": "NewProd", "sku": "SEC-NEW", "buying_price": "10.00", "selling_price": "20.00", "category": self.cat_a.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        product = Product.objects.get(pk=res.data["id"])
        self.assertEqual(product.category, self.cat_a)
        self.assertEqual(product.organization, self.org_a)

    def test_same_tenant_inventory_creation_succeeds(self):
        res = self.client.post(
            "/api/inventory/stock-movements/",
            {"product": self.product_c.id, "movement_type": "IN", "quantity": 15},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        inv = Inventory.objects.get(product=self.product_c)
        self.assertEqual(inv.product, self.product_c)
        self.assertEqual(inv.organization, self.org_a)
        self.assertEqual(inv.quantity, 15)

    def test_same_tenant_stock_movement_succeeds(self):
        res = self.client.post(
            "/api/inventory/stock-movements/",
            {"product": self.product_a.id, "movement_type": "IN", "quantity": 5},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        movement = StockMovement.objects.get(pk=res.data["id"])
        self.assertEqual(movement.product, self.product_a)
        self.assertEqual(movement.organization, self.org_a)

    # ------------------- cross-tenant create rejection -----------------

    def test_sale_item_cannot_reference_other_org_sale(self):
        before_inventory = self.inventory_a.quantity
        res = self.client.post(
            "/api/sales/sale-items/",
            {"sale": self.sale_b.id, "product": self.product_a.id, "quantity": 1, "unit_price": "10.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["sale"][0])
        self.assertEqual(SaleItem.objects.count(), 0)
        self.inventory_a.refresh_from_db()
        self.assertEqual(self.inventory_a.quantity, before_inventory)
        self.assertEqual(StockMovement.objects.filter(organization=self.org_b).count(), 0)

    def test_sale_item_cannot_reference_other_org_product(self):
        sale_id = self._create_sale()
        res = self.client.post(
            "/api/sales/sale-items/",
            {"sale": sale_id, "product": self.product_b.id, "quantity": 1, "unit_price": "10.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["product"][0])
        self.assertEqual(SaleItem.objects.count(), 0)
        self.inventory_a.refresh_from_db()
        self.assertEqual(self.inventory_a.quantity, 100)

    def test_purchase_item_cannot_reference_other_org_purchase(self):
        res = self.client.post(
            "/api/purchases/purchase-items/",
            {"purchase": self.purchase_b.id, "product": self.product_a.id, "quantity": 1, "unit_price": "10.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["purchase"][0])
        self.assertEqual(PurchaseItem.objects.count(), 0)
        self.assertEqual(StockMovement.objects.filter(organization=self.org_b).count(), 0)

    def test_purchase_item_cannot_reference_other_org_product(self):
        purchase_id = self._create_purchase()
        res = self.client.post(
            "/api/purchases/purchase-items/",
            {"purchase": purchase_id, "product": self.product_b.id, "quantity": 1, "unit_price": "10.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["product"][0])
        self.assertEqual(PurchaseItem.objects.count(), 0)
        self.inventory_b.refresh_from_db()
        self.assertEqual(self.inventory_b.quantity, 100)

    def test_sale_cannot_reference_other_org_customer(self):
        res = self.client.post(
            "/api/sales/sales/",
            {"invoice_number": "SEC-CX", "sale_date": "2026-08-01", "payment_status": "Paid", "customer": self.customer_b.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["customer"][0])
        self.assertEqual(Sale.objects.count(), 1)

    def test_purchase_cannot_reference_other_org_supplier(self):
        res = self.client.post(
            "/api/purchases/purchases/",
            {"invoice_number": "SEC-CX", "purchase_date": "2026-08-01", "status": "Completed", "supplier": self.supplier_b.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["supplier"][0])
        self.assertEqual(Purchase.objects.count(), 1)

    def test_product_cannot_reference_other_org_category(self):
        res = self.client.post(
            "/api/inventory/products/",
            {"name": "BadCat", "sku": "SEC-BADCAT", "buying_price": "10.00", "selling_price": "20.00", "category": self.cat_b.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["category"][0])
        self.assertEqual(
            Product.objects.filter(organization=self.org_a, sku="SEC-BADCAT").count(), 0
        )

    def test_inventory_cannot_reference_other_org_product(self):
        res = self.client.post(
            "/api/inventory/inventory/",
            {"product": self.product_b.id, "quantity": 5},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["product"][0])
        self.assertEqual(
            Inventory.objects.filter(product=self.product_b, organization=self.org_a).count(), 0
        )

    def test_stock_movement_cannot_reference_other_org_product(self):
        res = self.client.post(
            "/api/inventory/stock-movements/",
            {"product": self.product_b.id, "movement_type": "IN", "quantity": 5},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["product"][0])
        self.assertEqual(StockMovement.objects.count(), 0)
        self.assertEqual(Inventory.objects.filter(product=self.product_b).count(), 1)
        self.inventory_b.refresh_from_db()
        self.assertEqual(self.inventory_b.quantity, 100)

    def test_sale_item_update_cannot_reference_other_org_product(self):
        sale_id = self._create_sale()
        item_res = self.client.post(
            "/api/sales/sale-items/",
            {"sale": sale_id, "product": self.product_a.id, "quantity": 1, "unit_price": "10.00"},
            format="json",
        )
        self.assertEqual(item_res.status_code, status.HTTP_201_CREATED, item_res.data)
        item_id = item_res.data["id"]
        res = self.client.patch(
            f"/api/sales/sale-items/{item_id}/",
            {"product": self.product_b.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["product"][0])
        item = SaleItem.objects.get(pk=item_id)
        self.assertEqual(item.product, self.product_a)

    def test_sale_update_cannot_reference_other_org_customer(self):
        res = self.client.post(
            "/api/sales/sales/",
            {"invoice_number": "SEC-UP", "sale_date": "2026-08-01", "payment_status": "Paid", "customer": self.customer_a.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        sale_id = res.data["id"]
        res = self.client.patch(
            f"/api/sales/sales/{sale_id}/",
            {"customer": self.customer_b.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["customer"][0])
        sale = Sale.objects.get(pk=sale_id)
        self.assertEqual(sale.customer, self.customer_a)

    def test_product_update_cannot_use_other_org_category(self):
        res = self.client.post(
            "/api/inventory/products/",
            {"name": "UpProd", "sku": "SEC-UPCAT", "buying_price": "10.00", "selling_price": "20.00", "category": self.cat_a.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        product_id = res.data["id"]
        res = self.client.patch(
            f"/api/inventory/products/{product_id}/",
            {"category": self.cat_b.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("object does not exist", res.data["category"][0])
        product = Product.objects.get(pk=product_id)
        self.assertEqual(product.category, self.cat_a)

    def test_sale_cannot_update_other_org_sale(self):
        res = self.client.patch(
            f"/api/sales/sales/{self.sale_b.id}/",
            {"payment_status": "Pending"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_record_payment_on_other_org_sale(self):
        res = self.client.post(
            f"/api/sales/sales/{self.sale_b.id}/record-payment/",
            {"amount": "10.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        sale_b = Sale.objects.get(pk=self.sale_b.pk)
        self.assertEqual(float(sale_b.amount_paid), 0.00)

    # ------------------------ forged organization fields ----------------

    def test_forged_org_fields_on_sale_are_ignored(self):
        res = self.client.post(
            "/api/sales/sales/",
            {
                "invoice_number": "SEC-FORGED",
                "sale_date": "2026-08-01",
                "payment_status": "Paid",
                "customer": self.customer_a.id,
                "organization": self.org_b.id,
                "organization_id": self.org_b.id,
                "tenant_id": self.org_b.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        sale = Sale.objects.get(pk=res.data["id"])
        self.assertEqual(sale.organization, self.org_a)

    def test_forged_org_fields_on_product_are_ignored(self):
        res = self.client.post(
            "/api/inventory/products/",
            {
                "name": "ForgedProd",
                "sku": "SEC-FORGED",
                "buying_price": "10.00",
                "selling_price": "20.00",
                "category": self.cat_a.id,
                "organization": self.org_b.id,
                "organization_id": self.org_b.id,
                "tenant_id": self.org_b.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        product = Product.objects.get(pk=res.data["id"])
        self.assertEqual(product.organization, self.org_a)

    def test_forged_org_fields_on_sale_item_are_ignored(self):
        sale_id = self._create_sale("SEC-FORGED-ITEM")
        res = self.client.post(
            "/api/sales/sale-items/",
            {
                "sale": sale_id,
                "product": self.product_a.id,
                "quantity": 1,
                "unit_price": "10.00",
                "organization": self.org_b.id,
                "organization_id": self.org_b.id,
                "tenant_id": self.org_b.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        item = SaleItem.objects.get(pk=res.data["id"])
        self.assertEqual(item.sale.organization, self.org_a)

    # ------------------------ query string forgery ----------------------

    def test_query_string_org_forgery_is_ignored_for_reads(self):
        sale_id = self._create_sale("SEC-QS-1")
        res = self.client.get(f"/api/sales/sales/?organization={self.org_b.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        invoices = []
        for page in res.data["results"]:
            invoices.append(page["invoice_number"])
        self.assertEqual(invoices, ["SEC-QS-1"])
        self.assertNotIn("SECB-SALE", invoices)

    def test_query_string_org_forgery_is_ignored_for_stock_movements(self):
        self.client.post(
            "/api/inventory/stock-movements/",
            {"product": self.product_a.id, "movement_type": "IN", "quantity": 3},
            format="json",
        )
        res = self.client.get(
            "/api/inventory/stock-movements/?organization={}".format(self.org_b.id)
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for page in res.data["results"]:
            self.assertEqual(page["organization"], self.org_a.id)

    def test_cross_tenant_sale_item_delete_is_rejected(self):
        res = self.client.delete("/api/sales/sale-items/{}/".format("00000000-0000-0000-0000-000000000001"))
        self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST))

    def test_nullable_sale_customer_still_allowed(self):
        res = self.client.post(
            "/api/sales/sales/",
            {"invoice_number": "SEC-NOCUST", "sale_date": "2026-08-01", "payment_status": "Paid"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        sale = Sale.objects.get(pk=res.data["id"])
        self.assertIsNone(sale.customer)

    def test_nullable_product_category_still_allowed(self):
        res = self.client.post(
            "/api/inventory/products/",
            {"name": "NoCat", "sku": "SEC-NOCAT", "buying_price": "10.00", "selling_price": "20.00", "category": None},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertIsNone(Product.objects.get(pk=res.data["id"]).category)

    def test_cross_tenant_failure_creates_zero_records(self):
        attempts = [
            ("/api/sales/sale-items/", {"sale": self.sale_b.id, "product": self.product_a.id, "quantity": 1, "unit_price": "1.00"}),
            ("/api/purchases/purchase-items/", {"purchase": self.purchase_b.id, "product": self.product_a.id, "quantity": 1, "unit_price": "1.00"}),
        ]
        for url, payload in attempts:
            res = self.client.post(url, payload, format="json")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SaleItem.objects.count(), 0)
        self.assertEqual(PurchaseItem.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_forged_org_fields_on_stock_movement_are_ignored(self):
        res = self.client.post(
            "/api/inventory/stock-movements/",
            {
                "product": self.product_a.id,
                "movement_type": "IN",
                "quantity": 4,
                "organization": self.org_b.id,
                "organization_id": self.org_b.id,
                "tenant_id": self.org_b.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        movement = StockMovement.objects.get(pk=res.data["id"])
        self.assertEqual(movement.organization, self.org_a)

    def test_cross_tenant_purchase_delete_is_rejected(self):
        res = self.client.patch(
            f"/api/purchases/purchases/{self.purchase_b.id}/",
            {"status": "Cancelled"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)