from inventory.models import Inventory
from sales.models import Sale

from .forecasting import forecast_demand
from .recommendation import get_recommendations
from .insights import generate_insights


def get_ai_dashboard(organization=None):

    total_sales = Sale.objects.filter(
        organization=organization
    ).count()

    low_stock = Inventory.objects.filter(
        organization=organization,
        quantity__lte=10
    ).count()

    return {
        "forecast": forecast_demand(organization),
        "recommendations": get_recommendations(organization),
        "insights": generate_insights(organization),
        "summary": {
            "total_sales": total_sales,
            "low_stock_products": low_stock,
        },
    }