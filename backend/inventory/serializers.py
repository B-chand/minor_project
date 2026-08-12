from rest_framework import serializers

from core.mixins import TenantScopedSerializerMixin

from .models import (
    Category,
    Product,
    Inventory,
    StockMovement,
)


class CategorySerializer(TenantScopedSerializerMixin):

    class Meta:
        model = Category
        fields = "__all__"

        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
        )


class ProductSerializer(TenantScopedSerializerMixin):

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

        if buying_price is not None and buying_price <= 0:
            raise serializers.ValidationError(
                {
                    "buying_price":
                    "Buying price must be greater than 0."
                }
            )

        if selling_price is not None and selling_price <= 0:
            raise serializers.ValidationError(
                {
                    "selling_price":
                    "Selling price must be greater than 0."
                }
            )

        if (
            buying_price is not None
            and selling_price is not None
            and selling_price < buying_price
        ):
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


class InventorySerializer(TenantScopedSerializerMixin):

    product_name = serializers.ReadOnlyField(
        source="product.name"
    )

    product_sku = serializers.ReadOnlyField(
        source="product.sku"
    )

    category_name = serializers.SerializerMethodField()

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

    def get_category_name(self, obj):
        category = obj.product.category
        return category.name if category else None

    def validate_quantity(self, value):
        raise serializers.ValidationError(
            "Quantity cannot be set directly. Use Opening Stock (IN), "
            "a Purchase, a Sale, or the Stock Adjustment action to change "
            "physical stock with a matching audit movement."
        )


ADJUSTMENT_REASONS = (
    ("Correction", "Correction (fix a data entry error)"),
    ("Damaged", "Damaged goods"),
    ("Lost", "Lost or missing stock"),
    ("Found", "Found or returned stock"),
    ("Physical Count", "Physical count difference"),
    ("Other", "Other reason"),
)


class AdjustStockSerializer(serializers.Serializer):
    """
    Validates a signed stock adjustment against an existing inventory item.

    ``adjustment`` is the signed delta applied to the backend's authoritative
    quantity. ``reason`` must come from the controlled list and ``note`` is
    required (and meaningful) when the reason is "Other".
    """

    adjustment = serializers.IntegerField()

    reason = serializers.ChoiceField(choices=ADJUSTMENT_REASONS)

    note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_adjustment(self, value):
        if isinstance(value, bool):
            raise serializers.ValidationError(
                "Adjustment must be an integer (it can be negative)."
            )

        if value == 0:
            raise serializers.ValidationError(
                "The adjustment amount cannot be zero."
            )

        return value

    def validate(self, attrs):
        if attrs.get("reason") == "Other":
            note = attrs.get("note", "").strip()

            if len(note) < 5:
                raise serializers.ValidationError(
                    "A note of at least 5 characters is required "
                    "when the reason is 'Other'."
                )

            attrs["note"] = note

        return attrs


class StockMovementSerializer(TenantScopedSerializerMixin):

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