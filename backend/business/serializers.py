from rest_framework import serializers

from core.models import Organization

from .models import BusinessProfile


class BusinessProfileSerializer(serializers.ModelSerializer):
    """
    Business profile serializer that also exposes and writes the tenant's
    organization-level business information (name, email, phone, address).

    The organization is always derived from the authenticated user's own
    record — the ``organization`` field itself is read-only and never
    accepted from the client — so updates can only ever touch the requesting
    user's own tenant.
    """

    organization_name = serializers.CharField(
        max_length=255,
        allow_blank=False,
        write_only=True,
    )

    organization_email = serializers.EmailField(
        write_only=True,
    )

    organization_phone = serializers.CharField(
        max_length=20,
        allow_blank=False,
        write_only=True,
    )

    organization_address = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
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

    def validate_organization_email(self, value):
        organization = getattr(self.instance, "organization", None)

        if organization is None:
            request = self.context.get("request")
            if request is not None:
                organization = getattr(request.user, "organization", None)

        queryset = Organization.objects.all()
        if organization is not None:
            queryset = queryset.exclude(pk=organization.pk)

        if queryset.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An organization with this email already exists."
            )

        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)

        organization = instance.organization

        data["organization_name"] = organization.name
        data["organization_email"] = organization.email
        data["organization_phone"] = organization.phone
        data["organization_address"] = organization.address

        return data

    def _pop_organization_fields(self, validated_data):
        organization_keys = (
            "organization_name",
            "organization_email",
            "organization_phone",
            "organization_address",
        )

        return {
            key: validated_data.pop(key)
            for key in list(validated_data)
            if key in organization_keys
        }

    def _apply_organization_fields(self, organization, organization_fields):
        for attr, key in (
            ("name", "organization_name"),
            ("email", "organization_email"),
            ("phone", "organization_phone"),
            ("address", "organization_address"),
        ):
            if key in organization_fields:
                setattr(organization, attr, organization_fields[key])

        organization.save()

    def create(self, validated_data):
        organization_fields = self._pop_organization_fields(validated_data)

        instance = super().create(validated_data)

        if organization_fields:
            self._apply_organization_fields(
                instance.organization,
                organization_fields,
            )

        return instance

    def update(self, instance, validated_data):
        organization_fields = self._pop_organization_fields(validated_data)

        instance = super().update(instance, validated_data)

        if organization_fields:
            self._apply_organization_fields(
                instance.organization,
                organization_fields,
            )

        return instance
