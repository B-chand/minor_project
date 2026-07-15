from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "report_type",
        "generated_by",
        "organization",
        "created_at",
    )

    list_filter = (
        "report_type",
        "organization",
    )

    search_fields = (
        "title",
        "description",
    )