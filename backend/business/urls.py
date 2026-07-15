from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BusinessProfileViewSet


router = DefaultRouter()


router.register(
    "profile",
    BusinessProfileViewSet,
    basename="business-profile",
)


urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
]