from rest_framework.exceptions import ValidationError

from core.mixins import TenantModelViewSet

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(TenantModelViewSet):

    queryset = Notification.objects.select_related(
        "created_for"
    ).all()

    serializer_class = NotificationSerializer

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
            organization=organization,
            created_for=self.request.user,
        )