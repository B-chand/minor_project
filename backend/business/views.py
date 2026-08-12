from accounts.permissions import IsBusinessAdmin

from core.mixins import TenantModelViewSet

from .models import BusinessProfile
from .serializers import BusinessProfileSerializer


class BusinessProfileViewSet(TenantModelViewSet):
    """
    CRUD API for Business Profile (Business Admin only).
    """

    permission_classes = [IsBusinessAdmin]

    queryset = BusinessProfile.objects.all()

    serializer_class = BusinessProfileSerializer