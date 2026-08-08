from django.db.models import Sum, F

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

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
    """

    queryset = Report.objects.all()
    serializer_class = ReportSerializer

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

        total_products = Product.objects.filter(
            organization=organization
        ).count()

        total_customers = Customer.objects.filter(
            organization=organization
        ).count()

        total_suppliers = Supplier.objects.filter(
            organization=organization
        ).count()

        total_sales = (
            Sale.objects.filter(
                organization=organization
            ).aggregate(
                total=Sum("total_amount")
            )["total"] or 0
        )

        total_purchases = (
            Purchase.objects.filter(
                organization=organization
            ).aggregate(
                total=Sum("total_amount")
            )["total"] or 0
        )

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
                    "status": sale.payment_status,
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