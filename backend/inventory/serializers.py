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

    def validate(self, attrs):

        buying_price = attrs.get("buying_price")
        selling_price = attrs.get("selling_price")

        if buying_price <= 0:
            raise serializers.ValidationError(
                {
                    "buying_price":
                    "Buying price must be greater than 0."
                }
            )

        if selling_price <= 0:
            raise serializers.ValidationError(
                {
                    "selling_price":
                    "Selling price must be greater than 0."
                }
            )

        if selling_price < buying_price:
            raise serializers.ValidationError(
                {
                    "selling_price":
                    "Selling price cannot be less than buying price."
                }
            )

        return attrs

    def validate_sku(self, value):

        request = self.context["request"]

        queryset = Product.objects.filter(
            organization=request.user.organization,
            sku=value
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "A product with this SKU already exists."
            )

        return value


class InventorySerializer(serializers.ModelSerializer):

    product_name = serializers.ReadOnlyField(
        source="product.name"
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

    product_name = serializers.ReadOnlyField(
        source="product.name"
    )

    created_by_name = serializers.ReadOnlyField(
        source="created_by.username"
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