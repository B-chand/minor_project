from django.db import models

from core.models import TenantModel


class AIInsight(TenantModel):
    """
    Stores AI generated business insights.
    """

    INSIGHT_TYPES = (
        ("FORECAST", "Demand Forecast"),
        ("LOW_STOCK", "Low Stock Prediction"),
        ("RECOMMENDATION", "Inventory Recommendation"),
        ("ANALYSIS", "Business Analysis"),
    )


    title = models.CharField(
        max_length=255
    )


    description = models.TextField()


    insight_type = models.CharField(
        max_length=30,
        choices=INSIGHT_TYPES
    )


    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )


    generated_by = models.CharField(
        max_length=50,
        default="AI"
    )


    is_active = models.BooleanField(
        default=True
    )


    class Meta:
        ordering = [
            "-created_at"
        ]


    def __str__(self):
        return self.title