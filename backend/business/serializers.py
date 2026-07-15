from rest_framework import serializers

from .models import BusinessProfile


class BusinessProfileSerializer(serializers.ModelSerializer):

    organization_name = serializers.ReadOnlyField(
        source="organization.name"
    )

    class Meta:
        model = BusinessProfile

        fields = "__all__"

        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
        )