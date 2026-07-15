from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PurchaseViewSet,
    PurchaseItemViewSet,
)


router = DefaultRouter()

router.register(
    "purchases",
    PurchaseViewSet,
    basename="purchase",
)

router.register(
    "purchase-items",
    PurchaseItemViewSet,
    basename="purchase-item",
)


urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
]