from django.db import models

from core.models import TenantModel


class Customer(TenantModel):
    """
    Customer information.
    Every customer belongs to one organization (tenant).
    """

    first_name = models.CharField(
        max_length=100
    )

    last_name = models.CharField(
        max_length=100,
        blank=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    phone = models.CharField(
        max_length=20
    )

    address = models.TextField(
        blank=True
    )

    loyalty_points = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )


    class Meta:
        ordering = [
            "first_name",
            "last_name",
        ]

        unique_together = (
            "organization",
            "phone",
        )


    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()