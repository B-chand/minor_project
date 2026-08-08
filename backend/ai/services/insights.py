from django.db.models import Sum, Count

from sales.models import SaleItem
from inventory.models import Inventory

from .forecasting import forecast_demand


def generate_insights(organization=None):

    insights = []

    # ------------------------
    # Best Selling Product
    # ------------------------

    best = (
        SaleItem.objects
        .filter(
            sale__organization=organization
        )
        .values("product__name")
        .annotate(total=Sum("quantity"))
        .order_by("-total")
        .first()
    )

    if best:
        insights.append(
            f"{best['product__name']} is the best selling product."
        )

    # ------------------------
    # Low Stock Products
    # ------------------------

    low_stock = Inventory.objects.filter(
        organization=organization,
        quantity__lte=10
    ).count()

    insights.append(
        f"{low_stock} products are currently low in stock."
    )

    # ------------------------
    # Forecast
    # ------------------------

    forecast = forecast_demand(organization)

    if forecast:

        highest = max(
            forecast,
            key=lambda x: x["predicted_quantity"]
        )

        insights.append(
            f"{highest['product_name']} is expected to have the highest demand tomorrow."
        )

    # ------------------------
    # Total Products Sold
    # ------------------------

    total_sales = SaleItem.objects.filter(
        sale__organization=organization
    ).aggregate(
        total=Sum("quantity")
    )["total"] or 0

    insights.append(
        f"A total of {total_sales} products have been sold."
    )

    return insights