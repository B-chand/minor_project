from django.db import models

from core.models import TenantModel


class Report(TenantModel):
    """
    Stores generated reports.
    """

    REPORT_TYPES = (
        ("SALES", "Sales Report"),
        ("PURCHASE", "Purchase Report"),
        ("INVENTORY", "Inventory Report"),
        ("CUSTOMER", "Customer Report"),
    )

    title = models.CharField(
        max_length=255
    )

    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPES
    )

    description = models.TextField(
        blank=True
    )

    generated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True
    )


    class Meta:
        ordering = [
            "-created_at"
        ]


    def __str__(self):
        return self.title