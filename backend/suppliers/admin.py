from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "phone",
        "email",
        "organization",
        "is_active",
    )

    search_fields = (
        "name",
        "phone",
        "email",
    )

    list_filter = (
        "organization",
        "is_active",
    )