from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.mixins import TenantModelViewSet

from .models import (
    Sale,
    SaleItem,
)

from .serializers import (
    RecordPaymentSerializer,
    SaleSerializer,
    SaleItemSerializer,
)


class SaleViewSet(TenantModelViewSet):
    """
    CRUD API for Sales.
    """

    queryset = Sale.objects.all()

    serializer_class = SaleSerializer

    search_fields = [
        "invoice_number",
        "customer__first_name",
        "customer__last_name",
        "customer__phone",
    ]

    filterset_fields = [
        "payment_status",
        "sale_date",
    ]

    def _restock_item(self, item):
        from inventory.models import Inventory, StockMovement

        inventory = Inventory.objects.filter(
            product=item.product,
            organization=self.request.user.organization,
        ).first()

        if inventory:
            inventory.quantity += item.quantity
            inventory.save(update_fields=["quantity", "updated_at"])

        StockMovement.objects.create(
            product=item.product,
            organization=self.request.user.organization,
            movement_type="IN",
            quantity=item.quantity,
            remarks=f"Restock from deleted sale ({item.sale.invoice_number})",
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        """
        Record a payment received toward an unpaid / partially paid invoice.

        The payment is added to the sale's amount_paid and the stored
        payment_status is recomputed automatically. The sale row is locked
        with select_for_update so concurrent payments cannot exceed the
        remaining balance.
        """
        sale = self.get_object()

        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        with transaction.atomic():
            locked = Sale.objects.select_for_update().get(pk=sale.pk)

            remaining = locked.remaining_amount()

            if remaining == 0:
                raise ValidationError(
                    {
                        "amount": [
                            "This invoice is already fully paid; no further payment can be recorded."
                        ]
                    }
                )

            if amount > remaining:
                raise ValidationError(
                    {
                        "amount": [
                            f"Payment amount cannot exceed the remaining balance of {remaining}."
                        ]
                    }
                )

            locked.amount_paid = (locked.amount_paid or Decimal("0.00")) + amount
            locked.save(
                update_fields=["amount_paid", "payment_status", "updated_at"]
            )

        return Response(
            SaleSerializer(locked, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        sale = self.get_object()

        with transaction.atomic():
            for item in sale.items.all():
                self._restock_item(item)
            return super().destroy(request, *args, **kwargs)


class SaleItemViewSet(TenantModelViewSet):
    """
    CRUD API for Sale Items.
    """

    queryset = SaleItem.objects.all()

    serializer_class = SaleItemSerializer

    def get_queryset(self):
        user = self.request.user
        organization = getattr(user, "organization", None)
        if not organization:
            return self.queryset.none()
        return self.queryset.filter(
            sale__organization=organization
        )

    def destroy(self, request, *args, **kwargs):
        from inventory.models import Inventory, StockMovement

        item = self.get_object()
        sale = item.sale

        with transaction.atomic():
            inventory = Inventory.objects.filter(
                product=item.product,
                organization=sale.organization,
            ).first()

            if inventory:
                inventory.quantity += item.quantity
                inventory.save(update_fields=["quantity", "updated_at"])

            StockMovement.objects.create(
                product=item.product,
                organization=sale.organization,
                movement_type="IN",
                quantity=item.quantity,
                remarks=f"Restock from sale item removal ({sale.invoice_number})",
                created_by=request.user,
            )

            response = super().destroy(request, *args, **kwargs)

            sale.total_amount = sum(
                i.subtotal for i in sale.items.all()
            )
            sale.save(
                update_fields=[
                    "total_amount",
                    "payment_status",
                ]
            )

            return response