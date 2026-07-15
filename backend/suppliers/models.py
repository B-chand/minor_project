from django.db import models

from core.models import TenantModel


class Supplier(TenantModel):
    """
    Supplier information.
    """

    name = models.CharField(max_length=255)

    email = models.EmailField(
        blank=True,
        null=True
    )

    phone = models.CharField(max_length=20)

    address = models.TextField(blank=True)

    contact_person = models.CharField(
        max_length=255,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = (
            "organization",
            "phone",
        )

    def __str__(self):
        return self.name