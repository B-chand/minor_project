import uuid

from django.db import models


class BaseModel(models.Model):
    """
    Base model containing common timestamp fields.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organization(BaseModel):
    """
    Represents a tenant (organization).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)

    address = models.TextField(blank=True)

    logo = models.ImageField(
        upload_to="organization_logos/",
        blank=True,
        null=True
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text=(
            "Unique Business Code (e.g. B1) that identifies this "
            "tenant/organization at login."
        ),
    )

    is_active = models.BooleanField(default=True)

    def _next_code(self):
        """
        Assign the next sequential business code (``B<n>``) that is not
        already in use. Existing explicit codes are respected.
        """

        prefix = "B"
        max_number = 0

        codes = (
            Organization.objects
            .exclude(code__isnull=True)
            .exclude(code="")
            .values_list("code", flat=True)
        )

        for value in codes:
            suffix = value[len(prefix):] if value.startswith(prefix) else ""
            if suffix.isdigit():
                max_number = max(int(suffix), max_number)

        return f"{prefix}{max_number + 1}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._next_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TenantModel(BaseModel):
    """
    Every tenant-owned model inherits from this.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="%(class)ss"
    )

    class Meta:
        abstract = True