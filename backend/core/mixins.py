from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ModelSerializer


class TenantModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet for tenant-owned models.
    Automatically filters by organization when applicable.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Scope the queryset to the request user's organization.

        ``request.user.organization`` is the user's own organization from
        their user record — every user belongs to exactly one organization
        and can never switch tenants. A user with no organization never sees
        tenant data.
        """

        user = self.request.user

        model = self.queryset.model

        if hasattr(model, "organization"):
            if not getattr(user, "organization", None):
                return self.queryset.none()

            return self.queryset.filter(
                organization=user.organization
            )

        return self.queryset

    def perform_create(self, serializer):
        model = serializer.Meta.model

        if hasattr(model, "organization"):
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
                organization=organization
            )
        else:
            serializer.save()


class TenantScopedSerializerMixin(ModelSerializer):
    """
    Scope every writable ForeignKey to the authenticated user's organization.

    Any relational field whose related model carries an ``organization``
    attribute has its validation queryset narrowed to
    ``request.user.organization``. A client-supplied ID that references
    another organization's record therefore fails standard DRF validation
    with the same "Invalid pk ... object does not exist" error used for an
    unknown ID, so the request is rejected without leaking whether the
    foreign record exists.

    The organization is always derived from ``request.user.organization``;
    client-supplied organization/tenant parameters are never consulted.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if request is None:
            return

        organization = getattr(request.user, "organization", None)
        if organization is None:
            return

        for field_name, field in self.fields.items():
            queryset = getattr(field, "queryset", None)
            if queryset is None:
                continue

            related_model = getattr(queryset, "model", None)
            if related_model is None or not hasattr(related_model, "organization"):
                continue

            field.queryset = related_model.objects.filter(
                organization=organization
            )