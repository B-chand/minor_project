from core.mixins import TenantModelViewSet

from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(TenantModelViewSet):
    """
    CRUD API for Customers.
    """

    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer