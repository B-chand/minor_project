from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization
from customers.models import Customer
from suppliers.models import Supplier
from inventory.models import Category, Product, Inventory
from purchases.models import Purchase
from sales.models import Sale
from reports.models import Report
from ai.models import AIInsight

User = get_user_model()


def _mk_org(code, name, email, phone="10001"):
    return Organization.objects.create(
        code=code, name=name, email=email, phone=phone
    )


def _mk_user(username, email, organization, role="STAFF", password="pass-123"):
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
        organization=organization,
        role=role,
    )


class StrictTenantArchitectureTests(APITestCase):
    """
    Final INVENTO architecture: every user belongs to exactly one
    organization; there is no cross-tenant role, no business switching and
    no X-Business-Id. Tenant identity always comes from
    ``request.user.organization``.
    """

    @classmethod
    def setUpTestData(cls):
        cls.org_b1 = _mk_org("B1", "Alpha Traders", "alpha@test.com")
        cls.org_b2 = _mk_org("B2", "Omega Store", "omega@test.com")

        cls.admin_b1 = _mk_user("s30-admin-b1", "a1@test.com", cls.org_b1, role="ADMIN")
        cls.staff_b1 = _mk_user("s30-staff-b1", "s1@test.com", cls.org_b1, role="STAFF")
        cls.admin_b2 = _mk_user("s30-admin-b2", "a2@test.com", cls.org_b2, role="ADMIN")

        # Foreign-tenant data (B2) that no B1 user may ever see.
        cls.cat_b2 = Category.objects.create(organization=cls.org_b2, name="B2 Cat")
        cls.product_b2 = Product.objects.create(
            organization=cls.org_b2, category=cls.cat_b2, name="B2 Product",
            sku="S30-B2", buying_price="10.00", selling_price="20.00",
        )
        cls.inventory_b2 = Inventory.objects.create(
            organization=cls.org_b2, product=cls.product_b2, quantity=50,
        )
        cls.customer_b2 = Customer.objects.create(
            organization=cls.org_b2, first_name="B2Cust", phone="9800000901",
        )
        cls.supplier_b2 = Supplier.objects.create(
            organization=cls.org_b2, name="B2Sup", phone="9700000901",
        )
        cls.sale_b2 = Sale.objects.create(
            organization=cls.org_b2, invoice_number="S30-SALE-B2",
            sale_date=date.today(), total_amount=0,
        )
        cls.purchase_b2 = Purchase.objects.create(
            organization=cls.org_b2, supplier=cls.supplier_b2,
            invoice_number="S30-PUR-B2", purchase_date=date.today(),
            total_amount=0,
        )
        cls.report_b2 = Report.objects.create(
            organization=cls.org_b2, title="B2 Secret Report",
            report_type="SALES", generated_by=cls.admin_b2,
        )
        cls.insight_b2 = AIInsight.objects.create(
            organization=cls.org_b2, title="B2 Secret Insight",
            description="B2 only", insight_type="RECOMMENDATION",
        )

    def _login(self, business_code, username, password="pass-123"):
        return self.client.post(
            "/api/token/",
            {"business_code": business_code, "username": username, "password": password},
            format="json",
        )

    # ------------------ login / business code ------------------

    def test_business_code_is_required_for_business_users(self):
        res = self._login("", "s30-admin-b1")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_business_code_is_rejected(self):
        res = self._login("B9", "s30-admin-b1")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_password_is_rejected(self):
        res = self._login("B1", "s30-admin-b1", "wrong-password")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_username_from_other_business_is_rejected(self):
        res = self._login("B2", "s30-admin-b1")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_super_admin_cannot_use_api_login(self):
        User.objects.create_superuser(
            username="s30-root", email="s30-root@system.com", password="root-pass"
        )
        for business_code in ("", "B1"):
            res = self._login(business_code, "s30-root", "root-pass")
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_super_admin_switching_endpoints_are_gone(self):
        res = self.client.get("/api/accounts/superadmin/businesses/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        res = self.client.post(
            "/api/accounts/superadmin/select-business/",
            {"organization_id": str(self.org_b1.id)},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------ registration ------------------

    def test_registration_generates_unique_business_code(self):
        for name, email in [
            ("Alpha Retail", "regalpha@test.com"),
            ("Omega Retail", "regomega@test.com"),
        ]:
            res = self.client.post(
                "/api/accounts/register/",
                {
                    "username": f"reg-{name.split()[0].lower()}",
                    "email": f"reg-{name.split()[0].lower()}@test.com",
                    "password": "secure-pass-123",
                    "phone": "9800000001",
                    "organization_name": name,
                    "organization_email": email,
                    "organization_phone": "9800000002",
                },
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        codes = list(
            Organization.objects.filter(
                email__in=["regalpha@test.com", "regomega@test.com"]
            ).values_list("code", flat=True)
        )
        self.assertEqual(len(codes), 2)
        self.assertEqual(len(set(codes)), 2)

    def test_generated_business_code_returned_and_usable(self):
        res = self.client.post(
            "/api/accounts/register/",
            {
                "username": "reg-admin",
                "email": "reg-admin@test.com",
                "password": "secure-pass-123",
                "phone": "9800000003",
                "organization_name": "CodeCo",
                "organization_email": "codeco@test.com",
                "organization_phone": "9800000004",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        code = res.data["business_code"]
        self.assertTrue(code)

        login = self._login(code, "reg-admin", "secure-pass-123")
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertEqual(login.data["user"]["business_code"], code)

    # ------------------ admin-only access (ADMIN) ------------------

    def test_admin_can_access_admin_features(self):
        self.client.force_authenticate(self.admin_b1)
        for url in [
            "/api/reports/",
            "/api/ai/insights/",
            "/api/ai/forecast/",
            "/api/accounts/staff/",
            "/api/business/profile/",
        ]:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

    def test_admin_only_sees_own_organization(self):
        self.client.force_authenticate(self.admin_b1)
        res = self.client.get("/api/inventory/products/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 0)

        res = self.client.get(f"/api/inventory/products/{self.product_b2.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        res = self.client.get(f"/api/reports/{self.report_b2.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        res = self.client.get(f"/api/ai/insights/{self.insight_b2.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------ staff access ------------------

    def test_staff_can_use_ai_chat(self):
        self.client.force_authenticate(self.staff_b1)
        res = self.client.post(
            "/api/ai/chat/", {"message": "hello"}, format="json"
        )
        self.assertNotEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_cannot_access_admin_ai_features(self):
        self.client.force_authenticate(self.staff_b1)
        endpoints = [
            "/api/ai/insights/",
            "/api/ai/forecast/",
            "/api/ai/forecast-detail/",
            "/api/ai/recommendation/",
            "/api/ai/insights-summary/",
            "/api/ai/dashboard/",
            "/api/ai/business-intelligence/",
            "/api/ai/inventory-summary/",
            "/api/reports/",
            "/api/accounts/staff/",
            "/api/business/profile/",
        ]
        for url in endpoints:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, res.data)

    def test_staff_only_sees_own_organization(self):
        self.client.force_authenticate(self.staff_b1)
        res = self.client.get("/api/inventory/inventory/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 0)

        res = self.client.get(f"/api/inventory/inventory/{self.inventory_b2.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------ cross-tenant access blocked ------------------

    def test_b1_cannot_access_b2(self):
        self.client.force_authenticate(self.admin_b1)
        checks = [
            (f"/api/inventory/products/{self.product_b2.id}/", status.HTTP_404_NOT_FOUND),
            (f"/api/inventory/categories/{self.cat_b2.id}/", status.HTTP_404_NOT_FOUND),
            (f"/api/inventory/inventory/{self.inventory_b2.id}/", status.HTTP_404_NOT_FOUND),
            (f"/api/customers/customers/{self.customer_b2.id}/", status.HTTP_404_NOT_FOUND),
            (f"/api/suppliers/suppliers/{self.supplier_b2.id}/", status.HTTP_404_NOT_FOUND),
            (f"/api/sales/sales/{self.sale_b2.id}/", status.HTTP_404_NOT_FOUND),
            (f"/api/purchases/purchases/{self.purchase_b2.id}/", status.HTTP_404_NOT_FOUND),
            (f"/api/reports/{self.report_b2.id}/", status.HTTP_404_NOT_FOUND),
            (f"/api/ai/insights/{self.insight_b2.id}/", status.HTTP_404_NOT_FOUND),
        ]
        for url, expected in checks:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, expected, res.data)

    def test_b2_cannot_access_b1(self):
        self.client.force_authenticate(self.admin_b2)
        res = self.client.get("/api/inventory/products/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["sku"], "S30-B2")

    def test_b1_admin_cannot_update_b2_inventory(self):
        self.client.force_authenticate(self.admin_b1)
        res = self.client.post(
            f"/api/inventory/inventory/{self.inventory_b2.id}/adjust/",
            {"adjustment": 1, "reason": "hack"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.inventory_b2.refresh_from_db()
        self.assertEqual(self.inventory_b2.quantity, 50)

    def test_x_business_id_header_cannot_switch_tenant(self):
        self.client.force_authenticate(self.admin_b1)
        res = self.client.get(
            f"/api/inventory/products/{self.product_b2.id}/",
            HTTP_X_BUSINESS_ID=str(self.org_b2.id),
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------ tenant-scoped analytics ------------------

    def test_tenant_scoped_reports_remain_isolated(self):
        self.client.force_authenticate(self.admin_b2)
        res = self.client.get("/api/reports/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [r["title"] for r in res.data["results"]]
        self.assertEqual(titles, ["B2 Secret Report"])

        res = self.client.get("/api/reports/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_products"], 1)

    def test_tenant_scoped_ai_remains_isolated(self):
        self.client.force_authenticate(self.admin_b2)
        res = self.client.get("/api/ai/insights/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)

        self.client.force_authenticate(self.admin_b1)
        res = self.client.get("/api/ai/insights/")
        self.assertEqual(res.data["count"], 0)

    def test_inventory_remains_tenant_isolated(self):
        self.client.force_authenticate(self.admin_b2)
        res = self.client.get("/api/inventory/inventory/")
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["quantity"], 50)

        self.client.force_authenticate(self.admin_b1)
        res = self.client.get("/api/inventory/inventory/")
        self.assertEqual(res.data["count"], 0)

    def test_sales_and_purchases_remain_tenant_isolated(self):
        self.client.force_authenticate(self.admin_b2)
        res = self.client.get("/api/sales/sales/")
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["invoice_number"], "S30-SALE-B2")

        res = self.client.get("/api/purchases/purchases/")
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["invoice_number"], "S30-PUR-B2")

        self.client.force_authenticate(self.admin_b1)
        self.assertEqual(self.client.get("/api/sales/sales/").data["count"], 0)
        self.assertEqual(self.client.get("/api/purchases/purchases/").data["count"], 0)
