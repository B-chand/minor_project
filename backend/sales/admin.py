from django.contrib import admin

from .models import (
    Sale,
    SaleItem,
)


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1



@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):

    list_display = (
        "invoice_number",
        "customer",
        "sale_date",
        "total_amount",
        "payment_status",
        "organization",
    )

    list_filter = (
        "payment_status",
        "organization",
    )

    search_fields = (
        "invoice_number",
        "customer__first_name",
        "customer__last_name",
    )

    inlines = [
        SaleItemInline,
    ]