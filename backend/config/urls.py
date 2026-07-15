from django.contrib import admin
from django.urls import include, path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [

    # Admin
    path(
        "admin/",
        admin.site.urls,
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