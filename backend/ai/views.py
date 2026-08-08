from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from datetime import date

from core.mixins import TenantModelViewSet

from .models import AIInsight
from .serializers import AIInsightSerializer

from .services.forecasting import forecast_demand
from .services.recommendation import get_recommendations
from .services.insights import generate_insights
from .services.dashboard import get_ai_dashboard
from .services.chatbot import process_user_query
from .services.bi import get_business_intelligence
from .services.inventory_summary import build_inventory_summary

class AIInsightViewSet(TenantModelViewSet):
    """
    CRUD API for AI Insights.
    """

    queryset = AIInsight.objects.all()
    serializer_class = AIInsightSerializer


class ForecastAPIView(APIView):
    """
    AI Demand Forecast API
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = getattr(request.user, "organization", None)
        predictions = forecast_demand(organization)
        return Response(predictions)


class RecommendationAPIView(APIView):
    """
    AI Reorder Recommendation API
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = getattr(request.user, "organization", None)
        recommendations = get_recommendations(organization)
        return Response(recommendations)

class InsightsAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization = getattr(request.user, "organization", None)
        insights = generate_insights(organization)

        return Response(
            {
                "insights": insights
            }
        )

class AIDashboardAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization = getattr(request.user, "organization", None)
        data = get_ai_dashboard(organization)

        return Response(data)


class InventorySummaryAPIView(APIView):
    """
    Read-only AI Inventory Summary for the authenticated tenant.

    Returns a concise, rule-based, human-readable inventory summary built
    from the existing tenant-scoped BI tools. The organization is always
    derived from ``request.user.organization``; an organization id from the
    client (query or body) is never accepted or trusted. No LLM is involved.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = getattr(request.user, "organization", None)
        return Response(build_inventory_summary(organization))


class BusinessIntelligenceAPIView(APIView):
    """
    Read-only AI business-intelligence dashboard.

    Returns a stable, tenant-scoped aggregation of the existing BI tools
    (overview, metrics, sales/inventory/purchase intelligence and attention
    items). The organization is always derived from the authenticated user;
    an organization id from the client is never accepted or trusted.

    Optional, server-validated reporting-window query parameters are
    forwarded to the time-aware tools only:
      - ``days``        trailing window length (1..3650)
      - ``period``      recognized label (today, last_30_days, this_month, …)
      - ``start_date``/``end_date``  explicit inclusive ISO range (overrides
        ``days``/``period``)
      - ``bucket``      trend bucketing: ``day``, ``week`` or ``month``
    Unknown/empty values are ignored and the tools fall back to their
    defaults, so the default response contract never changes.
    """

    permission_classes = [IsAuthenticated]

    TREND_BUCKETS = {"day", "week", "month", "daily", "weekly"}

    @staticmethod
    def _parse_window(request):
        params = request.query_params
        window = {}

        days = (params.get("days") or "").strip()
        if days:
            try:
                number = int(days)
                if 1 <= number <= 3650:
                    window["days"] = number
            except (TypeError, ValueError):
                pass

        period = (params.get("period") or "").strip()
        if period:
            window["period"] = period

        bucket = (params.get("bucket") or "").strip().lower()
        if bucket in BusinessIntelligenceAPIView.TREND_BUCKETS:
            window["bucket"] = {
                "daily": "day",
                "weekly": "week",
            }.get(bucket, bucket)

        for field in ("start_date", "end_date"):
            raw = (params.get(field) or "").strip()
            if not raw:
                continue
            try:
                date.fromisoformat(raw)
            except ValueError:
                continue
            window[field] = raw

        return window

    def get(self, request):
        organization = getattr(request.user, "organization", None)
        window = self._parse_window(request)
        return Response(get_business_intelligence(organization, window=window))


class ChatbotAPIView(APIView):
    """
    AI Assistant API endpoint.

    Connects the authenticated user's message to the tenant-scoped Groq
    assistant. Returns ``reply`` on success and a structured ``error``
    object (with an appropriate HTTP status) when the AI service is
    unavailable, rate-limited, misconfigured, or unreachable.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}

        message = data.get("message")
        if not isinstance(message, str):
            message = ""

        if not message.strip():
            return Response(
                {"detail": "message is required"},
                status=400,
            )

        result = process_user_query(
            request,
            message,
            history=data.get("history"),
        )

        payload = {
            "reply": result.get("reply"),
            "context_ready": result.get("context_ready", False),
        }
        if result.get("error"):
            payload["error"] = result["error"]

        return Response(payload, status=result.get("http_status", 200))