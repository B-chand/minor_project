from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):

    user_name = serializers.ReadOnlyField(
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