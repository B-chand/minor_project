from core.mixins import TenantModelViewSet

from .models import (
    Sale,
    SaleItem,
)

from .serializers import (
    SaleSerializer,
    SaleItemSerializer,
)


class SaleViewSet(TenantModelViewSet):
    """
    CRUD API for Sales.
    """

    queryset = Sale.objects.all()

    serializer_class = SaleSerializer



class SaleItemViewSet(TenantModelViewSet):
    """
    CRUD API for Sale Items.
    """

    queryset = SaleItem.objects.all()

    serializer_class = SaleItemSerializer