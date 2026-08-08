from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import status
from rest_framework.response import Response

from django.db import transaction

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
)


class TenantViewSet(ModelViewSet):
    """
    Base ViewSet for tenant-owned models.
    Automatically filters data by organization.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return self.queryset

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
        organization = self.request.user.organization

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