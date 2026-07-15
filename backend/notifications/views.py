from core.mixins import TenantModelViewSet

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(TenantModelViewSet):
    """
    CRUD API for Notifications.
    """

    queryset = Notification.objects.all()

    serializer_class = NotificationSerializer