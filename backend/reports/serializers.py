from rest_framework import serializers

from .models import Report


class ReportSerializer(serializers.ModelSerializer):

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
        )