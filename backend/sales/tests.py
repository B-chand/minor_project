from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase
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

    # ------------------- Payment status clarity -------------------

    def _make_sale(self, invoice, amount_paid="0.00"):
        res = self.client.post(
            "/api/sales/sales/",
            {
                "invoice_number": invoice,
                "sale_date": "2026-08-01",
                "amount_paid": amount_paid,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        sale_id = res.data["id"]

        item_res = self.client.post(
            "/api/sales/sale-items/",
            {
                "sale": sale_id,
                "product": self.product.id,
                "quantity": 5,
                "unit_price": "20.00",
            },
            format="json",
        )
        self.assertEqual(item_res.status_code, status.HTTP_201_CREATED)
        return sale_id

    def test_unpaid_sale_is_REPORTED_UNPAID_with_remaining(self):
        sale_id = self._make_sale("INV-PAY1")
        res = self.client.get(f"/api/sales/sales/{sale_id}/")
        self.assertEqual(res.data["payment_status"], "UNPAID")
        self.assertEqual(float(res.data["remaining_amount"]), 100.00)

    def test_partial_payment_is_PARTIAL(self):
        sale_id = self._make_sale("INV-PAY2", amount_paid="40.00")
        res = self.client.get(f"/api/sales/sales/{sale_id}/")
        self.assertEqual(res.data["payment_status"], "PARTIAL")
        self.assertEqual(float(res.data["amount_paid"]), 40.00)
        self.assertEqual(float(res.data["remaining_amount"]), 60.00)

    def test_full_payment_is_PAID(self):
        sale_id = self._make_sale("INV-PAY3", amount_paid="100.00")
        res = self.client.get(f"/api/sales/sales/{sale_id}/")
        self.assertEqual(res.data["payment_status"], "PAID")
        self.assertEqual(float(res.data["remaining_amount"]), 0.00)

    def test_recording_payment_on_update_recomputes_status(self):
        sale_id = self._make_sale("INV-PAY4")
        res = self.client.patch(
            f"/api/sales/sales/{sale_id}/",
            {"amount_paid": "100.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["payment_status"], "PAID")

    def test_paid_payment_status_is_not_client_writable(self):
        sale_id = self._make_sale("INV-PAY5")
        self.client.patch(
            f"/api/sales/sales/{sale_id}/",
            {"payment_status": "Paid"},
            format="json",
        )
        sale = Sale.objects.get(id=sale_id)
        self.assertEqual(
            sale.computed_payment_status(),
            "UNPAID",
        )

    def test_negative_paid_amount_rejected(self):
        res = self.client.post(
            "/api/sales/sales/",
            {
                "invoice_number": "INV-NEG",
                "sale_date": "2026-08-01",
                "amount_paid": "-5.00",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_paid_amount_cannot_exceed_total_on_update(self):
        sale_id = self._make_sale("INV-OVP")
        res = self.client.patch(
            f"/api/sales/sales/{sale_id}/",
            {"amount_paid": "500.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------- Search & filters -------------------

    def test_sale_search_and_payment_status_filter(self):
        self._make_sale("INV-SRCH-PAID", amount_paid="100.00")
        self._make_sale("INV-SRCH-UNPAID")

        res = self.client.get("/api/sales/sales/?search=INV-SRCH")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {r["invoice_number"] for r in res.data["results"]},
            {"INV-SRCH-PAID", "INV-SRCH-UNPAID"},
        )

        res = self.client.get("/api/sales/sales/?payment_status=PAID")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        invoices = [r["invoice_number"] for r in res.data["results"]]
        self.assertIn("INV-SRCH-PAID", invoices)
        self.assertNotIn("INV-SRCH-UNPAID", invoices)


# ------------------- Phase 18.1: legacy payment-status sync -------------------


class PaymentStatusSyncMigrationTests(TestCase):
    """
    Verify the data migration backfills stored payment_status for existing
    rows from amount_paid / total_amount without touching any financial data.
    """

    migrate_from = [
        ("sales", "0003_sale_amount_paid_alter_sale_payment_status")
    ]
    migrate_to = [
        ("sales", "0004_sync_payment_status")
    ]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)

        old_apps = executor.loader.project_state(self.migrate_from).apps

        Organization = old_apps.get_model("core", "Organization")
        Product = old_apps.get_model("inventory", "Product")
        Sale = old_apps.get_model("sales", "Sale")
        SaleItem = old_apps.get_model("sales", "SaleItem")

        org = Organization.objects.create(
            name="Sync Org", email="sync@test.com", phone="9940000001"
        )
        product = Product.objects.create(
            name="SyncWidget", sku="SYNC-WIDGET", organization=org,
            buying_price="10.00", selling_price="20.00",
        )

        # (invoice, stale stored status, amount_paid, total_amount)
        self.cases = [
            ("LEG-UNPAID", "Paid", Decimal("0.00"), Decimal("100.00")),
            ("LEG-PARTIAL", "Pending", Decimal("40.00"), Decimal("100.00")),
            ("LEG-PAID-FULL", "Pending", Decimal("100.00"), Decimal("100.00")),
            ("LEG-OVERPAID", "Paid", Decimal("120.00"), Decimal("100.00")),
            ("LEG-NEGATIVE", "Paid", Decimal("-5.00"), Decimal("100.00")),
            ("LEG-ZERO-TOTAL", "Paid", Decimal("0.00"), Decimal("0.00")),
        ]

        self.sale_ids = {}
        for invoice, stale_status, paid, total in self.cases:
            sale = Sale.objects.create(
                organization=org,
                invoice_number=invoice,
                sale_date="2026-01-01",
                payment_status=stale_status,
                amount_paid=paid,
                total_amount=total,
            )
            self.sale_ids[invoice] = sale.pk

        # A SaleItem must survive the sync untouched.
        self.item_sale_pk = self.sale_ids["LEG-UNPAID"]
        SaleItem.objects.create(
            sale_id=self.item_sale_pk,
            product=product,
            quantity=3,
            unit_price=Decimal("20.00"),
            subtotal=Decimal("60.00"),
        )

        self.sale_count_before = Sale.objects.count()
        self.org_pk = org.pk

    def test_backfill_syncs_stored_payment_status_without_data_changes(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.migrate_to)

        Sale = executor.loader.project_state(self.migrate_to).apps.get_model(
            "sales", "Sale"
        )
        SaleItem = executor.loader.project_state(self.migrate_to).apps.get_model(
            "sales", "SaleItem"
        )

        expected = {
            "LEG-UNPAID": "UNPAID",
            "LEG-PARTIAL": "PARTIAL",
            "LEG-PAID-FULL": "PAID",
            "LEG-OVERPAID": "PAID",
            "LEG-NEGATIVE": "UNPAID",
            "LEG-ZERO-TOTAL": "UNPAID",
        }

        for invoice, status_ in expected.items():
            sale = Sale.objects.get(pk=self.sale_ids[invoice])
            self.assertEqual(sale.payment_status, status_, invoice)

        # Financial values, row identities and tenant are preserved.
        partial = Sale.objects.get(pk=self.sale_ids["LEG-PARTIAL"])
        self.assertEqual(Decimal(partial.amount_paid), Decimal("40.00"))
        self.assertEqual(Decimal(partial.total_amount), Decimal("100.00"))
        self.assertEqual(partial.organization_id, self.org_pk)
        self.assertEqual(Sale.objects.count(), self.sale_count_before)

        # SaleItems remain untouched.
        self.assertEqual(SaleItem.objects.count(), 1)
        item = SaleItem.objects.get()
        self.assertEqual(Decimal(item.subtotal), Decimal("60.00"))
        self.assertEqual(item.sale_id, self.item_sale_pk)


class PaymentStatusFilterTests(APITestCase):
    """
    After sync (or for any newly created sale) the stored payment_status MUST
    agree with the computed/displayed status, so the filter returns exactly the
    records the UI labels PAID / PARTIAL / UNPAID.
    """

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name="FilterCo", email="filter@test.com", phone="9940000002"
        )
        cls.admin = User.objects.create_user(
            username="filteradmin", email="filteradmin@test.com",
            password="pass-123", organization=cls.org, role="ADMIN",
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)
        self.product = Product.objects.create(
            name="Widget", sku="W-FILTER", organization=self.org,
            buying_price="10.00", selling_price="20.00",
        )
        self.inventory = Inventory.objects.create(
            product=self.product, organization=self.org, quantity=100
        )

    def _make_sale(self, invoice, amount_paid):
        res = self.client.post(
            "/api/sales/sales/",
            {
                "invoice_number": invoice,
                "sale_date": "2026-08-01",
                "amount_paid": amount_paid,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        sale_id = res.data["id"]

        item_res = self.client.post(
            "/api/sales/sale-items/",
            {
                "sale": sale_id,
                "product": self.product.id,
                "quantity": 1,
                "unit_price": "100.00",
            },
            format="json",
        )
        self.assertEqual(item_res.status_code, status.HTTP_201_CREATED)
        return sale_id

    def test_payment_status_filter_agrees_with_computed_status(self):
        self._make_sale("F-PAID", "100.00")
        self._make_sale("F-PARTIAL", "40.00")
        self._make_sale("F-UNPAID", "0.00")

        for status_, expected in [
            ("PAID", ["F-PAID"]),
            ("PARTIAL", ["F-PARTIAL"]),
            ("UNPAID", ["F-UNPAID"]),
        ]:
            res = self.client.get(f"/api/sales/sales/?payment_status={status_}")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            invoices = [r["invoice_number"] for r in res.data["results"]]
            self.assertEqual(invoices, expected, status_)

    def test_stored_status_matches_computed_for_new_sales(self):
        sale_id = self._make_sale("F-CONSISTENT", "40.00")
        sale = Sale.objects.get(id=sale_id)
        self.assertEqual(sale.payment_status, sale.computed_payment_status())
        self.assertEqual(sale.payment_status, "PARTIAL")


# ------------------- Record Payment -------------------


class RecordPaymentTests(APITestCase):
    """
    POST /api/sales/sales/{id}/record-payment/
    """

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name="PaymentsCo", email="pay@test.com", phone="9940000003"
        )
        cls.admin = User.objects.create_user(
            username="payadmin", email="payadmin@test.com",
            password="pass-123", organization=cls.org, role="ADMIN",
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

        self.product = Product.objects.create(
            name="Gadget", sku="G1", organization=self.org,
            buying_price="10.00", selling_price="20.00",
        )
        self.inventory = Inventory.objects.create(
            product=self.product, organization=self.org, quantity=50
        )

    def _make_sale(self, invoice, amount_paid="0.00"):
        res = self.client.post(
            "/api/sales/sales/",
            {
                "invoice_number": invoice,
                "sale_date": "2026-08-01",
                "amount_paid": amount_paid,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        sale_id = res.data["id"]

        item_res = self.client.post(
            "/api/sales/sale-items/",
            {
                "sale": sale_id,
                "product": self.product.id,
                "quantity": 5,
                "unit_price": "20.00",
            },
            format="json",
        )
        self.assertEqual(item_res.status_code, status.HTTP_201_CREATED)
        return sale_id

    def _record_payment(self, sale_id, amount):
        return self.client.post(
            f"/api/sales/sales/{sale_id}/record-payment/",
            {"amount": amount},
            format="json",
        )

    def test_partial_payment_is_recorded_and_reported(self):
        sale_id = self._make_sale("PMT-1")
        res = self._record_payment(sale_id, "40.00")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["payment_status"], "PARTIAL")
        self.assertEqual(float(res.data["amount_paid"]), 40.00)
        self.assertEqual(float(res.data["remaining_amount"]), 60.00)

    def test_second_payment_completes_sale(self):
        sale_id = self._make_sale("PMT-2", amount_paid="60.00")
        res = self._record_payment(sale_id, "40.00")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["payment_status"], "PAID")
        self.assertEqual(float(res.data["amount_paid"]), 100.00)
        self.assertEqual(float(res.data["remaining_amount"]), 0.00)

    def test_full_payment_of_unpaid_sale(self):
        sale_id = self._make_sale("PMT-3")
        res = self._record_payment(sale_id, "100.00")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["payment_status"], "PAID")
        self.assertEqual(float(res.data["remaining_amount"]), 0.00)

    def test_paid_sale_rejects_further_payment(self):
        sale_id = self._make_sale("PMT-4", amount_paid="100.00")
        res = self._record_payment(sale_id, "10.00")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        sale = Sale.objects.get(pk=sale_id)
        self.assertEqual(float(sale.amount_paid), 100.00)

    def test_overpayment_rejected(self):
        sale_id = self._make_sale("PMT-5")
        res = self._record_payment(sale_id, "150.00")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", res.data)
        sale = Sale.objects.get(pk=sale_id)
        self.assertEqual(float(sale.amount_paid), 0.00)

    def test_zero_and_negative_payments_rejected(self):
        sale_id = self._make_sale("PMT-6")
        for amount in ("0.00", "-5.00"):
            res = self._record_payment(sale_id, amount)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, amount)
            self.assertIn("amount", res.data)
        sale = Sale.objects.get(pk=sale_id)
        self.assertEqual(float(sale.amount_paid), 0.00)

    def test_missing_amount_rejected(self):
        sale_id = self._make_sale("PMT-7")
        res = self.client.post(
            f"/api/sales/sales/{sale_id}/record-payment/",
            {},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", res.data)

    def test_payment_does_not_change_total_or_stock(self):
        sale_id = self._make_sale("PMT-8")
        res = self._record_payment(sale_id, "40.00")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(float(res.data["total_amount"]), 100.00)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 45)

    def test_unauthenticated_request_rejected(self):
        sale_id = self._make_sale("PMT-9")
        self.client.force_authenticate(user=None)
        res = self._record_payment(sale_id, "10.00")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)