from inventory.models import Inventory

from .forecasting import forecast_demand


def build_recommendations(organization, forecasts):
    """Build reorder recommendations from precomputed demand forecasts.

    ``forecasts`` is the list returned by ``forecast_demand``; callers that
    already computed the forecast (e.g. the AI dashboard) reuse it here so
    the expensive ML step never runs more than once per request.
    """

    if not forecasts:
        return []

    inventory_map = {
        row.product_id: row
        for row in Inventory.objects.select_related("product").filter(
            organization=organization,
            product_id__in=[
                forecast["product_id"] for forecast in forecasts
            ],
        )
    }

    recommendations = []

    for forecast in forecasts:

        inventory = inventory_map.get(forecast["product_id"])

        if inventory is None:
            continue

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

    return recommendations


def get_recommendations(organization=None):

    return build_recommendations(
        organization,
        forecast_demand(organization),
    )
