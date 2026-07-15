from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


class TenantModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet for all tenant-owned models.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return self.queryset

        return self.queryset.filter(
            organization=user.organization
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization
        )