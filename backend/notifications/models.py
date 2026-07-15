from django.db import models

from core.models import TenantModel


class Notification(TenantModel):
    """
    Stores notifications for organizations/users.
    """

    TYPE_CHOICES = (
        ("LOW_STOCK", "Low Stock"),
        ("SYSTEM", "System"),
        ("SALE", "Sale"),
        ("PURCHASE", "Purchase"),
        ("AI", "AI Recommendation"),
    )

    title = models.CharField(
        max_length=255
    )

    message = models.TextField()

    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="SYSTEM"
    )

    is_read = models.BooleanField(
        default=False
    )

    created_for = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )


    class Meta:
        ordering = [
            "-created_at"
        ]


    def __str__(self):
        return self.title