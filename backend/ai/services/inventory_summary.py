"""
Rule-based, human-readable AI Inventory Summary.

Every number and condition in the summary is derived from the existing,
tenant-scoped BI tools in ``ai.services.tools`` — no fabrication. The
``organization`` is always passed in by the view from the authenticated user;
this module never reads it from the request. When a tenant has no inventory,
the summary reports that explicitly instead of inventing conditions.
"""

from . import tools


def _format_money(value):
    return f"Rs. {value:,.2f}"


def build_inventory_summary(organization):
    """Return a concise, factual inventory summary for one tenant."""
    metrics = tools.dashboard_metrics(organization)

    product_count = metrics["product_count"]
    stock_units = metrics["stock_units"]
    stock_value = metrics["stock_value"]
    low_stock_count = metrics["low_stock_count"]
    out_of_stock_count = metrics["out_of_stock_count"]
    products_with_no_sales = metrics["products_with_no_sales"]
    sales_count = metrics["sales_count"]
    sales_revenue = metrics["sales_revenue"]

    if product_count == 0:
        return {
            "has_data": False,
            "overall_condition": "No Inventory",
            "summary": (
                "No inventory has been recorded for this organization yet. "
                "Add products and stock levels to see an inventory summary."
            ),
            "population": {
                "product_count": 0,
                "stock_units": 0,
                "stock_value": 0.0,
            },
            "stock_health": {
                "low_stock_count": 0,
                "out_of_stock_count": 0,
                "products_with_no_sales": 0,
                "sales_count": 0,
                "sales_revenue": 0.0,
            },
            "low_stock": [],
            "out_of_stock": [],
            "no_sales": [],
            "observations": [],
            "recommended_actions": [],
        }

    low = tools.low_stock_products(organization, limit=10)
    out = tools.out_of_stock_products(organization, limit=10)
    no_sales_list = tools.business_attention(organization, limit=10)[
        "products_with_no_sales"
    ]
    best = tools.products_ranking(organization, "units_sold", "desc", limit=1)[
        "items"
    ]

    sentences = [
        (
            f"You have {product_count} products tracked with "
            f"{stock_units} units in stock, valued at {_format_money(stock_value)}."
        )
    ]

    if out_of_stock_count:
        sentences.append(f"{out_of_stock_count} products are out of stock.")
    if low_stock_count:
        sentences.append(
            f"{low_stock_count} products are at or below their minimum stock level."
        )
    if out_of_stock_count == 0 and low_stock_count == 0:
        sentences.append("All tracked products are above their minimum stock levels.")

    if sales_count:
        sentences.append(
            f"You have recorded {sales_count} sales worth {_format_money(sales_revenue)}."
        )
    if products_with_no_sales:
        sentences.append(f"{products_with_no_sales} products have no recorded sales.")

    observations = []
    if no_sales_list:
        names = ", ".join(p["name"] for p in no_sales_list[:3])
        observations.append(f"Products with no sales: {names}.")
    top_seller = best[0] if best else None
    if top_seller and top_seller["units_sold"]:
        observations.append(
            f"Best seller: {top_seller['name']} ({top_seller['units_sold']} units, "
            f"{_format_money(top_seller['sales_revenue'])})."
        )

    if sales_count == 0:
        observations.append("No sales have been recorded yet.")

    out_names = {item["sku"] for item in out["items"]}
    recommended_actions = []
    for item in out["items"]:
        recommended_actions.append(
            f"Restock {item['name']} (currently out of stock)."
        )
    for item in low["items"]:
        if item["sku"] in out_names:
            continue
        recommended_actions.append(
            f"Restock {item['name']} to its minimum of "
            f"{item['minimum_stock']} units (currently {item['quantity']} units)."
        )
    for product in no_sales_list:
        recommended_actions.append(
            f"Review {product['name']} — it has no recorded sales yet."
        )
    if not recommended_actions:
        recommended_actions.append("No restock actions are needed right now.")

    if out_of_stock_count:
        condition = "Needs Attention"
    elif low_stock_count:
        condition = "Low Stock Alert"
    elif products_with_no_sales:
        condition = "Monitor"
    else:
        condition = "Healthy"

    return {
        "has_data": True,
        "overall_condition": condition,
        "summary": " ".join(sentences),
        "population": {
            "product_count": product_count,
            "stock_units": stock_units,
            "stock_value": stock_value,
        },
        "stock_health": {
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "products_with_no_sales": products_with_no_sales,
            "sales_count": sales_count,
            "sales_revenue": sales_revenue,
        },
        "low_stock": low["items"],
        "out_of_stock": out["items"],
        "no_sales": no_sales_list,
        "observations": observations,
        "recommended_actions": recommended_actions[:8],
    }