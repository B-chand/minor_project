from django.db import models

from core.models import TenantModel


class Category(TenantModel):
    """
    Product category (Electronics, Grocery, Medicine, etc.)
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("organization", "name")

    def __str__(self):
        return self.name


class Product(TenantModel):
    """
    Product information.
    """

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products"
    )

    name = models.CharField(max_length=255)

    sku = models.CharField(max_length=100)

    barcode = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    description = models.TextField(blank=True)

    buying_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = (
            "organization",
            "sku",
        )

    def __str__(self):
        return self.name


class Inventory(TenantModel):
    """
    Current inventory.
    """

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory"
    )

    quantity = models.PositiveIntegerField(default=0)

    minimum_stock = models.PositiveIntegerField(default=10)

    maximum_stock = models.PositiveIntegerField(default=1000)

    class Meta:
        ordering = ["product__name"]

    @property
    def stock_status(self):

        if self.quantity <= 0:
            return "Out of Stock"

        if self.quantity <= self.minimum_stock:
            return "Low Stock"

        return "In Stock"

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


class StockMovement(TenantModel):
    """
    Complete stock movement history.
    """

    STOCK_TYPES = (
        ("IN", "Stock In"),
        ("OUT", "Stock Out"),
        ("ADJUSTMENT", "Adjustment"),
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="movements"
    )

    movement_type = models.CharField(
        max_length=20,
        choices=STOCK_TYPES
    )

    quantity = models.PositiveIntegerField()

    remarks = models.TextField(blank=True)

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} - {self.movement_type}"