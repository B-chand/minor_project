from django.contrib import admin

from .models import BusinessProfile


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):

    list_display = (
        "organization",
        "business_type",
        "currency",
        "invoice_prefix",
    )

    list_filter = (
        "business_type",
        "currency",
    )

    search_fields = (
        "organization__name",
        "pan_number",
        "vat_number",
    )