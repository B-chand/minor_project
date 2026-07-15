from rest_framework import serializers

from .models import (
    Purchase,
    PurchaseItem,
)


class PurchaseItemSerializer(serializers.ModelSerializer):

    product_name = serializers.ReadOnlyField(
        source="product.name"
    )

    class Meta:
        model = PurchaseItem
        fields = "__all__"


class PurchaseSerializer(serializers.ModelSerializer):

    supplier_name = serializers.ReadOnlyField(
        source="supplier.name"
    )

    items = PurchaseItemSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Purchase
        fields = "__all__"

        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
        )