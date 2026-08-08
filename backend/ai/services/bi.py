"""
Read-only business-intelligence aggregation for the AI dashboard.

This module contains NO business logic of its own. Every section is
produced by reusing the existing, tenant-scoped tools in
``ai.services.tools``; the ``organization`` used by every tool is always
derived from the authenticated user by the view, never accepted from the
client. The functions here only select which tools to call and organise
their results into a stable, predictable response structure.
"""

from . import tools


def _window_payloads(window, with_bucket=False):
    """Pick the reporting-window keys the BI tools understand.

    Values are already server-side validated by the view; only known keys are
    forwarded so unknown or empty values never reach the aggregation tools.
    ``bucket`` is only forwarded to the trend tool, which is the only consumer
    that understands chart bucketing.
    """
    kwargs = {
        key: window[key]
        for key in ("days", "period", "start_date", "end_date")
        if window.get(key) is not None
    }
    if with_bucket and window.get("bucket"):
        kwargs["bucket"] = window["bucket"]
    return kwargs


def get_business_intelligence(organization, window=None):
    """Compose stable, read-only, tenant-scoped BI sections from BI tools.

    ``window`` (optional) carries validated reporting-window parameters that
    are forwarded to the time-aware sales/purchase tools. When omitted, the
    tools use their defaults (30-day summary, 90-day month-bucketed trend),
    which keeps the response stable for existing callers.
    """
    window = window or {}
    sales_kwargs = _window_payloads(window)
    trend_kwargs = _window_payloads(window, with_bucket=True)

    return {
        "business_overview": tools.business_summary(organization),
        "dashboard_metrics": tools.dashboard_metrics(organization),
        "sales_intelligence": {
            "summary": tools.sales_summary(organization, **sales_kwargs),
            "trend": tools.sales_trend(organization, **trend_kwargs),
            "growth": tools.sales_growth(organization, **sales_kwargs),
            "top_products": tools.products_ranking(
                organization, metric="units_sold", order="desc", limit=5
            )["items"],
        },
        "inventory_intelligence": {
            "summary": tools.inventory_summary(organization, limit=30),
            "low_stock": tools.low_stock_products(organization, limit=10),
            "out_of_stock": tools.out_of_stock_products(organization, limit=10),
        },
        "purchase_intelligence": {
            "summary": tools.purchases_summary(organization, **sales_kwargs),
            "by_supplier": tools.purchases_breakdown(
                organization, group_by="supplier", limit=5, **sales_kwargs
            )["items"],
        },
        "business_attention": tools.business_attention(organization, limit=5),
    }