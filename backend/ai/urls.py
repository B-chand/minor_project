from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AIInsightViewSet,
    ForecastAPIView,
    RecommendationAPIView,
    InsightsAPIView,
    AIDashboardAPIView,
    BusinessIntelligenceAPIView,
    InventorySummaryAPIView,
    ChatbotAPIView,
)

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

    path(
        "forecast/",
        ForecastAPIView.as_view(),
        name="forecast",
    ),

    path(
        "recommendation/",
        RecommendationAPIView.as_view(),
        name="recommendation",
    ),

    path(
        "insights-summary/",
        InsightsAPIView.as_view(),
        name="insights-summary",
    ),

    path(
        "dashboard/",
        AIDashboardAPIView.as_view(),
        name="dashboard",
    ),

    path(
        "business-intelligence/",
        BusinessIntelligenceAPIView.as_view(),
        name="business-intelligence",
    ),

    path(
        "inventory-summary/",
        InventorySummaryAPIView.as_view(),
        name="inventory-summary",
    ),

    path(
        "chat/",
        ChatbotAPIView.as_view(),
        name="chat",
    ),
]