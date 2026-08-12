from decimal import Decimal

from rest_framework import serializers

from core.mixins import TenantScopedSerializerMixin

from .models import (
    Sale,
    SaleItem,
)

from notifications.services import create_notification


class SaleItemSerializer(TenantScopedSerializerMixin):

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


        sale = validated_data["sale"]
        product = validated_data["product"]
        quantity = validated_data["quantity"]
        unit_price = validated_data["unit_price"]


        # Calculate subtotal
        validated_data["subtotal"] = (
            Decimal(quantity) * unit_price
        )


        with transaction.atomic():

            # Lock the inventory row and check stock inside the transaction so
            # concurrent sale requests cannot oversell the same product.
            try:

                inventory = (
                    Inventory.objects
                    .select_for_update()
                    .get(
                        product=product,
                        organization=sale.organization
                    )
                )

            except Inventory.DoesNotExist:

                raise serializers.ValidationError(
                    {
                        "product":
                        "Inventory record does not exist for this product."
                    }
                )


            # Check available stock
            if inventory.quantity < quantity:

                raise serializers.ValidationError(
                    {
                        "quantity":
                        f"Only {inventory.quantity} items are available in stock."
                    }
                )


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
                    "total_amount",
                    "payment_status",
                ]
            )


            # Reduce inventory
            inventory.quantity -= quantity

            inventory.save(
                update_fields=[
                    "quantity",
                    "updated_at",
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


            # ==========================
            # SALE NOTIFICATION
            # ==========================

            create_notification(
                organization=sale.organization,
                user=self.context["request"].user,
                title="Sale Completed",
                message=(
                    f"{quantity} units of {product.name} "
                    "sold successfully."
                ),
                notification_type="SALE"
            )


            # ==========================
            # STOCK ALERTS
            # ==========================

            if inventory.quantity == 0:

                create_notification(
                    organization=sale.organization,
                    user=self.context["request"].user,
                    title="Out of Stock",
                    message=f"{product.name} is now out of stock.",
                    notification_type="OUT_OF_STOCK"
                )


            elif inventory.quantity <= inventory.minimum_stock:

                create_notification(
                    organization=sale.organization,
                    user=self.context["request"].user,
                    title="Low Stock Alert",
                    message=(
                        f"{product.name} stock is low. "
                        f"Remaining quantity: {inventory.quantity}"
                    ),
                    notification_type="LOW_STOCK"
                )


        return sale_item



class SaleSerializer(TenantScopedSerializerMixin):

    customer_name = serializers.ReadOnlyField(
        source="customer.first_name"
    )

    payment_status = serializers.SerializerMethodField()

    remaining_amount = serializers.SerializerMethodField()

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


    def get_payment_status(self, obj):
        return obj.computed_payment_status()


    def get_remaining_amount(self, obj):
        return obj.remaining_amount()


    def validate_amount_paid(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Paid amount cannot be negative."
            )

        if self.instance is not None and value > self.instance.total_amount:
            raise serializers.ValidationError(
                "Paid amount cannot exceed the invoice total."
            )

        return value


class RecordPaymentSerializer(serializers.Serializer):
    """
    Validates a single payment received toward a sale invoice.

    Only the request body is validated here; sale-specific constraints
    (already-paid state, remaining balance) are enforced in the view inside
    a transaction with a row lock.
    """

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Payment amount must be greater than zero."
            )
        return value


    def validate_invoice_number(self, value):

        request = self.context["request"]


        queryset = Sale.objects.filter(
            organization=request.user.organization,
            invoice_number=value
        )


        if self.instance:

            queryset = queryset.exclude(
                pk=self.instance.pk
            )


        if queryset.exists():

            raise serializers.ValidationError(
                "A sale with this invoice number already exists."
            )


        return value