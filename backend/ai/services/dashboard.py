from inventory.models import Inventory
from sales.models import Sale

from .forecasting import forecast_demand
from .recommendation import build_recommendations
from .insights import generate_insights


def get_ai_dashboard(organization=None):

    total_sales = Sale.objects.filter(
        organization=organization
    ).count()

    low_stock = Inventory.objects.filter(
        organization=organization,
        quantity__lte=10
    ).count()

    forecast = forecast_demand(organization)

    return {
        "forecast": forecast,
        "recommendations": build_recommendations(organization, forecast),
        "insights": generate_insights(organization, forecast=forecast),
        "summary": {
            "total_sales": total_sales,
            "low_stock_products": low_stock,
        },
    }
