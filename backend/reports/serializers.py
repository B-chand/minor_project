from rest_framework import serializers

from core.mixins import TenantScopedSerializerMixin

from .models import Report


class ReportSerializer(TenantScopedSerializerMixin):

    generated_by_name = serializers.ReadOnlyField(
        source="generated_by.username"
    )

    class Meta:
        model = Report

        fields = "__all__"

        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
            "generated_by",
        )