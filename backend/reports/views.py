from django.db.models import Sum, F

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from accounts.permissions import IsBusinessAdmin

from core.mixins import TenantModelViewSet

from .models import Report
from .serializers import ReportSerializer

from inventory.models import Product, Inventory
from customers.models import Customer
from suppliers.models import Supplier
from sales.models import Sale
from purchases.models import Purchase
from notifications.models import Notification


class ReportViewSet(TenantModelViewSet):
    """
    CRUD API for Reports + Analytics APIs.

    The saved-report CRUD (``list``/``create``/``retrieve``/``update``/
    ``destroy``) is restricted to Business Admins. The
    read-only analytics actions that feed the staff Dashboard (``dashboard``,
    ``sales``, ``purchases``, ``low-stock``) remain available to any
    authenticated organization member so the Phase 18 dashboard behaviour is
    preserved. Role gating is independent of — and applied in addition to —
    the Phase 17 tenant isolation in ``TenantModelViewSet``.
    """

    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    RESTRICTED_ACTIONS = {
        "list",
        "create",
        "retrieve",
        "update",
        "partial_update",
        "destroy",
    }

    def get_permissions(self):
        if self.action in self.RESTRICTED_ACTIONS:
            return [IsBusinessAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        organization = getattr(self.request.user, "organization", None)
        if not organization:
            raise ValidationError(
                {
                    "organization": (
                        "The authenticated user is not assigned to an organization."
                    )
                }
            )
        serializer.save(
            organization=organization,
            generated_by=self.request.user,
        )

    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        """
        Dashboard summary report.
        """

        organization = request.user.organization

        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")

        sales_qs = Sale.objects.filter(organization=organization)
        purchases_qs = Purchase.objects.filter(
            organization=organization
        )

        if from_date:
            sales_qs = sales_qs.filter(sale_date__gte=from_date)
            purchases_qs = purchases_qs.filter(
                purchase_date__gte=from_date
            )

        if to_date:
            sales_qs = sales_qs.filter(sale_date__lte=to_date)
            purchases_qs = purchases_qs.filter(purchase_date__lte=to_date)

        total_products = Product.objects.filter(
            organization=organization
        ).count()

        total_customers = Customer.objects.filter(
            organization=organization
        ).count()

        total_suppliers = Supplier.objects.filter(
            organization=organization
        ).count()

        total_sales = sales_qs.aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        total_purchases = purchases_qs.aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        sales_count = sales_qs.count()
        purchases_count = purchases_qs.count()

        low_stock_products = Inventory.objects.filter(
            organization=organization,
            quantity__lte=F("minimum_stock"),
            quantity__gt=0
        ).count()

        out_of_stock_products = Inventory.objects.filter(
            organization=organization,
            quantity=0
        ).count()

        unread_notifications = Notification.objects.filter(
            organization=organization,
            is_read=False
        ).count()

        return Response(
            {
                "total_products": total_products,
                "total_customers": total_customers,
                "total_suppliers": total_suppliers,
                "total_sales": total_sales,
                "total_purchases": total_purchases,
                "sales_count": sales_count,
                "purchases_count": purchases_count,
                "low_stock_products": low_stock_products,
                "out_of_stock_products": out_of_stock_products,
                "unread_notifications": unread_notifications,
            }
        )

    @action(detail=False, methods=["get"], url_path="sales")
    def sales(self, request):
        """
        Sales report.
        """

        sales = Sale.objects.filter(
            organization=request.user.organization
        )

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date:
            sales = sales.filter(sale_date__gte=start_date)

        if end_date:
            sales = sales.filter(sale_date__lte=end_date)

        data = []

        for sale in sales:
            data.append(
                {
                    "date": sale.sale_date,
                    "invoice": sale.invoice_number,
                    "customer": (
                        str(sale.customer)
                        if sale.customer
                        else "Walk-in Customer"
                    ),
                    "amount": sale.total_amount,
                    "paid": sale.amount_paid,
                    "remaining": sale.remaining_amount(),
                    "status": sale.computed_payment_status(),
                }
            )

        return Response(data)

    @action(detail=False, methods=["get"], url_path="purchases")
    def purchases(self, request):
        """
        Purchase report.
        """

        purchases = Purchase.objects.filter(
            organization=request.user.organization
        )

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date:
            purchases = purchases.filter(purchase_date__gte=start_date)

        if end_date:
            purchases = purchases.filter(purchase_date__lte=end_date)

        data = []

        for purchase in purchases:
            data.append(
                {
                    "date": purchase.purchase_date,
                    "invoice": purchase.invoice_number,
                    "supplier": purchase.supplier.name,
                    "amount": purchase.total_amount,
                    "status": purchase.status,
                }
            )

        return Response(data)

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        """
        Low stock report.
        """

        inventory = Inventory.objects.filter(
            organization=request.user.organization,
            quantity__lte=F("minimum_stock")
        )

        data = []

        for item in inventory:
            data.append(
                {
                    "product": item.product.name,
                    "quantity": item.quantity,
                    "minimum_stock": item.minimum_stock,
                    "status": item.stock_status,
                }
            )

        return Response(data)