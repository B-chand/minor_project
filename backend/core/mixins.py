from rest_framework import viewsets
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
            return self.queryset.filter(
                organization=user.organization
            )

        return self.queryset

    def perform_create(self, serializer):
        model = serializer.Meta.model

        if hasattr(model, "organization"):
            serializer.save(
                organization=self.request.user.organization
            )
        else:
            serializer.save()