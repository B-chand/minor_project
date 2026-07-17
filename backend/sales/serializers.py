from decimal import Decimal

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

        read_only_fields = (
            "subtotal",
        )


    def create(self, validated_data):

        from django.db import transaction
        from inventory.models import (
            Inventory,
            StockMovement,
        )
        from rest_framework.exceptions import ValidationError


        sale = validated_data["sale"]
        product = validated_data["product"]
        quantity = validated_data["quantity"]
        unit_price = validated_data["unit_price"]


        # Check inventory exists
        try:
            inventory = Inventory.objects.get(
                product=product,
                organization=sale.organization
            )

        except Inventory.DoesNotExist:
            raise ValidationError(
                "Inventory record does not exist for this product."
            )


        # Check available stock
        if inventory.quantity < quantity:
            raise ValidationError(
                f"Not enough stock. Available quantity: {inventory.quantity}"
            )


        # Calculate subtotal
        validated_data["subtotal"] = (
            Decimal(quantity) * unit_price
        )


        with transaction.atomic():

            # Create Sale Item
            sale_item = super().create(
                validated_data
            )


            # Update Sale total
            total = sum(
                item.subtotal
                for item in sale.items.all()
            )

            sale.total_amount = total

            sale.save(
                update_fields=[
                    "total_amount"
                ]
            )


            # Reduce inventory
            inventory.quantity -= quantity

            inventory.save(
                update_fields=[
                    "quantity"
                ]
            )


            # Create stock movement
            StockMovement.objects.create(
                product=product,
                organization=sale.organization,
                movement_type="OUT",
                quantity=quantity,
                remarks="Sale stock removed",
                created_by=self.context["request"].user
            )


        return sale_item



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
            "total_amount",
        )