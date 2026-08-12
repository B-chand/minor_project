from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization
from customers.models import Customer

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


class BusinessCodeLoginTests(APITestCase):
    """Business Code + Username + Password authentication."""

    @classmethod
    def setUpTestData(cls):
        cls.org_b1 = _mk_org("B1", "Alpha Traders", "alpha@test.com")
        cls.org_b2 = _mk_org("B2", "Omega Store", "omega@test.com")

        cls.admin_b1 = _mk_user(
            "admin", "admin@alpha.com", cls.org_b1, role="ADMIN"
        )
        cls.staff_b1 = _mk_user(
            "staff01", "staff01@alpha.com", cls.org_b1, role="STAFF"
        )
        # Usernames are globally unique in this system, so the second
        # tenant uses its own distinct username.
        cls.staff_b2 = _mk_user(
            "staff02", "staff02@omega.com", cls.org_b2, role="STAFF"
        )

    def _login(self, business_code, username, password):
        return self.client.post(
            "/api/token/",
            {"business_code": business_code, "username": username, "password": password},
            format="json",
        )

    def test_business_code_username_password_login_succeeds(self):
        res = self._login("B1", "admin", "pass-123")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_login_returns_role_and_business_code(self):
        res = self._login("B1", "staff01", "pass-123")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["user"]["username"], "staff01")
        self.assertEqual(res.data["user"]["role"], "STAFF")
        self.assertEqual(res.data["user"]["business_code"], "B1")
        self.assertEqual(res.data["user"]["organization"], "Alpha Traders")
        self.assertEqual(res.data["user"]["organization_id"], str(self.org_b1.id))

    def test_login_is_scoped_to_the_selected_business(self):
        # Each tenant's credentials only ever authenticate inside that
        # tenant; usernames are globally unique in this system.
        res_b1 = self._login("B1", "staff01", "pass-123")
        self.assertEqual(res_b1.status_code, status.HTTP_200_OK)
        self.assertEqual(res_b1.data["user"]["business_code"], "B1")

        res_b2 = self._login("B2", "staff02", "pass-123")
        self.assertEqual(res_b2.status_code, status.HTTP_200_OK)
        self.assertEqual(res_b2.data["user"]["business_code"], "B2")
        self.assertNotEqual(
            res_b1.data["user"]["organization_id"],
            res_b2.data["user"]["organization_id"],
        )

        # B1's staff credentials must never authenticate inside B2.
        res_cross = self._login("B2", "staff01", "pass-123")
        self.assertEqual(res_cross.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_business_code_rejected(self):
        res = self._login("B9", "staff01", "pass-123")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_business_code_is_case_insensitive(self):
        res = self._login("b1", "admin", "pass-123")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_wrong_password_rejected(self):
        res = self._login("B1", "admin", "wrong-password")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_username_not_in_business_rejected(self):
        res = self._login("B1", "ghost", "pass-123")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_from_b1_cannot_authenticate_as_b2_user(self):
        # B1-only users must not authenticate inside the B2 tenant.
        res = self._login("B2", "staff01", "pass-123")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        forged = self._login("B2", "admin", "pass-123")
        self.assertEqual(forged.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_before_login_token_identifies_authoritative_tenant(self):
        res = self._login("B1", "admin", "pass-123")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # The token carries the authenticated organization (never client data).
        self.assertEqual(
            res.data["user"]["organization_id"], str(self.org_b1.id)
        )

    def test_super_admin_cannot_login_without_business_code(self):
        # Super Admin / organization-less users are not part of the
        # application login flow; every API login needs a business code.
        User.objects.create_superuser(
            username="root", email="root@system.com", password="root-pass"
        )
        res = self._login("", "root", "root-pass")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_business_user_without_business_code_rejected(self):
        res = self._login("", "admin", "pass-123")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class RoleBasedAccessTests(APITestCase):
    """
    Staff cannot reach admin-only modules even through direct API calls;
    Business Admins keep full access to their own business.
    """

    @classmethod
    def setUpTestData(cls):
        cls.org_a = _mk_org("B10", "TenantA", "tenanta@test.com")
        cls.org_b = _mk_org("B11", "TenantB", "tenantb@test.com")
        cls.admin_a = _mk_user("admin-a", "admina@tenanta.com", cls.org_a, role="ADMIN")
        cls.staff_a = _mk_user("staff-a", "staffa@tenanta.com", cls.org_a, role="STAFF")
        cls.admin_b = _mk_user("admin-b", "adminb@tenantb.com", cls.org_b, role="ADMIN")

    def setUp(self):
        self.client.force_authenticate(self.staff_a)

    # ---------------------- staff blocked from admin modules ----------------------

    def test_staff_cannot_access_saved_reports(self):
        res = self.client.get("/api/reports/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res = self.client.post("/api/reports/", {"title": "X", "report_type": "SALES"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_cannot_delete_or_view_saved_reports(self):
        from reports.models import Report

        report = Report.objects.create(
            organization=self.org_a, title="Confidential",
            report_type="SALES", generated_by=self.admin_a,
        )
        self.assertEqual(
            self.client.get(f"/api/reports/{report.id}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(f"/api/reports/{report.id}/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_can_still_use_dashboard_feed_reports(self):
        # Dashboard data (two-bar chart) is an operational view, not the
        # restricted Reports / Saved Reports module.
        res = self.client.get("/api/reports/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res = self.client.get("/api/reports/sales/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_staff_cannot_access_ai_endpoints(self):
        endpoints = [
            "/api/ai/insights/",
            "/api/ai/forecast/",
            "/api/ai/forecast-detail/",
            "/api/ai/recommendation/",
            "/api/ai/insights-summary/",
            "/api/ai/dashboard/",
            "/api/ai/business-intelligence/",
            "/api/ai/inventory-summary/",
        ]
        for url in endpoints:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_access_ai_chat(self):
        # Staff may use the tenant-scoped AI chat, but never the admin-only
        # AI modules above.
        res = self.client.post(
            "/api/ai/chat/", {"message": "hello"}, format="json"
        )
        self.assertNotEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_cannot_manage_users(self):
        res = self.client.get("/api/accounts/staff/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res = self.client.post(
            "/api/accounts/staff/",
            {"username": "hacker", "email": "h@test.com", "password": "x"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_cannot_access_business_settings(self):
        res = self.client.get("/api/business/profile/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ---------------------- business admin can access business modules ----------------------

    def test_business_admin_can_access_business_modules(self):
        self.client.force_authenticate(self.admin_a)

        self.assertEqual(
            self.client.get("/api/inventory/products/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get("/api/reports/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get("/api/ai/insights/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get("/api/accounts/staff/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get("/api/business/profile/").status_code,
            status.HTTP_200_OK,
        )

    def test_business_admin_can_create_staff_in_own_business(self):
        self.client.force_authenticate(self.admin_a)
        res = self.client.post(
            "/api/accounts/staff/",
            {
                "username": "new-staff",
                "email": "new@tenanta.com",
                "password": "secret-1",
                "phone": "9800000111",
                "organization": self.org_b.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        created = User.objects.get(pk=res.data["id"])
        # Client-supplied organization is ignored; staff lands in admin A's org.
        self.assertEqual(created.organization, self.org_a)
        self.assertEqual(created.role, "STAFF")

    # ---------------------- tenant isolation remains authoritative ----------------------

    def test_cross_tenant_access_remains_blocked(self):
        from inventory.models import Product

        product_b = Product.objects.create(
            organization=self.org_b, name="Foreign",
            sku="RBAC-FOREIGN", buying_price="1", selling_price="2",
        )
        self.client.force_authenticate(self.admin_a)
        res = self.client.get(f"/api/inventory/products/{product_b.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_organization_id_in_body_cannot_bypass_tenant_isolation(self):
        self.client.force_authenticate(self.admin_a)
        res = self.client.post(
            "/api/customers/customers/",
            {
                "first_name": "Tamper",
                "last_name": "Guy",
                "phone": "9800000222",
                "email": "tamper@test.com",
                "organization": self.org_b.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        customer = Customer.objects.get(pk=res.data["id"])
        self.assertEqual(customer.organization, self.org_a)

    def test_staff_body_tenant_ids_do_not_switch_tenant(self):
        res = self.client.post(
            "/api/customers/customers/",
            {
                "first_name": "Staffer",
                "phone": "9800000333",
                "organization": self.org_b.id,
                "business_code": "B11",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        customer = Customer.objects.get(pk=res.data["id"])
        self.assertEqual(customer.organization, self.org_a)

    def test_admin_access_itself_is_org_scoped(self):
        self.client.force_authenticate(self.admin_b)
        self.assertEqual(
            self.client.get("/api/accounts/staff/").status_code,
            status.HTTP_200_OK,
        )