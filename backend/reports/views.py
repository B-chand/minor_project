from core.mixins import TenantModelViewSet

from .models import Report
from .serializers import ReportSerializer


class ReportViewSet(TenantModelViewSet):
    """
    CRUD API for Reports.
    """

    queryset = Report.objects.all()

    serializer_class = ReportSerializer