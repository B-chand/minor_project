from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AIInsightViewSet


router = DefaultRouter()


router.register(
    "insights",
    AIInsightViewSet,
    basename="ai-insight",
)


urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
]