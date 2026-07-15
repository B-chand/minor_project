from django.contrib import admin

from .models import AIInsight


@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "insight_type",
        "confidence_score",
        "organization",
        "created_at",
    )

    list_filter = (
        "insight_type",
        "organization",
    )

    search_fields = (
        "title",
        "description",
    )