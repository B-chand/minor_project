from django.db import migrations


def fix_cross_tenant_category(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    Product = apps.get_model("inventory", "Product")
    Category = apps.get_model("inventory", "Category")

    org = Organization.objects.filter(code="B1").first()
    if org is None:
        return

    product = Product.objects.filter(organization=org, sku="SKU-234822").first()
    if product is None:
        return

    if product.category is not None and product.category.organization_id != org.id:
        own_grocery = Category.objects.filter(organization=org, name="Grocery").first()
        if own_grocery is not None:
            product.category = own_grocery
            product.save(update_fields=["category", "updated_at"])


def restore_cross_tenant_category(apps, schema_editor):
    Product = apps.get_model("inventory", "Product")
    Category = apps.get_model("inventory", "Category")

    original = Category.objects.filter(pk=93).first()
    if original is None:
        return

    product = Product.objects.filter(sku="SKU-234822").first()
    if product is None:
        return

    product.category = original
    product.save(update_fields=["category", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_alter_product_category_alter_product_sku_and_more"),
    ]

    operations = [
        migrations.RunPython(fix_cross_tenant_category, restore_cross_tenant_category),
    ]
