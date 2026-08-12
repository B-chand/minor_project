from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import status
from rest_framework.response import Response

from django.db import transaction
from django.db.models import F, Q

from .models import (
    Category,
    Product,
    Inventory,
    StockMovement,
)

from .serializers import (
    CategorySerializer,
    ProductSerializer,
    InventorySerializer,
    StockMovementSerializer,
    AdjustStockSerializer,
)


class TenantViewSet(ModelViewSet):
    """
    Base ViewSet for tenant-owned models.
    Automatically filters data by organization.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        organization = getattr(user, "organization", None)

        if not organization:
            return self.queryset.none()

        return self.queryset.filter(
            organization=organization
        )

    def perform_create(self, serializer):
        organization = getattr(self.request.user, "organization", None)

        if not organization:
            raise ValidationError(
                {
                    "organization": (
                        "The authenticated user is not assigned to an organization."
                    )
                }
            )

        serializer.save(
            organization=organization
        )


class CategoryViewSet(TenantViewSet):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(TenantViewSet):

    queryset = Product.objects.select_related(
        "category"
    ).all()

    serializer_class = ProductSerializer

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "name",
        "sku",
        "barcode",
        "description",
        "category__name",
    ]

    filterset_fields = [
        "category",
        "is_active",
    ]

    ordering_fields = [
        "name",
        "buying_price",
        "selling_price",
        "created_at",
    ]

    ordering = [
        "name",
    ]

    def destroy(self, request, *args, **kwargs):

        product = self.get_object()

        try:
            inventory = product.inventory

            if inventory.quantity > 0:
                return Response(
                    {
                        "error":
                        "Cannot delete a product that still has inventory."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Inventory.DoesNotExist:
            pass

        return super().destroy(
            request,
            *args,
            **kwargs
        )

class InventoryViewSet(TenantViewSet):

    queryset = Inventory.objects.select_related(
        "product"
    ).all()

    serializer_class = InventorySerializer

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "product__name",
        "product__sku",
        "product__barcode",
        "product__category__name",
    ]

    filterset_fields = [
        "product__category",
    ]

    ordering_fields = [
        "product__name",
        "quantity",
        "minimum_stock",
        "maximum_stock",
        "created_at",
    ]

    ordering = [
        "product__name",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()

        stock_status = self.request.query_params.get("stock_status")
        if stock_status:
            domain = self._resolve_stock_status_domain(stock_status)
            if domain is not None:
                queryset = queryset.filter(domain)

        return queryset

    @staticmethod
    def _resolve_stock_status_domain(value):
        """
        Mirrors the ``Inventory.stock_status`` property exactly:
        equal-to-zero counts as Out, anything at or below the minimum
        threshold counts as Low, everything else is In Stock.
        """
        key = value.lower().strip()

        if key in ("out", "out-of-stock", "out of stock", "0"):
            return Q(quantity=0)

        if key in ("low", "low-stock", "low stock"):
            return Q(quantity__gt=0, quantity__lte=F("minimum_stock"))

        if key in ("in", "in-stock", "in stock"):
            return Q(quantity__gt=F("minimum_stock"))

        return None

    @action(detail=True, methods=["post"], url_path="adjust")
    def adjust(self, request, pk=None):
        """
        Apply a signed adjustment to an existing inventory item.

        The adjustment is always computed against the backend's authoritative
        quantity inside a transaction (row locked), then recorded as an
        ADJUSTMENT stock movement for the audit trail.
        """
        inventory = self.get_object()

        serializer = AdjustStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        adjustment = serializer.validated_data["adjustment"]
        reason = serializer.validated_data["reason"]
        note = serializer.validated_data.get("note", "").strip()

        with transaction.atomic():
            inventory = (
                Inventory.objects
                .select_related("product")
                .select_for_update()
                .get(pk=inventory.pk)
            )

            current = inventory.quantity
            new_quantity = current + adjustment

            if new_quantity < 0:
                raise ValidationError(
                    {
                        "adjustment": [(
                            "Cannot adjust stock below zero. "
                            f"Current stock is {current} units; "
                            f"an adjustment of {adjustment} would result "
                            f"in {new_quantity} units."
                        )]
                    }
                )

            inventory.quantity = new_quantity
            inventory.save(update_fields=["quantity", "updated_at"])

            if reason == "Other":
                remarks = note
            else:
                remarks = reason if not note else f"{reason}: {note}"

            movement = StockMovement.objects.create(
                organization=inventory.organization,
                product=inventory.product,
                movement_type="ADJUSTMENT",
                quantity=abs(adjustment),
                remarks=remarks,
                created_by=request.user,
            )

            try:
                from notifications.services import create_notification

                if inventory.quantity == 0:
                    create_notification(
                        organization=inventory.organization,
                        user=request.user,
                        title="Out of Stock",
                        message=(
                            f"{inventory.product.name} is now out of stock."
                        ),
                        notification_type="OUT_OF_STOCK",
                    )
                elif inventory.quantity <= inventory.minimum_stock:
                    create_notification(
                        organization=inventory.organization,
                        user=request.user,
                        title="Low Stock Alert",
                        message=(
                            f"{inventory.product.name} stock is low. "
                            f"Remaining quantity: {inventory.quantity}"
                        ),
                        notification_type="LOW_STOCK",
                    )
            except Exception:
                pass

        return Response(
            {
                "inventory": InventorySerializer(
                    inventory, context={"request": request}
                ).data,
                "movement": StockMovementSerializer(
                    movement, context={"request": request}
                ).data,
                "previous_quantity": current,
                "adjustment": adjustment,
                "new_quantity": new_quantity,
            },
            status=status.HTTP_200_OK,
        )


class StockMovementViewSet(TenantViewSet):

    queryset = StockMovement.objects.select_related(
        "product",
        "created_by",
    ).all()

    serializer_class = StockMovementSerializer

    def perform_create(self, serializer):
        qty = serializer.validated_data.get("quantity", 0)
        movement_type = serializer.validated_data.get(
            "movement_type", "ADJUSTMENT"
        )
        product = serializer.validated_data.get("product")
        organization = getattr(self.request.user, "organization", None)

        if not organization:
            raise ValidationError(
                {
                    "organization": (
                        "The authenticated user is not assigned to an organization."
                    )
                }
            )

        with transaction.atomic():
            inventory, created = Inventory.objects.get_or_create(
                product=product,
                organization=organization,
                defaults={"quantity": 0},
            )

            if movement_type == "IN":
                inventory.quantity += qty
            elif movement_type == "OUT":
                if qty > inventory.quantity:
                    raise ValidationError(
                        {
                            "quantity": (
                                f"Cannot remove {qty} units. "
                                f"Only {inventory.quantity} available."
                            )
                        }
                    )
                inventory.quantity -= qty
            else:
                inventory.quantity = qty

            inventory.save(update_fields=["quantity", "updated_at"])

            movement = serializer.save(
                organization=organization,
                created_by=self.request.user,
            )

            try:
                from notifications.services import create_notification

                if inventory.quantity == 0:
                    create_notification(
                        organization=organization,
                        user=self.request.user,
                        title="Out of Stock",
                        message=f"{product.name} is now out of stock.",
                        notification_type="OUT_OF_STOCK",
                    )
                elif inventory.quantity <= inventory.minimum_stock:
                    create_notification(
                        organization=organization,
                        user=self.request.user,
                        title="Low Stock Alert",
                        message=(
                            f"{product.name} stock is low. "
                            f"Remaining quantity: {inventory.quantity}"
                        ),
                        notification_type="LOW_STOCK",
                    )
            except Exception:
                pass

            return movement