from django.contrib import admin

from .models import (
    Category,
    Product,
    Inventory,
    StockMovement,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "organization",
        "created_at",
    )

    list_filter = (
        "organization",
    )

    search_fields = (
        "name",
    )



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "sku",
        "category",
        "buying_price",
        "selling_price",
        "organization",
        "is_active",
    )

    list_filter = (
        "category",
        "organization",
        "is_active",
    )

    search_fields = (
        "name",
        "sku",
        "barcode",
    )



@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "quantity",
        "minimum_stock",
        "maximum_stock",
        "organization",
    )

    list_filter = (
        "organization",
    )

    search_fields = (
        "product__name",
    )



@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "movement_type",
        "quantity",
        "created_by",
        "organization",
        "created_at",
    )

    list_filter = (
        "movement_type",
        "organization",
    )

    search_fields = (
        "product__name",
        "remarks",
    )