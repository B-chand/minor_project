from rest_framework import serializers

from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = "__all__"

        read_only_fields = (
            "id",
            "organization",
            "created_at",
            "updated_at",
        )

    def validate_email(self, value):

        if not value:
            return value

        request = self.context["request"]

        queryset = Customer.objects.filter(
            organization=request.user.organization,
            email=value
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "A customer with this email already exists."
            )

        return value

    def validate_phone(self, value):

        if not value:
            return value

        request = self.context["request"]

        queryset = Customer.objects.filter(
            organization=request.user.organization,
            phone=value
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "A customer with this phone number already exists."
            )

        return value