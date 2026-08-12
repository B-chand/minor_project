from decimal import Decimal

from django.db import migrations


def _computed_status(amount_paid, total_amount):
    """Authoritative Phase 18 payment status rules (single source of truth)."""
    paid = amount_paid if amount_paid is not None else Decimal("0.00")
    total = total_amount if total_amount is not None else Decimal("0.00")

    if paid <= Decimal("0.00"):
        return "UNPAID"

    if paid < total:
        return "PARTIAL"

    return "PAID"


def sync_payment_status(apps, schema_editor):
    """
    Synchronize stored Sale.payment_status with the authoritative rules.

    Only the stored `payment_status` label is updated. Financial values
    (amount_paid, total_amount) are untouched, no rows are deleted, and
    no related models are modified. `query.update()` is used instead of
    `model.save()` so no model-level logic or signals can run.
    """
    Sale = apps.get_model("sales", "Sale")

    rows = list(
        Sale.objects.all()
        .values("pk", "amount_paid", "total_amount")
    )

    counts = {"PAID": 0, "PARTIAL": 0, "UNPAID": 0}

    for row in rows:
        status = _computed_status(row["amount_paid"], row["total_amount"])
        counts[status] += 1
        Sale.objects.filter(pk=row["pk"]).update(payment_status=status)

    print(
        "\nSales payment-status sync: "
        f"{len(rows)} rows | "
        f"PAID={counts['PAID']} "
        f"PARTIAL={counts['PARTIAL']} "
        f"UNPAID={counts['UNPAID']}"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0003_sale_amount_paid_alter_sale_payment_status"),
    ]

    operations = [
        migrations.RunPython(sync_payment_status, migrations.RunPython.noop),
    ]