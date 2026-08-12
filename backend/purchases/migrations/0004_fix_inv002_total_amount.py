from decimal import Decimal

from django.db import migrations


def fix_inv002_total(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    Purchase = apps.get_model("purchases", "Purchase")

    org = Organization.objects.filter(code="B1").first()
    if org is None:
        return

    purchase = Purchase.objects.filter(organization=org, invoice_number="INV-002").first()
    if purchase is None:
        return

    if purchase.total_amount != Decimal("210.00"):
        purchase.total_amount = Decimal("210.00")
        purchase.save(update_fields=["total_amount", "updated_at"])


def restore_inv002_total(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    Purchase = apps.get_model("purchases", "Purchase")

    org = Organization.objects.filter(code="B1").first()
    if org is None:
        return

    purchase = Purchase.objects.filter(organization=org, invoice_number="INV-002").first()
    if purchase is None:
        return

    purchase.total_amount = Decimal("0.00")
    purchase.save(update_fields=["total_amount", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("purchases", "0003_alter_purchaseitem_options"),
    ]

    operations = [
        migrations.RunPython(fix_inv002_total, restore_inv002_total),
    ]
