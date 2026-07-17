from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterView,
    CurrentUserView,
    StaffViewSet,
)

router = DefaultRouter()

router.register(
    "staff",
    StaffViewSet,
    basename="staff",
)

urlpatterns = [
    path(
        "register/",
        RegisterView.as_view(),
        name="register",
    ),

    path(
        "me/",
        CurrentUserView.as_view(),
        name="current-user",
    ),

    path(
        "",
        include(router.urls),
    ),
]