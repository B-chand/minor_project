from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated


class TenantModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet for tenant-owned models.
    Automatically filters by organization when applicable.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return self.queryset

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