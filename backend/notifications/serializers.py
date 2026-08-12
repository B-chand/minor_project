from rest_framework import serializers

from core.mixins import TenantScopedSerializerMixin

from .models import Notification


class NotificationSerializer(TenantScopedSerializerMixin):

    created_for_name = serializers.ReadOnlyField(
        source="created_for.username"
    )

    class Meta:
        model = Notification
        fields = "__all__"

        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
        )