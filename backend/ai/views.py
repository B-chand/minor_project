from core.mixins import TenantModelViewSet

from .models import AIInsight
from .serializers import AIInsightSerializer


class AIInsightViewSet(TenantModelViewSet):
    """
    CRUD API for AI Insights.
    """

    queryset = AIInsight.objects.all()

    serializer_class = AIInsightSerializer