from core.mixins import TenantModelViewSet

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(TenantModelViewSet):

    queryset = Notification.objects.select_related(
        "created_for"
    ).all()

    serializer_class = NotificationSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_for=self.request.user,
        )