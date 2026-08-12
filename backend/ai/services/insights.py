from decimal import Decimal

from django.db.models import Sum, Count

from ai.models import AIInsight
from sales.models import SaleItem
from inventory.models import Inventory

from .forecasting import forecast_demand
from .recommendation import get_recommendations


def generate_insights(organization=None, forecast=None):

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

    if forecast is None:
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


def _safe_forecast(organization):
    """Forecast demand without ever blocking insight generation."""
    try:
        return forecast_demand(organization)
    except Exception:  # noqa: BLE001 - must never block generation
        return []


def build_insight_candidates(organization=None):
    """
    Compute candidate AIInsight rows from live tenant data.

    Returns a list of dicts (title / description / insight_type /
    confidence_score). Nothing is persisted here. Titles embed the
    specific product or condition so the duplicate check performed by
    ``persist_generated_insights`` stays meaningful and conservative.
    """
    if organization is None:
        return []

    candidates = []

    best = (
        SaleItem.objects
        .filter(sale__organization=organization)
        .values("product__name")
        .annotate(total=Sum("quantity"))
        .order_by("-total")
        .first()
    )
    if best:
        candidates.append({
            "title": f"Best seller: {best['product__name']}",
            "description": (
                f"{best['product__name']} is the best selling product in "
                "this period."
            ),
            "insight_type": "ANALYSIS",
            "confidence_score": Decimal("0.90"),
        })

    stocks = list(
        Inventory.objects.filter(organization=organization)
        .select_related("product")
    )

    low = min(
        (s for s in stocks if 0 < s.quantity <= s.minimum_stock),
        key=lambda s: s.quantity,
        default=None,
    )
    if low:
        candidates.append({
            "title": f"Low stock: {low.product.name}",
            "description": (
                f"{low.product.name} has {low.quantity} units left "
                f"(minimum {low.minimum_stock})."
            ),
            "insight_type": "LOW_STOCK",
            "confidence_score": Decimal("0.85"),
        })

    out = next((s for s in stocks if s.quantity == 0), None)
    if out:
        candidates.append({
            "title": f"Out of stock: {out.product.name}",
            "description": f"{out.product.name} is currently out of stock.",
            "insight_type": "LOW_STOCK",
            "confidence_score": Decimal("0.70"),
        })

    top_reorder = max(
        get_recommendations(organization),
        key=lambda r: r["recommended_order"],
        default=None,
    )
    if top_reorder and top_reorder["recommended_order"] > 0:
        candidates.append({
            "title": f"Restock: {top_reorder['product_name']}",
            "description": (
                f"Order about {top_reorder['recommended_order']} units of "
                f"{top_reorder['product_name']} to cover expected demand "
                f"({top_reorder['current_stock']} units in stock)."
            ),
            "insight_type": "RECOMMENDATION",
            "confidence_score": Decimal("0.85"),
        })

    forecast = _safe_forecast(organization)
    if forecast:
        highest = max(
            forecast,
            key=lambda x: x["predicted_quantity"],
        )
        candidates.append({
            "title": f"Demand forecast: {highest['product_name']}",
            "description": (
                f"{highest['product_name']} is expected to see the highest "
                f"demand next ({highest['predicted_quantity']} units)."
            ),
            "insight_type": "FORECAST",
            "confidence_score": Decimal("0.80"),
        })

    total_sold = (
        SaleItem.objects.filter(sale__organization=organization)
        .aggregate(total=Sum("quantity"))["total"] or 0
    )
    if total_sold > 0:
        invoice_count = (
            SaleItem.objects.filter(sale__organization=organization)
            .values("sale_id")
            .distinct()
            .count()
        )
        candidates.append({
            "title": "Sales activity snapshot",
            "description": (
                f"{total_sold} units have been sold across {invoice_count} "
                "invoices in the current period."
            ),
            "insight_type": "ANALYSIS",
            "confidence_score": Decimal("0.90"),
        })

    return candidates


def persist_generated_insights(organization=None):
    """
    Persist only the missing generated insights for ``organization``.

    - Existing insights are never deleted, edited or deactivated, whether
      they were created manually or seeded earlier.
    - Before creating a new insight, a conservative duplicate check runs on
      ``organization`` + ``insight_type`` + case-insensitive ``title``.
    - Existing insights stay visible and editable through the AI Insights
      CRUD page.
    - Safe to run multiple times: matches are skipped, never overwritten.
    """
    created = []
    skipped = []
    if organization is None:
        return {"created": created, "skipped": skipped}

    for candidate in build_insight_candidates(organization):
        duplicate = AIInsight.objects.filter(
            organization=organization,
            insight_type=candidate["insight_type"],
            title__iexact=candidate["title"],
        ).exists()
        if duplicate:
            skipped.append(candidate["title"])
            continue
        AIInsight.objects.create(
            organization=organization,
            title=candidate["title"],
            description=candidate["description"],
            insight_type=candidate["insight_type"],
            confidence_score=candidate["confidence_score"],
        )
        created.append(candidate["title"])

    return {"created": created, "skipped": skipped}