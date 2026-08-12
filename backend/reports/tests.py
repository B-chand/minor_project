from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization
from customers.models import Customer
from suppliers.models import Supplier
from sales.models import Sale
from purchases.models import Purchase

from .models import Report

User = get_user_model()

_COUNTER = [0]


def _next_phone(prefix):
    _COUNTER[0] += 1
    return f"98{prefix}{_COUNTER[0]:08d}"


class ReportApiTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(
            name="RepA", email="repa@test.com", phone="1"
        )
        cls.org_b = Organization.objects.create(
            name="RepB", email="repb@test.com", phone="2"
        )
        cls.user_a = User.objects.create_user(
            username="repadmin", email="repadmin@test.com",
            password="pass-123", organization=cls.org_a, role="ADMIN",
        )

    def setUp(self):
        self.client.force_authenticate(self.user_a)

    def _make_sale(self, org, invoice, date, amount_paid):
        customer = Customer.objects.create(
            organization=org, first_name="Sam", last_name="Lee", phone=_next_phone(1)
        )
        return Sale.objects.create(
            organization=org,
            customer=customer,
            invoice_number=invoice,
            sale_date=date,
            total_amount=Decimal("1000.00"),
            amount_paid=Decimal(amount_paid),
        )

    def _make_purchase(self, org, invoice, date):
        supplier = Supplier.objects.create(
            organization=org, name="Supplier Inc", phone=_next_phone(2)
        )
        purchase = Purchase.objects.create(
            organization=org,
            supplier=supplier,
            invoice_number=invoice,
            purchase_date=date,
            total_amount=Decimal("500.00"),
            status="Completed",
        )
        return purchase

    def test_sales_report_is_org_scoped_with_payment_breakdown(self):
        self._make_sale(self.org_a, "INV-A-FULL", "2026-08-01", "1000.00")
        self._make_sale(self.org_a, "INV-A-PARTIAL", "2026-08-02", "400.00")
        # Other org's sale must not leak into the report.
        self._make_sale(self.org_b, "INV-B-SALE", "2026-08-03", "999.00")

        res = self.client.get("/api/reports/sales/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        invoices = [r["invoice"] for r in res.data]
        self.assertEqual(len(invoices), 2)

        paid_entry = next(r for r in res.data if float(r["paid"]) == 1000.00)
        self.assertEqual(paid_entry["status"], "PAID")
        self.assertEqual(float(paid_entry["remaining"]), 0.00)

        partial_entry = next(r for r in res.data if float(r["paid"]) == 400.00)
        self.assertEqual(partial_entry["status"], "PARTIAL")
        self.assertEqual(float(partial_entry["remaining"]), 600.00)

        self.assertNotIn("INV-B-SALE", [r["invoice"] for r in res.data])

    def test_sales_report_respects_date_range(self):
        self._make_sale(self.org_a, "INV-R1", "2026-08-01", "1000.00")
        self._make_sale(self.org_a, "INV-R2", "2026-08-10", "1000.00")

        res = self.client.get(
            "/api/reports/sales/?start_date=2026-08-05&end_date=2026-08-15"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_purchases_report_is_org_scoped_and_date_filtered(self):
        self._make_purchase(self.org_a, "PO-REP-1", "2026-07-01")
        self._make_purchase(self.org_a, "PO-REP-2", "2026-07-15")
        self._make_purchase(self.org_b, "PO-REP-3", "2026-07-10")

        res = self.client.get("/api/reports/purchases/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        invoices = [r["invoice"] for r in res.data]
        self.assertIn("PO-REP-1", invoices)
        self.assertIn("PO-REP-2", invoices)
        self.assertNotIn("PO-REP-3", invoices)

        res = self.client.get(
            "/api/reports/purchases/?start_date=2026-07-01&end_date=2026-07-05"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        invoices = [r["invoice"] for r in res.data]
        self.assertEqual(invoices, ["PO-REP-1"])

    def test_dashboard_totals_respect_inclusive_date_range(self):
        self._make_sale(self.org_a, "INV-D1", "2026-08-01", "1000.00")
        self._make_sale(self.org_a, "INV-D2", "2026-08-10", "1000.00")
        self._make_purchase(self.org_a, "PO-D1", "2026-08-01")
        self._make_purchase(self.org_a, "PO-D2", "2026-08-20")
        # Foreign org data must never leak in.
        self._make_sale(self.org_b, "INV-DB", "2026-08-10", "9999.00")

        res = self.client.get("/api/reports/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(float(res.data["total_sales"]), 2000.00)
        self.assertEqual(float(res.data["total_purchases"]), 1000.00)
        self.assertEqual(res.data["sales_count"], 2)
        self.assertEqual(res.data["purchases_count"], 2)

        # Both boundaries inclusive, foreign sale excluded.
        res = self.client.get(
            "/api/reports/dashboard/?from_date=2026-08-01&to_date=2026-08-10"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(float(res.data["total_sales"]), 2000.00)
        self.assertEqual(res.data["sales_count"], 2)
        self.assertEqual(float(res.data["total_purchases"]), 500.00)
        self.assertEqual(res.data["purchases_count"], 1)

        # Same-day range is valid.
        res = self.client.get(
            "/api/reports/dashboard/?from_date=2026-08-10&to_date=2026-08-10"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["sales_count"], 1)
        self.assertEqual(res.data["purchases_count"], 0)

        # Empty/no-result range reports zeros normally.
        res = self.client.get(
            "/api/reports/dashboard/?from_date=2026-09-01&to_date=2026-09-30"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(float(res.data["total_sales"]), 0.00)
        self.assertEqual(float(res.data["total_purchases"]), 0.00)
        self.assertEqual(res.data["sales_count"], 0)
        self.assertEqual(res.data["purchases_count"], 0)


class SavedReportApiTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(
            name="SavedA", email="saveda@test.com", phone="21"
        )
        cls.org_b = Organization.objects.create(
            name="SavedB", email="savedb@test.com", phone="22"
        )
        cls.user_a = User.objects.create_user(
            username="saved-admin-a", email="savedadmina@test.com",
            password="pass-123", organization=cls.org_a, role="ADMIN",
        )
        cls.user_b = User.objects.create_user(
            username="saved-admin-b", email="savedadminb@test.com",
            password="pass-123", organization=cls.org_b, role="ADMIN",
        )

    def setUp(self):
        self.client.force_authenticate(self.user_a)

    def _payload(self, **overrides):
        payload = {
            "title": "Q3 Sales & Inventory Summary",
            "report_type": "SALES",
            "description": "Snapshot for later review",
            "report_data": {
                "config": {"tab": "sales", "report_type": "SALES"},
                "generated_at": "2026-08-10T05:00:00Z",
                "rows": [
                    {
                        "date": "2026-08-01",
                        "invoice": "INV-SR-1",
                        "customer": "Sam Lee",
                        "amount": "100.00",
                        "status": "PAID",
                    }
                ],
            },
        }
        payload.update(overrides)
        return payload

    def test_create_saves_report_with_report_data(self):
        res = self.client.post("/api/reports/", self._payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        self.assertEqual(res.data["title"], "Q3 Sales & Inventory Summary")
        self.assertEqual(res.data["report_data"]["config"]["tab"], "sales")
        self.assertEqual(
            res.data["report_data"]["rows"][0]["invoice"], "INV-SR-1"
        )

        report = Report.objects.get(id=res.data["id"])
        self.assertEqual(report.organization, self.org_a)
        self.assertEqual(report.generated_by, self.user_a)
        self.assertEqual(report.report_type, "SALES")

    def test_report_data_round_trip_on_retrieve(self):
        created = self.client.post("/api/reports/", self._payload(), format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        res = self.client.get(f"/api/reports/{created.data['id']}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res.data["report_data"], created.data["report_data"]
        )

    def test_saved_reports_are_org_isolated_in_list(self):
        self.client.post("/api/reports/", self._payload(), format="json")
        Report.objects.create(
            organization=self.org_b,
            title="Foreign Report",
            report_type="PURCHASE",
            report_data={
                "config": {"tab": "purchases"},
                "generated_at": "2026-08-10T05:00:00Z",
                "rows": [{"invoice": "PO-FOREIGN"}],
            },
            generated_by=self.user_b,
        )

        res = self.client.get("/api/reports/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(
            res.data["results"][0]["title"], "Q3 Sales & Inventory Summary"
        )

    def test_cross_tenant_read_update_delete_denied(self):
        foreign = Report.objects.create(
            organization=self.org_b,
            title="Foreign Report",
            report_type="SALES",
            generated_by=self.user_b,
        )

        self.assertEqual(
            self.client.get(f"/api/reports/{foreign.pk}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/reports/{foreign.pk}/",
                {"title": "Hacked"},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(f"/api/reports/{foreign.pk}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(Report.objects.filter(pk=foreign.pk).exists())

    def test_foreign_user_cannot_touch_my_saved_report(self):
        self.client.force_authenticate(self.user_b)
        mine = Report.objects.create(
            organization=self.org_a,
            title="My Report",
            report_type="SALES",
            generated_by=self.user_a,
        )

        self.assertEqual(
            self.client.get(f"/api/reports/{mine.pk}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(f"/api/reports/{mine.pk}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(Report.objects.filter(pk=mine.pk).exists())

    def test_delete_saved_report(self):
        created = self.client.post("/api/reports/", self._payload(), format="json")
        report_id = created.data["id"]

        res = self.client.delete(f"/api/reports/{report_id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Report.objects.filter(pk=report_id).exists())

        res = self.client.get(f"/api/reports/{report_id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_generated_by_is_server_controlled(self):
        other = User.objects.create_user(
            username="saved-staff",
            email="savedstaff@test.com",
            password="pass-123",
            organization=self.org_a,
            role="STAFF",
        )

        res = self.client.post(
            "/api/reports/",
            self._payload(generated_by=other.pk),
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        report = Report.objects.get(id=res.data["id"])
        self.assertEqual(report.generated_by, self.user_a)

        res = self.client.patch(
            f"/api/reports/{report.pk}/",
            {"generated_by": other.pk},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        report.refresh_from_db()
        self.assertEqual(report.generated_by, self.user_a)
        self.assertEqual(res.data["generated_by_name"], self.user_a.username)