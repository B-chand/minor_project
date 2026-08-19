from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Organization

from .models import BusinessProfile

User = get_user_model()


class BusinessProfileOrganizationInfoTests(APITestCase):
    """
    The Business Profile page shows the logged-in tenant's existing
    organization details (name, email, phone, address) and lets the
    organization admin edit them. Existing settings (currency, invoice
    prefix, PAN/VAT, website, business type) keep working, tenant isolation
    is preserved, and non-admin users cannot modify organization info.
    """

    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(
            name="Alpha Traders",
            email="alpha@test.com",
            phone="9800000001",
            address="Kathmandu",
        )
        cls.org_b = Organization.objects.create(
            name="Omega Store",
            email="omega@test.com",
            phone="9800000002",
            address="Pokhara",
        )
        cls.admin_a = User.objects.create_user(
            username="admin_a", email="admin_a@test.com", password="pass-123",
            organization=cls.org_a, role="ADMIN",
        )
        cls.admin_b = User.objects.create_user(
            username="admin_b", email="admin_b@test.com", password="pass-123",
            organization=cls.org_b, role="ADMIN",
        )
        cls.staff_a = User.objects.create_user(
            username="staff_a", email="staff_a@test.com", password="pass-123",
            organization=cls.org_a, role="STAFF",
        )

    def setUp(self):
        self.client.force_authenticate(self.admin_a)

    # ----------------------- profile creation -------------------------

    def test_create_profile_preserves_existing_organization_details(self):
        res = self.client.post(
            "/api/business/profile/",
            {
                "organization_name": "Alpha Traders",
                "organization_email": "alpha@test.com",
                "organization_phone": "9800000001",
                "organization_address": "Kathmandu",
                "business_type": "RETAIL",
                "invoice_prefix": "INV",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        profile = BusinessProfile.objects.get(pk=res.data["id"])
        self.assertEqual(profile.organization, self.org_a)
        self.org_a.refresh_from_db()
        self.assertEqual(self.org_a.name, "Alpha Traders")
        self.assertEqual(self.org_a.email, "alpha@test.com")
        self.assertEqual(self.org_a.phone, "9800000001")
        self.assertEqual(self.org_a.address, "Kathmandu")

    def test_create_profile_updates_organization_details(self):
        res = self.client.post(
            "/api/business/profile/",
            {
                "organization_name": "Alpha Traders HQ",
                "organization_email": "hq@alpha.com",
                "organization_phone": "9800000111",
                "organization_address": "Lalitpur",
                "business_type": "WHOLESALE",
                "invoice_prefix": "AT",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        profile = BusinessProfile.objects.get(pk=res.data["id"])
        self.assertEqual(profile.organization, self.org_a)
        self.org_a.refresh_from_db()
        self.assertEqual(self.org_a.name, "Alpha Traders HQ")
        self.assertEqual(self.org_a.email, "hq@alpha.com")
        self.assertEqual(self.org_a.phone, "9800000111")
        self.assertEqual(self.org_a.address, "Lalitpur")

    # ------------------------ profile reading -------------------------

    def test_get_profile_returns_organization_details(self):
        BusinessProfile.objects.create(
            organization=self.org_a,
            business_type="RETAIL",
            invoice_prefix="INV",
            pan_number="PAN-A",
            vat_number="VAT-A",
            website="https://alpha.com",
            currency="NPR",
        )
        res = self.client.get("/api/business/profile/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["count"], 1)
        item = res.data["results"][0]
        self.assertEqual(item["organization_name"], "Alpha Traders")
        self.assertEqual(item["organization_email"], "alpha@test.com")
        self.assertEqual(item["organization_phone"], "9800000001")
        self.assertEqual(item["organization_address"], "Kathmandu")
        self.assertEqual(item["business_type"], "RETAIL")
        self.assertEqual(item["invoice_prefix"], "INV")
        self.assertEqual(item["pan_number"], "PAN-A")
        self.assertEqual(item["vat_number"], "VAT-A")
        self.assertEqual(item["website"], "https://alpha.com")
        self.assertEqual(item["currency"], "NPR")

    # ------------------------ profile updating ------------------------

    def test_update_profile_updates_organization_details(self):
        profile = BusinessProfile.objects.create(
            organization=self.org_a,
            business_type="RETAIL",
            invoice_prefix="INV",
        )
        res = self.client.patch(
            f"/api/business/profile/{profile.id}/",
            {
                "organization_name": "Alpha Traders Renamed",
                "organization_email": "renamed@alpha.com",
                "organization_phone": "9800000222",
                "organization_address": "Baneshwor",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.org_a.refresh_from_db()
        self.assertEqual(self.org_a.name, "Alpha Traders Renamed")
        self.assertEqual(self.org_a.email, "renamed@alpha.com")
        self.assertEqual(self.org_a.phone, "9800000222")
        self.assertEqual(self.org_a.address, "Baneshwor")

    def test_update_profile_keeps_existing_settings(self):
        profile = BusinessProfile.objects.create(
            organization=self.org_a,
            business_type="SERVICE",
            invoice_prefix="SV",
            pan_number="PAN-1",
            vat_number="VAT-1",
            website="https://alpha.com",
            currency="NPR",
        )
        res = self.client.patch(
            f"/api/business/profile/{profile.id}/",
            {"organization_name": "Alpha Renamed"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        profile.refresh_from_db()
        self.assertEqual(profile.organization, self.org_a)
        self.assertEqual(profile.business_type, "SERVICE")
        self.assertEqual(profile.invoice_prefix, "SV")
        self.assertEqual(profile.pan_number, "PAN-1")
        self.assertEqual(profile.vat_number, "VAT-1")
        self.assertEqual(profile.website, "https://alpha.com")
        self.assertEqual(profile.currency, "NPR")
        self.org_a.refresh_from_db()
        self.assertEqual(self.org_a.name, "Alpha Renamed")

    def test_duplicate_organization_email_is_rejected(self):
        profile = BusinessProfile.objects.create(organization=self.org_a)
        res = self.client.patch(
            f"/api/business/profile/{profile.id}/",
            {"organization_email": "omega@test.com"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", res.data["organization_email"][0])
        self.org_a.refresh_from_db()
        self.assertEqual(self.org_a.email, "alpha@test.com")

    def test_same_email_on_own_organization_is_allowed(self):
        profile = BusinessProfile.objects.create(organization=self.org_a)
        res = self.client.patch(
            f"/api/business/profile/{profile.id}/",
            {
                "organization_name": "Alpha Traders",
                "organization_email": "alpha@test.com",
                "organization_phone": "9800000001",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

    # ------------------------ tenant isolation ------------------------

    def test_cannot_access_other_organization_profile(self):
        profile_b = BusinessProfile.objects.create(organization=self.org_b)
        res = self.client.get(f"/api/business/profile/{profile_b.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_update_other_organization_through_forged_profile_id(self):
        profile_b = BusinessProfile.objects.create(
            organization=self.org_b,
            business_type="RETAIL",
        )
        res = self.client.patch(
            f"/api/business/profile/{profile_b.id}/",
            {"organization_name": "Hacked Store"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.org_b.refresh_from_db()
        self.assertEqual(self.org_b.name, "Omega Store")

    def test_forged_organization_field_is_ignored(self):
        profile = BusinessProfile.objects.create(organization=self.org_a)
        res = self.client.patch(
            f"/api/business/profile/{profile.id}/",
            {
                "organization_name": "Own Name",
                "organization": self.org_b.id,
                "organization_id": self.org_b.id,
                "tenant_id": self.org_b.id,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        profile.refresh_from_db()
        self.assertEqual(profile.organization, self.org_a)
        self.org_a.refresh_from_db()
        self.assertEqual(self.org_a.name, "Own Name")
        self.org_b.refresh_from_db()
        self.assertEqual(self.org_b.name, "Omega Store")

    def test_own_profile_update_never_touches_other_organization(self):
        profile = BusinessProfile.objects.create(organization=self.org_a)
        self.client.patch(
            f"/api/business/profile/{profile.id}/",
            {
                "organization_name": "Changed",
                "organization_email": "changed@alpha.com",
                "organization_phone": "9800000333",
                "organization_address": "New Address",
            },
            format="json",
        )
        self.org_b.refresh_from_db()
        self.assertEqual(self.org_b.name, "Omega Store")
        self.assertEqual(self.org_b.email, "omega@test.com")
        self.assertEqual(self.org_b.phone, "9800000002")
        self.assertEqual(self.org_b.address, "Pokhara")

    # ------------------------- role-based access ----------------------

    def test_staff_cannot_access_business_profile(self):
        self.client.force_authenticate(self.staff_a)
        for method in ("get", "post", "patch"):
            with self.subTest(method=method):
                if method == "get":
                    res = self.client.get("/api/business/profile/")
                elif method == "post":
                    res = self.client.post("/api/business/profile/", {}, format="json")
                else:
                    res = self.client.patch(
                        "/api/business/profile/00000000-0000-0000-0000-000000000001/",
                        {"organization_name": "x"},
                        format="json",
                    )
                self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_cannot_modify_organization_details(self):
        self.client.force_authenticate(self.staff_a)
        profile = BusinessProfile.objects.create(organization=self.org_a)
        res = self.client.patch(
            f"/api/business/profile/{profile.id}/",
            {"organization_name": "Staff Hijack"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.org_a.refresh_from_db()
        self.assertEqual(self.org_a.name, "Alpha Traders")

    # ------------------- authenticated-user relationship ---------------

    def test_current_user_exposes_organization_details(self):
        res = self.client.get("/api/accounts/me/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["organization"], "Alpha Traders")
        self.assertEqual(res.data["organization_email"], "alpha@test.com")
        self.assertEqual(res.data["organization_phone"], "9800000001")
        self.assertEqual(res.data["organization_address"], "Kathmandu")