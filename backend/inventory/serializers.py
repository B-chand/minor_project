from rest_framework import serializers

from .models import (
    Category,
    Product,
    Inventory,
    StockMovement,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
        )


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
        )


class InventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    stock_status = serializers.ReadOnlyField()

    class Meta:
        model = Inventory
        fields = "__all__"
        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
            "stock_status",
        )


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    created_by_name = serializers.CharField(
        source="created_by.username",
        read_only=True
    )

    class Meta:
        model = StockMovement
        fields = "__all__"
        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
            "created_by",
        )