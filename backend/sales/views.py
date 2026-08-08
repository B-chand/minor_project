from django.db import transaction

from core.mixins import TenantModelViewSet

from .models import (
    Sale,
    SaleItem,
)

from .serializers import (
    SaleSerializer,
    SaleItemSerializer,
)


class SaleViewSet(TenantModelViewSet):
    """
    CRUD API for Sales.
    """

    queryset = Sale.objects.all()

    serializer_class = SaleSerializer

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
        if user.is_superuser:
            return self.queryset
        return self.queryset.filter(
            sale__organization=user.organization
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
            sale.save(update_fields=["total_amount"])

            return response