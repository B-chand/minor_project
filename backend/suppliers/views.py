from core.mixins import TenantModelViewSet

from .models import Supplier
from .serializers import SupplierSerializer


class SupplierViewSet(TenantModelViewSet):

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    