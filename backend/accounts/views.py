from rest_framework import generics, permissions, viewsets
from rest_framework.authentication import BaseAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mixins import TenantModelViewSet

from .models import User
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    StaffSerializer,
    BusinessTokenObtainSerializer,
)

from .permissions import IsBusinessAdmin

class RegisterView(generics.CreateAPIView):
    """
    Register a new Organization and its first Business Admin.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class BusinessLoginAuthentication(BaseAuthentication):
    """
    Pluggable authenticator for the public login endpoint.

    It never authenticates a request itself; it only advertises a
    ``WWW-Authenticate`` header so DRF keeps ``AuthenticationFailed``
    responses at HTTP 401 instead of coercing them to 403.
    """

    def authenticate(self, request):
        return None

    def authenticate_header(self, request):
        return "Bearer"


class BusinessLoginView(APIView):
    """
    Business Code + Username + Password login.

    Swaps the stock SimpleJWT obtain-token endpoint for the tenanted
    login flow. Returns ``access``/``refresh`` tokens plus the
    authenticated user's role and business information.
    """

    authentication_classes = [BusinessLoginAuthentication]
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = BusinessTokenObtainSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data)


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
        IsBusinessAdmin
    ]

    queryset = User.objects.filter(
        role="STAFF"
    ).order_by("created_at")
    serializer_class = StaffSerializer