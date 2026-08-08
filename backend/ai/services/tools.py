"""
Controlled, tenant-scoped data tools for the AI assistant.

Groq has NO direct database access. The only way it can learn about a
tenant's data is by calling one of the functions below, and every function
enforces ``organization`` filtering in server-side code. The ``organization``
argument is always supplied by the backend from the authenticated user; the
model can never request another tenant's organization.

Tools cover the full business-intelligence surface: products, inventory,
sales, purchases, customers, suppliers, categories, stock movements and
overall business analysis. Every monetary value is in Nepalese Rupees (NPR)
and is returned as a plain number; the assistant renders it as ``Rs.``.

All functions return plain JSON-serializable structures.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import (
    Sum,
    Count,
    Q,
    F,
    Value,
    DecimalField,
)
from django.db.models.functions import Coalesce
from django.db.models import OuterRef, Subquery

from customers.models import Customer
from suppliers.models import Supplier
from inventory.models import (
    Inventory,
    Product,
    Category,
    StockMovement,
)
from sales.models import Sale, SaleItem
from purchases.models import Purchase, PurchaseItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DECIMAL = DecimalField(max_digits=14, decimal_places=2)


def _num(value):
    """Safely convert Decimal/int/float to a JSON-friendly number."""
    if isinstance(value, Decimal):
        return float(value)
    return value


def _money(amount):
    """Convert a money value (Decimal/None) to a JSON-friendly float."""
    if amount is None:
        return 0.0
    return float(amount)


def _iso(d):
    """ISO string for a date (or None)."""
    return d.isoformat() if isinstance(d, date) else None


def _as_date(value):
    """Coerce a date/datetime/ISO-ish string into a date, else None."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _period_bounds(period, today=None):
    """Map a human date-period label to an inclusive ``(start, end)`` tuple.

    Supported labels: today, yesterday, this_week, last_week, this_month,
    last_month, last_7_days, last_30_days, this_year, last_year, all.
    Returns an empty tuple for unknown labels so callers fall back to the
    default trailing ``days`` window.
    """
    today = today or date.today()
    p = (period or "").strip().lower()
    if p in ("all", "all_time", ""):
        return (None, None)

    first_of_month = today.replace(day=1)
    first_of_last_month = (first_of_month - timedelta(days=1)).replace(day=1)

    starts = {
        "today": today,
        "yesterday": today - timedelta(days=1),
        "this_week": today - timedelta(days=today.weekday()),
        "last_week": today - timedelta(days=today.weekday() + 7),
        "this_month": first_of_month,
        "last_month": first_of_last_month,
        "last_7_days": today - timedelta(days=6),
        "7_days": today - timedelta(days=6),
        "last_30_days": today - timedelta(days=29),
        "30_days": today - timedelta(days=29),
        "this_year": date(today.year, 1, 1),
        "last_year": date(today.year - 1, 1, 1),
        "week": today - timedelta(days=today.weekday()),
        "month": first_of_month,
    }
    ends = {
        "yesterday": today - timedelta(days=1),
        "last_week": today - timedelta(days=today.weekday() + 1),
        "last_month": first_of_month - timedelta(days=1),
        "last_year": date(today.year - 1, 12, 31),
    }
    start = starts.get(p)
    if start is None:
        return ()
    return (start, ends.get(p, today))


def _resolve_window(days=30, period=None, start_date=None, end_date=None):
    """Resolve an inclusive ``(start, end)`` date window for reporting tools.

    Priority: explicit ``start_date``/``end_date`` > ``period`` label >
    trailing ``days`` window. ``all``/``all_time`` means full history.
    """
    today = date.today()
    start = _as_date(start_date)
    end = _as_date(end_date)

    if start is None and period:
        bounds = _period_bounds(period, today)
        if bounds:
            b_start, b_end = bounds
            if b_start is None:
                start = None  # all-time
            else:
                start = b_start
                if end is None:
                    end = b_end

    if start is None:
        if (period and not _period_bounds(period, today)) or not period:
            start = today - timedelta(days=max(1, int(days or 30)))
        else:
            start = date(1970, 1, 1)
    if end is None:
        end = today
    if start > end:
        start, end = end, start
    return start, end


def _annotated_products(organization):
    """Products with aggregate sales + inventory numbers (org-scoped)."""
    inventory_totals = (
        Inventory.objects.filter(product_id=OuterRef("pk"))
        .values("product_id")
        .annotate(total=Sum("quantity"))
        .values("total")
    )
    return (
        Product.objects.filter(organization=organization)
        .select_related("category")
        .annotate(
            units_sold=Coalesce(Sum("saleitem__quantity"), 0),
            sales_count=Coalesce(Count("saleitem"), 0),
            sales_revenue=Coalesce(
                Sum(
                    F("saleitem__quantity") * F("saleitem__unit_price"),
                    output_field=_DECIMAL,
                ),
                Value(0),
                output_field=_DECIMAL,
            ),
            current_stock=Coalesce(Subquery(inventory_totals), 0),
        )
    )


def _product_row(p):
    """Serialize an annotated Product to a JSON-friendly dict."""
    return {
        "name": p.name,
        "sku": p.sku,
        "category": p.category.name if p.category_id else None,
        "buying_price": _money(p.buying_price),
        "selling_price": _money(p.selling_price),
        "units_sold": _num(p.units_sold) or 0,
        "sales_count": _num(p.sales_count) or 0,
        "sales_revenue": _money(p.sales_revenue),
        "current_stock": _num(p.current_stock) or 0,
    }


# ---------------------------------------------------------------------------
# PRODUCTS
# ---------------------------------------------------------------------------

def product_search(organization, query=None, category=None, limit=25):
    """Search products by a partial name/SKU/barcode match or by category."""
    filters = Q()
    if query:
        filters &= (
            Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(barcode__icontains=query)
        )
    if category:
        filters &= Q(category__name__iexact=category)

    qs = _annotated_products(organization)
    if filters:
        qs = qs.filter(filters)
    rows = list(qs.order_by("name")[: int(limit or 25)])
    return {
        "query": query or "",
        "category": category or "",
        "count": len(rows),
        "items": [_product_row(p) for p in rows],
    }


def products_ranking(organization, metric="units_sold", order="desc", limit=10):
    """Rank products by a metric.

    Supported ``metric`` values:
      - ``selling_price`` / ``buying_price`` (most/least expensive)
      - ``stock`` (highest/lowest current stock)
      - ``units_sold`` / ``sales_revenue`` (most/least sold, best sellers)
      - ``sales_count`` (number of sale invoices touching the product)
      - ``margin`` (selling minus buying)
      - ``recent`` (newest products first)
      - ``name`` (alphabetical)
    """
    metric = (metric or "units_sold").strip().lower()
    order = (order or "desc").strip().lower()
    direction = "-" if order in ("desc", "descending", "d") else ""

    products = _annotated_products(organization)

    sort_fields = {
        "selling_price": "selling_price",
        "buying_price": "buying_price",
        "stock": "current_stock",
        "units_sold": "units_sold",
        "sales_revenue": "sales_revenue",
        "sales": "sales_revenue",
        "sales_count": "sales_count",
        "recent": "created_at",
        "name": "name",
    }
    field = sort_fields.get(metric)

    if metric == "margin":
        products = products.annotate(margin=F("selling_price") - F("buying_price"))
        rows = list(products.order_by(direction + "margin")[: int(limit or 10)])
        items = []
        for p in rows:
            row = _product_row(p)
            row["margin"] = _money(p.margin)
            items.append(row)
    elif field:
        rows = list(products.order_by(direction + field)[: int(limit or 10)])
        items = [_product_row(p) for p in rows]
    else:
        # Unknown metric -> fall back to best sellers.
        rows = list(products.order_by("-units_sold")[: int(limit or 10)])
        items = [_product_row(p) for p in rows]

    return {
        "metric": metric,
        "order": order,
        "limit": int(limit or 10),
        "items": items,
    }


# ---------------------------------------------------------------------------
# INVENTORY
# ---------------------------------------------------------------------------

def inventory_summary(organization, limit=50):
    """List current inventory with quantity and valuation per product."""
    base = Inventory.objects.filter(organization=organization)
    total_units = base.aggregate(total=Sum("quantity"))["total"] or 0
    total_value = base.aggregate(
        value=Sum(
            F("quantity") * F("product__buying_price"),
            output_field=_DECIMAL,
        )
    )["value"] or 0
    rows = (
        base.select_related("product__category")
        .order_by("product__name")[: int(limit or 50)]
    )
    return {
        "total_items": base.count(),
        "total_units": total_units,
        "total_value": _money(total_value),
        "items": [
            {
                "name": inv.product.name,
                "sku": inv.product.sku,
                "category": (
                    inv.product.category.name
                    if inv.product.category_id
                    else None
                ),
                "quantity": inv.quantity,
                "minimum_stock": inv.minimum_stock,
                "maximum_stock": inv.maximum_stock,
                "stock_value": _money(inv.quantity * inv.product.buying_price),
                "status": inv.stock_status,
            }
            for inv in rows
        ],
    }


def low_stock_products(organization, limit=25):
    """Products at or below their minimum stock level (need reorder)."""
    rows = (
        Inventory.objects.filter(
            organization=organization,
            quantity__lte=F("minimum_stock"),
        )
        .select_related("product")
        .order_by("quantity")[: int(limit or 25)]
    )
    return {
        "count": Inventory.objects.filter(
            organization=organization,
            quantity__lte=F("minimum_stock"),
        ).count(),
        "items": [
            {
                "name": inv.product.name,
                "sku": inv.product.sku,
                "quantity": inv.quantity,
                "minimum_stock": inv.minimum_stock,
                "to_reorder": max(inv.minimum_stock - inv.quantity, 0),
            }
            for inv in rows
        ],
    }


def out_of_stock_products(organization, limit=25):
    """Products with zero stock available."""
    rows = (
        Inventory.objects.filter(organization=organization, quantity=0)
        .select_related("product")
        .order_by("product__name")[: int(limit or 25)]
    )
    return {
        "count": Inventory.objects.filter(
            organization=organization, quantity=0
        ).count(),
        "items": [{"name": inv.product.name, "sku": inv.product.sku} for inv in rows],
    }


def stock_movements(
    organization,
    limit=50,
    movement_type=None,
    start_date=None,
    end_date=None,
):
    """Recent stock movements, optionally filtered by type and date range."""
    qs = StockMovement.objects.filter(organization=organization)
    if movement_type:
        qs = qs.filter(movement_type__iexact=movement_type)
    if start_date or end_date:
        start, end = _resolve_window(
            days=365, start_date=start_date, end_date=end_date
        )
        qs = qs.filter(
            created_at__date__gte=start,
            created_at__date__lte=end,
        )
    rows = list(qs.select_related("product").order_by("-created_at")[: int(limit or 50)])

    totals = {"IN": 0, "OUT": 0, "ADJUSTMENT": 0}
    for mv in rows:
        totals[mv.movement_type] = totals.get(mv.movement_type, 0) + mv.quantity

    return {
        "count": len(rows),
        "movement_type": movement_type or "all",
        "totals": totals,
        "net_change": totals.get("IN", 0) - totals.get("OUT", 0),
        "items": [
            {
                "product": mv.product.name,
                "sku": mv.product.sku,
                "movement_type": mv.movement_type,
                "quantity": mv.quantity,
                "remarks": mv.remarks or "",
                "created_by": (
                    mv.created_by.username if mv.created_by_id else "System"
                ),
                "date": _iso(mv.created_at.date()),
            }
            for mv in rows
        ],
    }


# ---------------------------------------------------------------------------
# SALES
# ---------------------------------------------------------------------------

def sales_summary(
    organization,
    days=30,
    period=None,
    start_date=None,
    end_date=None,
):
    """Sales summary for a date window: count, revenue, avg, extremes, recent."""
    start, end = _resolve_window(
        days=days, period=period, start_date=start_date, end_date=end_date
    )
    sales = Sale.objects.filter(
        organization=organization,
        sale_date__gte=start,
        sale_date__lte=end,
    )
    agg = sales.aggregate(total=Sum("total_amount"), count=Count("id"))
    total = _money(agg["total"])
    count = agg["count"] or 0

    latest = list(sales.order_by("-sale_date", "-created_at")[:5])
    highest = list(sales.order_by("-total_amount")[:1])
    lowest = list(sales.order_by("total_amount")[:1])

    return {
        "period_start": _iso(start),
        "period_end": _iso(end),
        "period_days": days,
        "sales_in_period": count,
        "revenue_in_period": total,
        "average_sale_value": (total / count) if count else 0.0,
        "highest_sale": (
            {
                "invoice": highest[0].invoice_number,
                "amount": _money(highest[0].total_amount),
                "date": _iso(highest[0].sale_date),
            }
            if highest
            else None
        ),
        "lowest_sale": (
            {
                "invoice": lowest[0].invoice_number,
                "amount": _money(lowest[0].total_amount),
                "date": _iso(lowest[0].sale_date),
            }
            if lowest
            else None
        ),
        "recent_sales": [
            {
                "invoice": s.invoice_number,
                "date": _iso(s.sale_date),
                "total": _money(s.total_amount),
                "payment_status": s.payment_status,
            }
            for s in latest
        ],
    }


def sales_breakdown(
    organization,
    group_by="product",
    limit=10,
    days=30,
    period=None,
    start_date=None,
    end_date=None,
):
    """Aggregate sales by product or customer for a date window."""
    start, end = _resolve_window(
        days=days, period=period, start_date=start_date, end_date=end_date
    )
    items = SaleItem.objects.filter(
        sale__organization=organization,
        sale__sale_date__gte=start,
        sale__sale_date__lte=end,
    )
    limit = int(limit or 10)
    group_by = (group_by or "product").strip().lower()

    if group_by in ("customer", "customers"):
        grouped = {}
        sales = Sale.objects.filter(
            organization=organization,
            sale_date__gte=start,
            sale_date__lte=end,
        ).select_related("customer")
        for sale in sales:
            key = sale.customer_id if sale.customer_id else "walk-in"
            name = (
                f"{sale.customer.first_name} {sale.customer.last_name}".strip()
                if sale.customer_id
                else "Walk-in Customer"
            )
            bucket = grouped.setdefault(
                key, {"name": name, "units": 0, "revenue": 0.0, "invoices": 0}
            )
            bucket["revenue"] += _money(sale.total_amount)
            bucket["invoices"] += 1
        for si in items.select_related("sale"):
            key = si.sale.customer_id if si.sale.customer_id else "walk-in"
            bucket = grouped.get(key)
            if bucket:
                bucket["units"] += si.quantity
        rows = sorted(grouped.values(), key=lambda g: g["revenue"], reverse=True)[:limit]
        return {
            "group_by": "customer",
            "period_start": _iso(start),
            "period_end": _iso(end),
            "items": rows,
        }

    grouped = {}
    for si in items.select_related("product"):
        bucket = grouped.setdefault(
            si.product_id,
            {"product": si.product.name, "units": 0, "revenue": 0.0, "invoices": 0},
        )
        bucket["units"] += si.quantity
        bucket["revenue"] += _money(si.quantity * si.unit_price)
        bucket["invoices"] += 1
    rows = sorted(grouped.values(), key=lambda g: g["revenue"], reverse=True)[:limit]
    return {
        "group_by": "product",
        "period_start": _iso(start),
        "period_end": _iso(end),
        "items": rows,
    }


def sales_trend(
    organization,
    bucket="month",
    days=90,
    period=None,
    start_date=None,
    end_date=None,
):
    """Sales trend bucketed by day, week or month over a date window."""
    start, end = _resolve_window(
        days=days, period=period, start_date=start_date, end_date=end_date
    )
    bucket = (bucket or "month").strip().lower()
    items = SaleItem.objects.filter(
        sale__organization=organization,
        sale__sale_date__gte=start,
        sale__sale_date__lte=end,
    ).select_related("sale")

    points = {}
    for si in items:
        d = si.sale.sale_date
        if bucket in ("day", "d", "daily"):
            key = d
            label = _iso(d)
        elif bucket in ("week", "w", "weekly"):
            key = d - timedelta(days=d.weekday())
            label = _iso(key)
        else:  # month default
            key = d.replace(day=1)
            label = _iso(key)

        bucket_data = points.setdefault(
            key, {"label": label, "sales": 0, "revenue": 0.0, "units": 0}
        )
        bucket_data["sales"] += 1
        bucket_data["revenue"] += _money(si.quantity * si.unit_price)
        bucket_data["units"] += si.quantity

    keys = sorted(points)
    series = []
    for index, key in enumerate(keys):
        point = points[key]
        if index == 0:
            point["growth_percent"] = None
            point["direction"] = "flat"
        else:
            previous_revenue = points[keys[index - 1]]["revenue"]
            current_revenue = point["revenue"]
            if previous_revenue:
                growth = round(
                    ((current_revenue - previous_revenue) / previous_revenue) * 100,
                    1,
                )
                point["growth_percent"] = growth
                point["direction"] = (
                    "up"
                    if growth > 0
                    else "down"
                    if growth < 0
                    else "flat"
                )
            else:
                point["growth_percent"] = None
                point["direction"] = "flat"
        series.append(point)
    return {
        "bucket": bucket,
        "period_start": _iso(start),
        "period_end": _iso(end),
        "total_sales": len(items),
        "points": series,
    }


def sales_growth(
    organization,
    days=30,
    period=None,
    start_date=None,
    end_date=None,
):
    """Compare the current window's sales revenue/units against the previous
    equal-length window, returning period-over-period growth percentages.

    The previous window is the same length as the resolved reporting window
    immediately before it. Growth is always derived from the tenant's own
    sales data. When there is no previous window (or no revenue in it) the
    percent is ``None`` and ``direction`` is ``flat`` so callers can render a
    neutral state instead of fabricating a number.
    """
    start, end = _resolve_window(
        days=days, period=period, start_date=start_date, end_date=end_date
    )
    window_days = max(1, (end - start).days)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=window_days - 1)

    current_sales = Sale.objects.filter(
        organization=organization,
        sale_date__gte=start,
        sale_date__lte=end,
    )
    previous_sales = Sale.objects.filter(
        organization=organization,
        sale_date__gte=previous_start,
        sale_date__lte=previous_end,
    )

    revenue_now = _money(current_sales.aggregate(total=Sum("total_amount"))["total"])
    revenue_prev = _money(previous_sales.aggregate(total=Sum("total_amount"))["total"])

    units_now = _num(
        SaleItem.objects.filter(
            sale__organization=organization,
            sale__sale_date__gte=start,
            sale__sale_date__lte=end,
        ).aggregate(total=Sum("quantity"))["total"]
    ) or 0
    units_prev = _num(
        SaleItem.objects.filter(
            sale__organization=organization,
            sale__sale_date__gte=previous_start,
            sale__sale_date__lte=previous_end,
        ).aggregate(total=Sum("quantity"))["total"]
    ) or 0

    def _percent(current, previous):
        if previous:
            return round(((current - previous) / previous) * 100, 1)
        return None

    revenue_growth = _percent(revenue_now, revenue_prev)
    units_growth = _percent(float(units_now), float(units_prev))

    if revenue_growth is None or revenue_growth == 0:
        direction = "flat"
    elif revenue_growth > 0:
        direction = "up"
    else:
        direction = "down"

    return {
        "window_start": _iso(start),
        "window_end": _iso(end),
        "previous_start": _iso(previous_start),
        "previous_end": _iso(previous_end),
        "current_revenue": revenue_now,
        "previous_revenue": revenue_prev,
        "revenue_growth_percent": revenue_growth,
        "current_units": units_now,
        "previous_units": units_prev,
        "units_growth_percent": units_growth,
        "direction": direction,
    }


# ---------------------------------------------------------------------------
# PURCHASES
# ---------------------------------------------------------------------------

def purchases_summary(
    organization,
    days=30,
    period=None,
    start_date=None,
    end_date=None,
):
    """Purchase summary for a date window: count, spend, avg, extremes."""
    start, end = _resolve_window(
        days=days, period=period, start_date=start_date, end_date=end_date
    )
    purchases = Purchase.objects.filter(
        organization=organization,
        purchase_date__gte=start,
        purchase_date__lte=end,
    )
    agg = purchases.aggregate(total=Sum("total_amount"), count=Count("id"))
    total = _money(agg["total"])
    count = agg["count"] or 0

    latest = list(purchases.order_by("-purchase_date", "-created_at")[:5])
    highest = list(purchases.order_by("-total_amount")[:1])
    lowest = list(purchases.order_by("total_amount")[:1])

    return {
        "period_start": _iso(start),
        "period_end": _iso(end),
        "purchases_in_period": count,
        "spend_in_period": total,
        "average_purchase_value": (total / count) if count else 0.0,
        "highest_purchase": (
            {
                "invoice": highest[0].invoice_number,
                "amount": _money(highest[0].total_amount),
                "date": _iso(highest[0].purchase_date),
            }
            if highest
            else None
        ),
        "lowest_purchase": (
            {
                "invoice": lowest[0].invoice_number,
                "amount": _money(lowest[0].total_amount),
                "date": _iso(lowest[0].purchase_date),
            }
            if lowest
            else None
        ),
        "recent_purchases": [
            {
                "invoice": p.invoice_number,
                "date": _iso(p.purchase_date),
                "total": _money(p.total_amount),
                "status": p.status,
            }
            for p in latest
        ],
    }


def purchases_breakdown(
    organization,
    group_by="supplier",
    limit=10,
    days=30,
    period=None,
    start_date=None,
    end_date=None,
):
    """Aggregate purchases by supplier or by product for a date window."""
    start, end = _resolve_window(
        days=days, period=period, start_date=start_date, end_date=end_date
    )
    items = PurchaseItem.objects.filter(
        purchase__organization=organization,
        purchase__purchase_date__gte=start,
        purchase__purchase_date__lte=end,
    )
    limit = int(limit or 10)
    group_by = (group_by or "supplier").strip().lower()

    if group_by in ("supplier", "suppliers"):
        grouped = {}
        for pi in items.select_related("purchase", "purchase__supplier"):
            sup = pi.purchase.supplier
            bucket = grouped.setdefault(
                sup.pk,
                {
                    "supplier": sup.name,
                    "orders": set(),
                    "units": 0,
                    "spend": 0.0,
                },
            )
            bucket["orders"].add(pi.purchase_id)
            bucket["units"] += pi.quantity
            bucket["spend"] += _money(pi.quantity * pi.unit_price)
        rows = []
        for g in sorted(grouped.values(), key=lambda g: g["spend"], reverse=True)[:limit]:
            rows.append(
                {
                    "supplier": g["supplier"],
                    "orders": len(g["orders"]),
                    "units": g["units"],
                    "spend": round(g["spend"], 2),
                }
            )
        return {
            "group_by": "supplier",
            "period_start": _iso(start),
            "period_end": _iso(end),
            "items": rows,
        }

    grouped = {}
    for pi in items.select_related("product"):
        bucket = grouped.setdefault(
            pi.product_id,
            {"product": pi.product.name, "units": 0, "spend": 0.0},
        )
        bucket["units"] += pi.quantity
        bucket["spend"] += _money(pi.quantity * pi.unit_price)
    rows = sorted(grouped.values(), key=lambda g: g["spend"], reverse=True)[:limit]
    return {
        "group_by": "product",
        "period_start": _iso(start),
        "period_end": _iso(end),
        "items": rows,
    }


# ---------------------------------------------------------------------------
# CUSTOMERS
# ---------------------------------------------------------------------------

def customers_summary(organization, limit=10):
    """Customer count, top spenders, most frequent buyers and inactive ones."""
    customers = Customer.objects.filter(organization=organization)
    limit = int(limit or 10)

    annotated = customers.annotate(
        total_spend=Sum("sales__total_amount"),
        total_sales_count=Count("sales__id"),
    )
    top = (
        annotated.filter(total_spend__isnull=False)
        .order_by("-total_spend")[:limit]
    )
    frequent = (
        annotated.filter(total_sales_count__gt=0)
        .order_by("-total_sales_count", "-total_spend")[:limit]
    )
    no_purchase_count = (
        annotated.filter(total_sales_count=0).count()
    )

    return {
        "total_customers": customers.count(),
        "customers_with_no_purchases": no_purchase_count,
        "top_customers": [
            {
                "name": f"{c.first_name} {c.last_name}".strip(),
                "phone": c.phone,
                "loyalty_points": c.loyalty_points,
                "total_spend": _money(c.total_spend),
                "purchase_count": c.total_sales_count or 0,
            }
            for c in top
        ],
        "most_frequent_buyers": [
            {
                "name": f"{c.first_name} {c.last_name}".strip(),
                "phone": c.phone,
                "purchase_count": c.total_sales_count or 0,
                "total_spend": _money(c.total_spend),
            }
            for c in frequent
        ],
    }


def customer_search(organization, query="", limit=10):
    """Find customers by name/phone/email and return purchase history."""
    customers = Customer.objects.filter(organization=organization)
    if query:
        customers = customers.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
        )
    rows = (
        customers.annotate(
            total_spend=Sum("sales__total_amount"),
            total_sales_count=Count("sales__id"),
        )
        .order_by("first_name", "last_name")[: int(limit or 10)]
    )

    items = []
    for c in rows:
        history = list(c.sales.order_by("-sale_date")[:5])
        items.append(
            {
                "name": f"{c.first_name} {c.last_name}".strip(),
                "phone": c.phone,
                "email": c.email,
                "address": c.address,
                "loyalty_points": c.loyalty_points,
                "total_spend": _money(c.total_spend),
                "purchase_count": c.total_sales_count or 0,
                "recent_purchases": [
                    {
                        "invoice": h.invoice_number,
                        "date": _iso(h.sale_date),
                        "amount": _money(h.total_amount),
                    }
                    for h in history
                ],
            }
        )
    return {"query": query, "count": len(items), "items": items}


# ---------------------------------------------------------------------------
# SUPPLIERS
# ---------------------------------------------------------------------------

def suppliers_summary(organization, limit=25):
    """Supplier count and per-supplier spending (ranked by spend)."""
    suppliers = Supplier.objects.filter(organization=organization)
    rows = (
        suppliers.annotate(
            total_spend=Sum("purchases__total_amount"),
            purchase_count=Count("purchases__id"),
        )
        .order_by("-total_spend")[: int(limit or 25)]
    )
    return {
        "total_suppliers": suppliers.count(),
        "items": [
            {
                "name": s.name,
                "contact_person": s.contact_person,
                "phone": s.phone,
                "email": s.email,
                "is_active": s.is_active,
                "total_spend": _money(s.total_spend),
                "purchase_count": s.purchase_count or 0,
            }
            for s in rows
        ],
    }


def supplier_search(organization, query="", limit=10):
    """Find suppliers by name/phone/contact and their purchase history."""
    suppliers = Supplier.objects.filter(organization=organization)
    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
            | Q(contact_person__icontains=query)
        )
    rows = (
        suppliers.annotate(
            total_spend=Sum("purchases__total_amount"),
            purchase_count=Count("purchases__id"),
        )
        .order_by("name")[: int(limit or 10)]
    )

    items = []
    for s in rows:
        history = list(s.purchases.order_by("-purchase_date")[:3])
        supplied = (
            PurchaseItem.objects.filter(
                purchase__supplier=s,
                purchase__organization=organization,
            )
            .values("product__name")
            .annotate(total_qty=Sum("quantity"))
            .order_by("-total_qty")[:10]
        )
        items.append(
            {
                "name": s.name,
                "contact_person": s.contact_person,
                "phone": s.phone,
                "email": s.email,
                "address": s.address,
                "total_spend": _money(s.total_spend),
                "purchase_count": s.purchase_count or 0,
                "recent_purchases": [
                    {
                        "invoice": p.invoice_number,
                        "date": _iso(p.purchase_date),
                        "amount": _money(p.total_amount),
                    }
                    for p in history
                ],
                "products_supplied": [
                    {
                        "product": r["product__name"],
                        "quantity": r["total_qty"],
                    }
                    for r in supplied
                ],
            }
        )
    return {"query": query, "count": len(items), "items": items}


# ---------------------------------------------------------------------------
# CATEGORIES
# ---------------------------------------------------------------------------

def categories_summary(organization):
    """Per-category: product count, stock, inventory value and sales."""
    categories = list(Category.objects.filter(organization=organization))
    uncategorized = list(
        Product.objects.filter(
            organization=organization, category__isnull=True
        )
    )

    def _category_stats(prod_ids):
        stock = Inventory.objects.filter(
            organization=organization, product__in=prod_ids
        ).aggregate(
            units=Sum("quantity"),
            value=Sum(
                F("quantity") * F("product__buying_price"),
                output_field=_DECIMAL,
            ),
        )
        sold = SaleItem.objects.filter(
            product__in=prod_ids,
            sale__organization=organization,
        ).aggregate(
            units=Sum("quantity"),
            revenue=Sum(
                F("quantity") * F("unit_price"),
                output_field=_DECIMAL,
            ),
        )
        return stock, sold

    rows = []
    for cat in categories:
        prod_ids = list(cat.products.filter(organization=organization).values_list("id", flat=True))
        stock, sold = _category_stats(prod_ids)
        rows.append(
            {
                "name": cat.name,
                "product_count": len(prod_ids),
                "units_in_stock": _num(stock["units"]) or 0,
                "inventory_value": _money(stock["value"]),
                "units_sold": _num(sold["units"]) or 0,
                "sales_revenue": _money(sold["revenue"]),
            }
        )

    if uncategorized:
        prod_ids = [p.pk for p in uncategorized]
        stock, sold = _category_stats(prod_ids)
        rows.append(
            {
                "name": "Uncategorized",
                "product_count": len(prod_ids),
                "units_in_stock": _num(stock["units"]) or 0,
                "inventory_value": _money(stock["value"]),
                "units_sold": _num(sold["units"]) or 0,
                "sales_revenue": _money(sold["revenue"]),
            }
        )

    rows.sort(key=lambda r: r["sales_revenue"], reverse=True)
    return {"categories": rows}


# ---------------------------------------------------------------------------
# BUSINESS ANALYSIS
# ---------------------------------------------------------------------------

def dashboard_metrics(organization):
    """Overall current business metrics (quick status)."""
    inv = Inventory.objects.filter(organization=organization)
    products = Product.objects.filter(organization=organization)
    sales = Sale.objects.filter(organization=organization)
    purchases = Purchase.objects.filter(organization=organization)

    return {
        "product_count": products.count(),
        "stock_units": inv.aggregate(total=Sum("quantity"))["total"] or 0,
        "stock_value": _money(
            inv.aggregate(
                value=Sum(
                    F("quantity") * F("product__buying_price"),
                    output_field=_DECIMAL,
                )
            )["value"]
        ),
        "low_stock_count": inv.filter(quantity__lte=F("minimum_stock")).count(),
        "out_of_stock_count": inv.filter(quantity=0).count(),
        "sales_count": sales.count(),
        "sales_revenue": _money(
            sales.aggregate(total=Sum("total_amount"))["total"]
        ),
        "purchases_count": purchases.count(),
        "purchase_spend": _money(
            purchases.aggregate(total=Sum("total_amount"))["total"]
        ),
        "products_with_no_sales": products.filter(
            saleitem__isnull=True
        ).distinct().count(),
        "customer_count": Customer.objects.filter(
            organization=organization
        ).count(),
        "supplier_count": Supplier.objects.filter(
            organization=organization
        ).count(),
    }


def _attention_low_stock(organization, limit):
    rows = (
        Inventory.objects.filter(
            organization=organization,
            quantity__lte=F("minimum_stock"),
        )
        .select_related("product")
        .order_by("quantity")[: int(limit or 5)]
    )
    return [
        {
            "name": inv.product.name,
            "sku": inv.product.sku,
            "quantity": inv.quantity,
            "minimum_stock": inv.minimum_stock,
            "to_reorder": inv.minimum_stock - inv.quantity,
        }
        for inv in rows
    ]


def _attention_out_of_stock(organization, limit):
    rows = (
        Inventory.objects.filter(organization=organization, quantity=0)
        .select_related("product")
        .order_by("product__name")[: int(limit or 5)]
    )
    return [
        {
            "name": inv.product.name,
            "sku": inv.product.sku,
            "to_reorder": max(inv.minimum_stock - inv.quantity, 0),
        }
        for inv in rows
    ]


def _products_with_no_sales(organization, limit):
    rows = (
        Product.objects.filter(organization=organization, saleitem__isnull=True)
        .distinct()
        .order_by("name")[: int(limit or 5)]
    )
    return [{"name": p.name, "sku": p.sku} for p in rows]


def business_attention(organization, limit=5):
    """Everything needing attention: stock and sales signals."""
    low = _attention_low_stock(organization, limit)
    out = _attention_out_of_stock(organization, limit)
    no_sales = _products_with_no_sales(organization, limit)
    top = products_ranking(organization, "units_sold", "desc", limit)["items"]
    worst = products_ranking(organization, "units_sold", "asc", limit)["items"]
    restock = [
        {"name": r["name"], "sku": r["sku"], "to_reorder": r["to_reorder"]}
        for r in low + out
    ]
    return {
        "out_of_stock": out,
        "low_stock": low,
        "restock_priority": restock,
        "top_selling_products": top,
        "worst_selling_products": worst,
        "products_with_no_sales": no_sales,
        "product_count": Product.objects.filter(
            organization=organization
        ).count(),
    }


def _top_sellers_period(organization, start, end, limit):
    grouped = {}
    items = SaleItem.objects.filter(
        sale__organization=organization,
        sale__sale_date__gte=start,
        sale__sale_date__lte=end,
    ).select_related("product")
    for si in items:
        bucket = grouped.setdefault(
            si.product_id, {"name": si.product.name, "units": 0, "revenue": 0.0}
        )
        bucket["units"] += si.quantity
        bucket["revenue"] += _money(si.quantity * si.unit_price)
    return sorted(grouped.values(), key=lambda g: g["units"], reverse=True)[:limit]


def _top_customer_period(organization, start, end):
    grouped = {}
    sales = Sale.objects.filter(
        organization=organization,
        sale_date__gte=start,
        sale_date__lte=end,
        customer__isnull=False,
    ).select_related("customer")
    for s in sales:
        name = f"{s.customer.first_name} {s.customer.last_name}".strip()
        bucket = grouped.setdefault(
            s.customer_id, {"name": name, "revenue": 0.0, "sales": 0}
        )
        bucket["revenue"] += _money(s.total_amount)
        bucket["sales"] += 1
    if not grouped:
        return None
    return max(grouped.values(), key=lambda g: g["revenue"])


def _top_supplier_period(organization, start, end):
    grouped = {}
    rows = Purchase.objects.filter(
        organization=organization,
        purchase_date__gte=start,
        purchase_date__lte=end,
    ).select_related("supplier")
    for p in rows:
        bucket = grouped.setdefault(
            p.supplier_id, {"name": p.supplier.name, "spend": 0.0, "orders": 0}
        )
        bucket["spend"] += _money(p.total_amount)
        bucket["orders"] += 1
    if not grouped:
        return None
    return max(grouped.values(), key=lambda g: g["spend"])


def business_summary(
    organization,
    days=90,
    period=None,
    start_date=None,
    end_date=None,
):
    """Concise overall business snapshot answering 'how is my business?'"""
    start, end = _resolve_window(
        days=days, period=period, start_date=start_date, end_date=end_date
    )
    sales = Sale.objects.filter(
        organization=organization,
        sale_date__gte=start,
        sale_date__lte=end,
    )
    purchases = Purchase.objects.filter(
        organization=organization,
        purchase_date__gte=start,
        purchase_date__lte=end,
    )
    sagg = sales.aggregate(total=Sum("total_amount"), count=Count("id"))
    pagg = purchases.aggregate(total=Sum("total_amount"), count=Count("id"))
    revenue = _money(sagg["total"])
    spend = _money(pagg["total"])
    sale_count = sagg["count"] or 0

    top_seller = _top_sellers_period(organization, start, end, 1)
    return {
        "period_start": _iso(start),
        "period_end": _iso(end),
        "revenue": revenue,
        "purchase_spend": spend,
        "net": round(revenue - spend, 2),
        "sales_count": sale_count,
        "purchase_count": pagg["count"] or 0,
        "average_sale_value": round(revenue / sale_count, 2) if sale_count else 0.0,
        "top_selling_product": top_seller[0] if top_seller else None,
        "top_customer": _top_customer_period(organization, start, end),
        "top_supplier": _top_supplier_period(organization, start, end),
        "low_stock_count": Inventory.objects.filter(
            organization=organization,
            quantity__lte=F("minimum_stock"),
        ).count(),
        "out_of_stock_count": Inventory.objects.filter(
            organization=organization, quantity=0
        ).count(),
        "product_count": Product.objects.filter(
            organization=organization
        ).count(),
        "customer_count": Customer.objects.filter(
            organization=organization
        ).count(),
    }


# ---------------------------------------------------------------------------
# Tool metadata (name -> callable) and Groq function declarations.
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {
    "inventory_summary": inventory_summary,
    "low_stock_products": low_stock_products,
    "out_of_stock_products": out_of_stock_products,
    "product_search": product_search,
    "products_ranking": products_ranking,
    "sales_summary": sales_summary,
    "sales_breakdown": sales_breakdown,
    "sales_trend": sales_trend,
    "purchases_summary": purchases_summary,
    "purchases_breakdown": purchases_breakdown,
    "stock_movements": stock_movements,
    "customers_summary": customers_summary,
    "customer_search": customer_search,
    "suppliers_summary": suppliers_summary,
    "supplier_search": supplier_search,
    "categories_summary": categories_summary,
    "dashboard_metrics": dashboard_metrics,
    "business_attention": business_attention,
    "business_summary": business_summary,
}


def _int_prop(description, default=None):
    prop = {"type": "integer", "description": description}
    if default is not None:
        prop["default"] = default
    return prop


def _str_prop(description, default=None):
    prop = {"type": "string", "description": description}
    if default is not None:
        prop["default"] = default
    return prop


def _date_prop(description="Explicit date (YYYY-MM-DD)."):
    return _str_prop(description)


def _window_prop(default="last_30_days"):
    return _str_prop(
        "Date window label: today, yesterday, this_week, last_week, "
        "this_month, last_month, last_7_days, last_30_days, this_year, "
        "last_year, or all.",
        default=default,
    )


def _decl(name, description, properties):
    return {
        "name": name,
        "description": description,
        "parameters": {"type": "object", "properties": properties},
    }


NPR_HINT = "All monetary values are in Nepalese Rupees (NPR), shown as Rs.."


TOOL_DECLARATIONS = [
    _decl(
        "dashboard_metrics",
        "Overall current business metrics: product/stock/sale/purchase/"
        f"customer/supplier counts, low/out-of-stock counts, total stock "
        f"value and products with no sales. {NPR_HINT}",
        {},
    ),
    _decl(
        "product_search",
        "Search products by name, SKU or barcode; optionally by exact "
        f"category name. Returns price, current stock and units sold. {NPR_HINT}",
        {
            "query": _str_prop("Text to match against product name/SKU/barcode."),
            "category": _str_prop("Exact category name to filter by."),
            "limit": _int_prop("Maximum results.", default=10),
        },
    ),
    _decl(
        "products_ranking",
        "Rank products by a metric: selling_price or buying_price (most/least "
        "expensive), stock (highest/lowest), units_sold or sales_revenue "
        "(most/least sold, top sellers), margin, recent (newest) or name. "
        f"Use order='desc' or 'asc'. {NPR_HINT}",
        {
            "metric": _str_prop(
                "selling_price, buying_price, stock, units_sold, "
                "sales_revenue, sales_count, margin, recent, or name.",
                default="units_sold",
            ),
            "order": _str_prop("Order: 'desc' (default) or 'asc'.", default="desc"),
            "limit": _int_prop("Maximum products.", default=10),
        },
    ),
    _decl(
        "inventory_summary",
        "Current stock levels: per-product quantity, thresholds, status and "
        f"value, plus total units and total stock value. {NPR_HINT}",
        {"limit": _int_prop("Maximum products.", default=25)},
    ),
    _decl(
        "low_stock_products",
        "Products at or below their minimum stock level (need reorder), "
        "including how many units to reorder.",
        {"limit": _int_prop("Maximum products.", default=10)},
    ),
    _decl(
        "out_of_stock_products",
        "Products currently out of stock (quantity zero).",
        {"limit": _int_prop("Maximum products.", default=10)},
    ),
    _decl(
        "stock_movements",
        "Recent stock movements (IN, OUT, ADJUSTMENT), optionally filtered by "
        "movement type and date range. Returns latest entries with totals and "
        "net stock change. Useful for restocking history and stock increases/"
        "decreases.",
        {
            "movement_type": _str_prop("Filter by IN, OUT or ADJUSTMENT."),
            "start_date": _date_prop("Filter movement dates from (YYYY-MM-DD)."),
            "end_date": _date_prop("Filter movement dates to (YYYY-MM-DD)."),
            "limit": _int_prop("Maximum entries.", default=20),
        },
    ),
    _decl(
        "sales_summary",
        "Sales summary for a date window: number of sales, total revenue, "
        "average sale value, highest and lowest sale, and recent invoices. "
        f"Supports today/this_month/last_30_days/date ranges. {NPR_HINT}",
        {
            "period": _window_prop("last_30_days"),
            "start_date": _date_prop("Explicit range start (YYYY-MM-DD)."),
            "end_date": _date_prop("Explicit range end (YYYY-MM-DD)."),
            "days": _int_prop("Fallback look-back days when no window given.", default=30),
        },
    ),
    _decl(
        "sales_breakdown",
        "Sales grouped by product or by customer for a date window "
        f"(units and revenue per group). {NPR_HINT}",
        {
            "group_by": _str_prop("Group by 'product' or 'customer'.", default="product"),
            "period": _window_prop("last_30_days"),
            "start_date": _date_prop("Explicit range start (YYYY-MM-DD)."),
            "end_date": _date_prop("Explicit range end (YYYY-MM-DD)."),
            "limit": _int_prop("Maximum groups.", default=10),
        },
    ),
    _decl(
        "sales_trend",
        "Sales over time bucketed by day, week or month. Use for sales "
        f"trends across a date window. {NPR_HINT}",
        {
            "bucket": _str_prop("'day', 'week' or 'month'.", default="month"),
            "period": _window_prop("last_90_days"),
            "start_date": _date_prop("Explicit range start (YYYY-MM-DD)."),
            "end_date": _date_prop("Explicit range end (YYYY-MM-DD)."),
        },
    ),
    _decl(
        "purchases_summary",
        "Purchase/spending summary for a date window: count, total spend, "
        "average purchase, highest and lowest purchase, recent purchases. "
        f"Supports period/date-range filters. {NPR_HINT}",
        {
            "period": _window_prop("last_30_days"),
            "start_date": _date_prop("Explicit range start (YYYY-MM-DD)."),
            "end_date": _date_prop("Explicit range end (YYYY-MM-DD)."),
            "days": _int_prop("Fallback look-back days.", default=30),
        },
    ),
    _decl(
        "purchases_breakdown",
        "Purchases grouped by supplier (who we spend the most with) or by "
        f"product (most purchased items). {NPR_HINT}",
        {
            "group_by": _str_prop("Group by 'supplier' or 'product'.", default="supplier"),
            "period": _window_prop("last_30_days"),
            "start_date": _date_prop("Explicit range start (YYYY-MM-DD)."),
            "end_date": _date_prop("Explicit range end (YYYY-MM-DD)."),
            "limit": _int_prop("Maximum groups.", default=10),
        },
    ),
    _decl(
        "customers_summary",
        "Customer counts, top customers by total spending, most frequent "
        "buyers, and how many customers have no purchases. {NPR_HINT}",
        {"limit": _int_prop("Maximum customers.", default=10)},
    ),
    _decl(
        "customer_search",
        "Find customers by name, phone or email and return their purchase "
        f"history (recent invoices). {NPR_HINT}",
        {
            "query": _str_prop("Text to search (name/phone/email)."),
            "limit": _int_prop("Maximum results.", default=5),
        },
    ),
    _decl(
        "suppliers_summary",
        "Supplier count and per-supplier spending ranked by total spend. "
        f"Finds the supplier you spend the most with. {NPR_HINT}",
        {"limit": _int_prop("Maximum suppliers.", default=10)},
    ),
    _decl(
        "supplier_search",
        "Find suppliers by name/phone/contact and see purchase history plus "
        f"the products they supply. {NPR_HINT}",
        {
            "query": _str_prop("Text to search (name/phone/contact)."),
            "limit": _int_prop("Maximum results.", default=5),
        },
    ),
    _decl(
        "categories_summary",
        "Per-category performance: product count, units in stock, inventory "
        f"value, units sold and sales revenue. Best/worst categories. {NPR_HINT}",
        {},
    ),
    _decl(
        "business_attention",
        "Everything that needs attention right now: out-of-stock and "
        "low-stock items with restock priorities, top-selling and "
        "worst-selling products, and products with no sales yet. {NPR_HINT}",
        {"limit": _int_prop("Maximum items per list.", default=5)},
    ),
    _decl(
        "business_summary",
        "Concise overall business snapshot for a window: revenue, purchase "
        "spend, net, counts, top product/customer/supplier, average sale "
        f"value and stock alerts. {NPR_HINT}",
        {
            "period": _window_prop("last_90_days"),
            "start_date": _date_prop("Explicit range start (YYYY-MM-DD)."),
            "end_date": _date_prop("Explicit range end (YYYY-MM-DD)."),
        },
    ),
]


def dispatch_tool(name, organization, args):
    """
    Execute a single controlled tool on behalf of the model.

    ``organization`` is always injected by the backend; it is never taken
    from model-supplied arguments, so cross-tenant access is impossible.
    """
    func = TOOL_REGISTRY.get(name)
    if func is None:
        return {"error": f"Unknown tool: {name}"}

    call_args = dict(args or {})
    call_args["organization"] = organization

    try:
        result = func(**call_args)
    except TypeError:
        # Model supplied invalid parameters; retry with defaults only.
        result = func(organization)
    except Exception as exc:  # noqa: BLE001 - surfaced to the model safely
        result = {"error": f"Tool {name} failed: {type(exc).__name__}"}

    return {"tool": name, "result": result}