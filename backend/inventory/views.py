from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

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