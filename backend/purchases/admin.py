from django.contrib import admin
from django.urls import include, path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "api/accounts/",
        include("accounts.urls"),
    ),

    path(
        "api/inventory/",
        include("inventory.urls"),
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

    path(
    "api/purchases/",
    include("purchases.urls"),
    ),

    path(
    "api/customers/",
    include("customers.urls"),
    ),

    path(
    "api/suppliers/",
    include("suppliers.urls"),
    ),
]



