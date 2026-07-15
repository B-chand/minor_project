from core.mixins import TenantModelViewSet

from .models import Purchase, PurchaseItem
from .serializers import (
    PurchaseSerializer,
    PurchaseItemSerializer,
)


class PurchaseViewSet(TenantModelViewSet):
    """
    CRUD API for Purchases.
    """

    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer


class PurchaseItemViewSet(TenantModelViewSet):
    """
    CRUD API for Purchase Items.
    """

    queryset = PurchaseItem.objects.all()
    serializer_class = PurchaseItemSerializer