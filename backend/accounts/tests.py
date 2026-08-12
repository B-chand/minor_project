from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization

User = get_user_model()


class RegisterAndAuthTests(APITestCase):

    def test_register_creates_org_and_admin(self):
        url = "/api/accounts/register/"
        data = {
            "username": "admin1",
            "email": "admin1@test.com",
            "password": "secure-pass-123",
            "phone": "9800000000",
            "organization_name": "Acme Retail",
            "organization_email": "acme@test.com",
            "organization_phone": "9800000001",
            "organization_address": "Kathmandu",
        }

        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="admin1")
        self.assertEqual(user.role, "ADMIN")
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.name, "Acme Retail")

    def test_register_duplicate_organization_email_returns_400(self):
        Organization.objects.create(
            name="Existing Corp",
            email="existing@corp.com",
            phone="9800",
        )

        url = "/api/accounts/register/"
        data = {
            "username": "admin_dup",
            "email": "admin_dup@test.com",
            "password": "secure-pass-123",
            "phone": "9800000000",
            "organization_name": "Acme Retail",
            "organization_email": "existing@corp.com",
            "organization_phone": "9800000001",
        }

        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data["organization_email"],
            ["An organization with this email already exists."],
        )

    def test_register_duplicate_username_returns_field_error(self):
        Organization.objects.create(
            name="Seed Org",
            email="seed@corp.com",
            phone="9800",
        )
        User.objects.create_user(
            username="taken_user",
            email="taken@test.com",
            password="pass-123",
        )

        url = "/api/accounts/register/"
        data = {
            "username": "taken_user",
            "email": "new@test.com",
            "password": "secure-pass-123",
            "phone": "9800000000",
            "organization_name": "Acme Retail",
            "organization_email": "acme@corp.com",
            "organization_phone": "9800000001",
        }

        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data["username"],
            ["A user with that username already exists."],
        )

    def test_register_returns_generated_business_code(self):
        url = "/api/accounts/register/"
        data = {
            "username": "admin_gen",
            "email": "admin_gen@test.com",
            "password": "secure-pass-123",
            "phone": "9800000000",
            "organization_name": "Code Retail",
            "organization_email": "code@test.com",
            "organization_phone": "9800000001",
            "organization_address": "Kathmandu",
        }

        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        code = res.data.get("business_code")
        self.assertTrue(code)
        self.assertEqual(res.data.get("organization_code"), code)

        org = User.objects.get(username="admin_gen").organization
        self.assertEqual(org.code, code)

        # The generated code works for Business Admin login.
        login = self.client.post(
            "/api/token/",
            {
                "business_code": code,
                "username": "admin_gen",
                "password": "secure-pass-123",
            },
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_register_ignores_client_business_code_and_organization_id(self):
        url = "/api/accounts/register/"
        data = {
            "username": "admin_tamper",
            "email": "admin_tamper@test.com",
            "password": "secure-pass-123",
            "phone": "9800000000",
            "organization_name": "Tamper Retail",
            "organization_email": "tamperorg@test.com",
            "organization_phone": "9800000001",
            "business_code": "CUSTOM-EDITED",
            "organization_id": "00000000-0000-0000-0000-000000000001",
        }

        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

        org = User.objects.get(username="admin_tamper").organization
        # Client-supplied code/tenant are ignored; the server generates one.
        self.assertNotEqual(org.code, "CUSTOM-EDITED")
        self.assertTrue(org.code.startswith("B"))
        self.assertEqual(res.data["business_code"], org.code)

    def test_login_returns_tokens(self):
        org = Organization.objects.create(
            name="Corp", email="corp@test.com", phone="9800"
        )
        User.objects.create_user(
            username="boss",
            email="boss@test.com",
            password="pass-123",
            organization=org,
            role="ADMIN",
        )

        res = self.client.post(
            "/api/token/",
            {
                "business_code": org.code,
                "username": "boss",
                "password": "pass-123",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_current_user_requires_auth(self):
        res = self.client.get("/api/accounts/me/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class TenantIsolationTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(
            name="OrgA", email="a@test.com", phone="1"
        )
        cls.org_b = Organization.objects.create(
            name="OrgB", email="b@test.com", phone="2"
        )
        cls.admin_a = User.objects.create_user(
            username="admin_a", email="admina@test.com",
            password="pass-123", organization=cls.org_a, role="ADMIN",
        )
        cls.admin_b = User.objects.create_user(
            username="admin_b", email="adminb@test.com",
            password="pass-123", organization=cls.org_b, role="ADMIN",
        )

    def test_staff_list_is_scoped_to_org(self):
        self.client.force_authenticate(self.admin_a)
        self.client.post(
            "/api/accounts/staff/",
            {"username": "staff_a", "email": "staffa@test.com",
             "password": "pass-123", "phone": "555"},
            format="json",
        )
        res = self.client.get("/api/accounts/staff/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        names = [u["username"] for u in res.data["results"]]
        self.assertIn("staff_a", names)
        self.assertNotIn("staff_b", names)

    def test_customers_are_scoped_to_org(self):
        self.client.force_authenticate(self.admin_b)
        self.client.post(
            "/api/customers/customers/",
            {"first_name": "Bob", "phone": "9800000002"},
            format="json",
        )

        self.client.force_authenticate(self.admin_a)
        res = self.client.get("/api/customers/customers/")
        self.assertEqual(res.data["count"], 0)