from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ProductViewSet,
    InventoryViewSet,
    StockMovementViewSet,
)

router = DefaultRouter()

router.register(
    "categories",
    CategoryViewSet,
    basename="category"
)

router.register(
    "products",
    ProductViewSet,
    basename="product"
)

router.register(
    "inventory",
    InventoryViewSet,
    basename="inventory"
)

router.register(
    "stock-movements",
    StockMovementViewSet,
    basename="stockmovement"
)

urlpatterns = [
    path("", include(router.urls)),
]