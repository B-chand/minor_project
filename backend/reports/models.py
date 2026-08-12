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

    report_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Stores the useful report configuration/content snapshot "
            "(rows, filters, generated_at) that makes a saved report "
            "re-viewable later."
        ),
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