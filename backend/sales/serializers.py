from rest_framework import serializers

from .models import (
    Sale,
    SaleItem,
)


class SaleItemSerializer(serializers.ModelSerializer):

    product_name = serializers.ReadOnlyField(
        source="product.name"
    )

    class Meta:
        model = SaleItem

        fields = "__all__"


class SaleSerializer(serializers.ModelSerializer):

    customer_name = serializers.ReadOnlyField(
        source="customer.first_name"
    )

    items = SaleItemSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Sale

        fields = "__all__"

        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
        )