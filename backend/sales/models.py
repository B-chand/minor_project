from decimal import Decimal

from django.db import models

from core.models import TenantModel
from customers.models import Customer
from inventory.models import Product


class Sale(TenantModel):
    """
    Sales invoice.
    """

    PAYMENT_STATUS = (
        ("PAID", "Paid"),
        ("PARTIAL", "Partial"),
        ("UNPAID", "Unpaid"),
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales"
    )

    invoice_number = models.CharField(
        max_length=100
    )

    sale_date = models.DateField()

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="UNPAID"
    )

    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
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
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "invoice_number"],
                name="uniq_sale_invoice_per_org"
            )
        ]


    def computed_payment_status(self):
        """
        Authoritative payment status derived from paid and total amounts.

        - paid <= 0        -> UNPAID
        - paid < total     -> PARTIAL
        - paid >= total    -> PAID
        """
        paid = self.amount_paid or Decimal("0.00")
        total = self.total_amount or Decimal("0.00")

        if paid <= Decimal("0.00"):
            return "UNPAID"

        if paid < total:
            return "PARTIAL"

        return "PAID"


    def remaining_amount(self):
        """Outstanding balance (never negative)."""
        remaining = (self.total_amount or Decimal("0.00")) - (self.amount_paid or Decimal("0.00"))
        return max(remaining, Decimal("0.00"))

    def save(self, *args, **kwargs):
        self.payment_status = self.computed_payment_status()
        return super().save(*args, **kwargs)


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

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.product.name