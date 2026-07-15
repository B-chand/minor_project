from django.db import models

from core.models import TenantModel


class BusinessProfile(TenantModel):
    """
    Stores business-specific information.
    """

    BUSINESS_TYPES = (
        ("RETAIL", "Retail"),
        ("WHOLESALE", "Wholesale"),
        ("MANUFACTURING", "Manufacturing"),
        ("SERVICE", "Service"),
    )

    business_type = models.CharField(
        max_length=50,
        choices=BUSINESS_TYPES,
        default="RETAIL"
    )

    pan_number = models.CharField(
        max_length=50,
        blank=True
    )

    vat_number = models.CharField(
        max_length=50,
        blank=True
    )

    website = models.URLField(
        blank=True
    )

    currency = models.CharField(
        max_length=10,
        default="NPR"
    )

    invoice_prefix = models.CharField(
        max_length=20,
        default="INV"
    )


    def __str__(self):
        return self.organization.name