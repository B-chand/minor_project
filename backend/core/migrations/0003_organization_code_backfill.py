from django.db import migrations


def assign_business_codes(apps, schema_editor):
    """
    Safely backfill a unique Business Code (``B<n>``) for every existing
    organization that does not have one yet.

    This is a pure additive operation: no organization or user data is
    deleted or modified other than recording each organization's code.
    """

    Organization = apps.get_model("core", "Organization")

    prefix = "B"
    max_number = 0

    for code in (
        Organization.objects.exclude(code__isnull=True)
        .exclude(code="")
        .values_list("code", flat=True)
    ):
        suffix = code[len(prefix):] if code.startswith(prefix) else ""
        if suffix.isdigit():
            max_number = max(int(suffix), max_number)

    organizations = (
        Organization.objects
        .filter(code__isnull=True)
        .order_by("created_at", "id")
    )

    for organization in organizations:
        max_number += 1
        organization.code = f"{prefix}{max_number}"
        organization.save(update_fields=["code"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_organization_code"),
    ]

    operations = [
        migrations.RunPython(
            assign_business_codes,
            migrations.RunPython.noop,
        ),
    ]