from decimal import Decimal

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

        read_only_fields = (
            "subtotal",
        )

    def create(self, validated_data):

        from inventory.models import (
            Inventory,
            StockMovement,
        )

        purchase = validated_data["purchase"]
        product = validated_data["product"]
        quantity = validated_data["quantity"]
        unit_price = validated_data["unit_price"]

        # Calculate subtotal automatically
        validated_data["subtotal"] = (
            Decimal(quantity) * unit_price
        )

        # Create Purchase Item
        purchase_item = super().create(validated_data)

        # Update Purchase total amount
        total = sum(
            item.subtotal
            for item in purchase.items.all()
        )

        purchase.total_amount = total
        purchase.save(
            update_fields=["total_amount"]
        )

        # Update Inventory quantity
        inventory, created = Inventory.objects.get_or_create(
            product=product,
            organization=purchase.organization,
            defaults={
                "quantity": 0
            }
        )

        inventory.quantity += quantity

        inventory.save(
            update_fields=[
                "quantity"
            ]
        )

        # Create Stock Movement history
        StockMovement.objects.create(
            product=product,
            organization=purchase.organization,
            movement_type="IN",
            quantity=quantity,
            remarks="Purchase stock added",
            created_by=self.context["request"].user
        )

        return purchase_item


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
            "total_amount",
        )