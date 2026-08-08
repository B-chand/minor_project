from django.contrib import admin
from django.urls import include, path

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


class HealthCheckView(APIView):
    """Simple health check endpoint."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok"})


urlpatterns = [

    # Admin
    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "api/health/",
        HealthCheckView.as_view(),
        name="health",
    ),


    # Authentication
    path(
        "api/accounts/",
        include("accounts.urls"),
    ),

    path(
        "api/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),


    # Core Business Modules
    path(
        "api/inventory/",
        include("inventory.urls"),
    ),

    path(
        "api/customers/",
        include("customers.urls"),
    ),

    path(
        "api/suppliers/",
        include("suppliers.urls"),
    ),

    path(
        "api/purchases/",
        include("purchases.urls"),
    ),

    path(
    "api/sales/",
    include("sales.urls"),
    ),

    path(
    "api/notifications/",
    include("notifications.urls"),
    ),

    path(
    "api/reports/",
    include("reports.urls"),
    ),

    path(
    "api/ai/",
    include("ai.urls"),
    ),

    path(
    "api/business/",
    include("business.urls"),
    ),
]