from django.db import transaction

from core.mixins import TenantModelViewSet

from .models import Purchase, PurchaseItem
from .serializers import (
    PurchaseSerializer,
    PurchaseItemSerializer,
)


class PurchaseViewSet(TenantModelViewSet):
    """
    CRUD API for Purchases.
    """

    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer

    def _reduce_stock(self, item):
        from inventory.models import Inventory, StockMovement

        inventory = Inventory.objects.filter(
            product=item.product,
            organization=self.request.user.organization,
        ).first()

        if inventory:
            new_qty = max(0, inventory.quantity - item.quantity)
            inventory.quantity = new_qty
            inventory.save(update_fields=["quantity", "updated_at"])

        StockMovement.objects.create(
            product=item.product,
            organization=self.request.user.organization,
            movement_type="OUT",
            quantity=item.quantity,
            remarks=f"Stock removed from deleted purchase ({item.purchase.invoice_number})",
            created_by=self.request.user,
        )

    def destroy(self, request, *args, **kwargs):
        purchase = self.get_object()

        with transaction.atomic():
            for item in purchase.items.all():
                self._reduce_stock(item)
            return super().destroy(request, *args, **kwargs)


class PurchaseItemViewSet(TenantModelViewSet):
    """
    CRUD API for Purchase Items.
    """

    queryset = PurchaseItem.objects.all()
    serializer_class = PurchaseItemSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        return self.queryset.filter(
            purchase__organization=user.organization
        )

    def destroy(self, request, *args, **kwargs):
        from inventory.models import Inventory, StockMovement

        item = self.get_object()
        purchase = item.purchase

        with transaction.atomic():
            inventory = Inventory.objects.filter(
                product=item.product,
                organization=purchase.organization,
            ).first()

            if inventory:
                new_qty = max(0, inventory.quantity - item.quantity)
                inventory.quantity = new_qty
                inventory.save(update_fields=["quantity", "updated_at"])

            StockMovement.objects.create(
                product=item.product,
                organization=purchase.organization,
                movement_type="OUT",
                quantity=item.quantity,
                remarks=f"Stock removed from purchase item removal ({purchase.invoice_number})",
                created_by=request.user,
            )

            response = super().destroy(request, *args, **kwargs)

            purchase.total_amount = sum(
                i.subtotal for i in purchase.items.all()
            )
            purchase.save(update_fields=["total_amount"])

            return response