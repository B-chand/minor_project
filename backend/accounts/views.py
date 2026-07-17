from rest_framework import generics, permissions, viewsets

from core.mixins import TenantModelViewSet

from .models import User
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    StaffSerializer,
)

from .permissions import IsAdminOrSuperAdmin

class RegisterView(generics.CreateAPIView):
    """
    Register a new Organization and its first Business Admin.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class CurrentUserView(generics.RetrieveAPIView):
    """
    Return the currently logged-in user.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class StaffViewSet(TenantModelViewSet):
    """
    Business Admin can manage staff users.
    """

    permission_classes = [
        IsAdminOrSuperAdmin
    ]

    queryset = User.objects.filter(role="STAFF")
    serializer_class = StaffSerializer