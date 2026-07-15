from django.db import models

from core.models import TenantModel
from customers.models import Customer
from inventory.models import Product


class Sale(TenantModel):
    """
    Sales invoice.
    """

    PAYMENT_STATUS = (
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Partial", "Partial"),
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales"
    )

    invoice_number = models.CharField(
        max_length=100,
        unique=True
    )

    sale_date = models.DateField()

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="Paid"
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    notes = models.TextField(
        blank=True
    )


    class Meta:
        ordering = ["-sale_date"]


    def __str__(self):
        return self.invoice_number



class SaleItem(models.Model):
    """
    Individual products inside a sale.
    """

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )


    def __str__(self):
        return self.product.name