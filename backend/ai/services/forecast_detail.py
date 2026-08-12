"""
Product-specific weekly demand forecasting.

Context
-------
The existing ``forecasting.forecast_demand`` produces one predicted
quantity per product and hides its training series, so it cannot answer
"show me this product's weekly history and its next 4 weeks". This module
builds a real product-specific weekly forecast from actual
``SaleItem``/``Sale`` data only.

- Historical period : the last ``HISTORICAL_WEEKS`` calendar weeks
  (Monday-aligned). Weeks with no sales are zero-filled so the series is
  continuous and an absent record is never mistaken for absent time.
- Forecast period   : the next ``FORECAST_WEEKS`` calendar weeks (4).
- Granularity       : weekly.

Model
-----
``RandomForestRegressor`` is deliberately NOT used here: a 12-week series
(with the project's demo data typically only a handful of non-zero weeks)
is far too short to fit a forest meaningfully. The forecast instead uses a
transparent, statistically defensible method identified in every response:

1. Build the weekly series for the product (zeros included).
2. Fit a least-squares linear trend over the 12 weeks.
3. Base rate = recent-weighted weekly average (last 6 weeks weighted 2x).
4. Forecast week ``i`` = ``max(0, round(base + slope * (i + 0.5)))``.

A product is forecasted only when its truthful history clears strict minima
(``MIN_SALE_ITEMS`` rows and ``MIN_NONZERO_WEEKS`` distinct non-zero weeks);
otherwise ``status: "insufficient_data"`` is returned instead of a
fabricated series. ``trend`` compares the last-4-week average against the
prior-8-week average with a documented 10% band.

Tenant safety
-------------
``organization`` is supplied by the view from the authenticated user and is
the only tenant identity this module ever reads.
"""

from datetime import date, timedelta

from sales.models import SaleItem
from inventory.models import Product, Inventory

HISTORICAL_WEEKS = 12
FORECAST_WEEKS = 4
MIN_SALE_ITEMS = 3
MIN_NONZERO_WEEKS = 4
TREND_THRESHOLD_PERCENT = 10.0
METHOD = "trend_adjusted_weekly_average"
METHOD_NOTE = (
    "RandomForest is unsuitable for such a short weekly series; the rate is "
    "a recent-weighted weekly average adjusted by the least-squares linear "
    "trend over the last 12 weeks."
)


def _week_start(day):
    return day - timedelta(days=day.weekday())


def _iso(day):
    return day.isoformat()


def _classify_trend(recent_mean, prior_mean):
    """Last-4-week average vs prior-8-week average with a 10% band."""
    if recent_mean <= 0 and prior_mean <= 0:
        return "stable"
    if prior_mean <= 0:
        return "increasing" if recent_mean > 0 else "stable"
    change = (recent_mean - prior_mean) / prior_mean * 100.0
    if change > TREND_THRESHOLD_PERCENT:
        return "increasing"
    if change < -TREND_THRESHOLD_PERCENT:
        return "decreasing"
    return "stable"


def _linear_trend(values):
    """Least-squares slope/intercept over x = 0..n-1."""
    n = len(values)
    if n < 2:
        return 0.0, float(values[0]) if values else 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    sxx = sum((i - mean_x) ** 2 for i in range(n))
    sxy = sum((i - mean_x) * (y - mean_y) for i, y in enumerate(values))
    slope = sxy / sxx if sxx else 0.0
    return slope, mean_y - slope * mean_x


def _product_payload(product, weekly, sale_rows, historical_starts,
                     forecast_starts):
    """Structured forecast/insufficient-data payload for one product."""
    nonzero_count = sum(1 for u in weekly if u > 0)
    product_info = {"id": product.pk, "name": product.name}

    if nonzero_count < MIN_NONZERO_WEEKS or sale_rows < MIN_SALE_ITEMS:
        return {
            "product": product_info,
            "forecastable": False,
            "status": "insufficient_data",
            "message": (
                "Not enough sales history to generate a reliable forecast. "
                "Demand forecasting requires more historical sales for this "
                "product."
            ),
            "observed_weeks": nonzero_count,
            "sale_rows": sale_rows,
            "historical": None,
            "forecast": None,
            "forecast_total": None,
            "average_weekly_demand": None,
            "trend": None,
            "trend_basis": None,
            "method": None,
            "current_stock": None,
            "minimum_stock": None,
            "stock_coverage_weeks": None,
        }

    series_total = sum(weekly)
    avg_weekly = round(series_total / float(HISTORICAL_WEEKS))
    recent = sum(weekly[-4:]) / 4.0
    prior = sum(weekly[:8]) / 8.0
    trend = _classify_trend(recent, prior)

    weights = [1.0] * HISTORICAL_WEEKS
    for i in range(HISTORICAL_WEEKS - 6, HISTORICAL_WEEKS):
        weights[i] = 2.0
    base_rate = sum(u * w for u, w in zip(weekly, weights)) / sum(weights)

    slope, _intercept = _linear_trend(weekly)
    forecast = [
        max(0, round(base_rate + slope * (i + 0.5)))
        for i in range(FORECAST_WEEKS)
    ]

    inventory = Inventory.objects.filter(
        organization=product.organization, product=product
    ).first()
    current_stock = inventory.quantity if inventory else None
    minimum_stock = inventory.minimum_stock if inventory else None
    coverage = (
        round(current_stock / avg_weekly, 1)
        if current_stock is not None and avg_weekly > 0
        else None
    )

    return {
        "product": product_info,
        "forecastable": True,
        "status": "ok",
        "message": "Forecast generated successfully.",
        "observed_weeks": nonzero_count,
        "sale_rows": sale_rows,
        "method": METHOD,
        "method_note": METHOD_NOTE,
        "historical": [
            {"week": _iso(historical_starts[i]), "units": weekly[i]}
            for i in range(HISTORICAL_WEEKS)
        ],
        "forecast": [
            {"week": _iso(forecast_starts[i]), "units": forecast[i]}
            for i in range(FORECAST_WEEKS)
        ],
        "forecast_total": sum(forecast),
        "average_weekly_demand": avg_weekly,
        "trend": trend,
        "trend_basis": (
            f"last-4-week avg {recent:.1f} vs prior-8-week avg {prior:.1f} "
            f"| band {TREND_THRESHOLD_PERCENT:.0f}%"
        ),
        "current_stock": current_stock,
        "minimum_stock": minimum_stock,
        "stock_coverage_weeks": coverage,
    }


def build_forecast_detail(organization=None, today=None):
    """Return product-specific weekly forecasts for ``organization``.

    ``organization`` must be the authenticated user's tenant; it is never
    read from client input. Products with recent sales inside the window are
    reported individually (forecastable or insufficient-data) sorted with
    forecastable products first, then by forecast size.
    """
    today = _week_start(today or date.today())
    historical_starts = [
        today - timedelta(weeks=HISTORICAL_WEEKS - 1 - i)
        for i in range(HISTORICAL_WEEKS)
    ]
    forecast_starts = [
        today + timedelta(weeks=i) for i in range(1, FORECAST_WEEKS + 1)
    ]
    week_index = {
        week: i for i, week in enumerate(historical_starts)
    }

    buckets = {}
    rows = {}
    items = SaleItem.objects.filter(
        sale__organization=organization
    ).select_related("sale", "product")
    for sale_item in items:
        week = _week_start(sale_item.sale.sale_date)
        idx = week_index.get(week)
        if idx is None:
            continue
        bucket = buckets.setdefault(
            sale_item.product_id, [0] * HISTORICAL_WEEKS
        )
        bucket[idx] += sale_item.quantity
        rows[sale_item.product_id] = rows.get(sale_item.product_id, 0) + 1

    products = {
        p.pk: p for p in Product.objects.filter(organization=organization)
    }

    payload = [
        _product_payload(
            products[product_id],
            weekly,
            rows[product_id],
            historical_starts,
            forecast_starts,
        )
        for product_id, weekly in buckets.items()
        if product_id in products
    ]
    payload.sort(
        key=lambda item: (
            not item["forecastable"],
            -(item["forecast_total"] or 0),
            item["product"]["name"].lower(),
        )
    )

    return {
        "granularity": "week",
        "historical_weeks": HISTORICAL_WEEKS,
        "forecast_weeks": FORECAST_WEEKS,
        "method": METHOD,
        "method_note": METHOD_NOTE,
        "window_start": _iso(historical_starts[0]),
        "window_end": _iso(historical_starts[-1]),
        "products": payload,
    }