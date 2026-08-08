from inventory.models import Inventory

from .forecasting import forecast_demand


def get_recommendations(organization=None):

    forecasts = forecast_demand(organization)

    recommendations = []

    for forecast in forecasts:

        try:
            inventory = Inventory.objects.select_related(
                "product"
            ).get(
                product_id=forecast["product_id"],
                organization=organization,
            )

            recommended = (
                inventory.minimum_stock
                + forecast["predicted_quantity"]
                - inventory.quantity
            )

            if recommended < 0:
                recommended = 0

            recommendations.append(
                {
                    "product_id": inventory.product.id,
                    "product_name": inventory.product.name,
                    "current_stock": inventory.quantity,
                    "minimum_stock": inventory.minimum_stock,
                    "forecast": forecast["predicted_quantity"],
                    "recommended_order": recommended,
                }
            )

        except Inventory.DoesNotExist:
            continue

    return recommendations