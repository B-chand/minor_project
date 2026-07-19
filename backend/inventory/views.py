from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import status
from rest_framework.response import Response

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
        return self.queryset.filter(
            organization=self.request.user.organization
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization
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
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )