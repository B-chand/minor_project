from django.core.management.base import BaseCommand
from django.db.models import Q

from core.models import Organization
from ai.services.insights import persist_generated_insights


class Command(BaseCommand):
    help = (
        "Generate missing AI insights for each organization from live "
        "business data. Existing insights (manually created or "
        "demo-seeded) are never deleted or overwritten; only missing "
        "insights are added, so the command is safe to run repeatedly."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--orgs",
            nargs="*",
            dest="orgs",
            default=None,
            help="Limit to organization ids or names (space separated).",
        )

    def handle(self, *args, **options):
        orgs = Organization.objects.all().order_by("name")

        selectors = options.get("orgs")
        if selectors:
            query = Q()
            for selector in selectors:
                if selector.isdigit():
                    query |= Q(pk=selector)
                else:
                    query |= Q(name__iexact=selector)
            orgs = orgs.filter(query)

        total_created = 0
        for org in orgs:
            result = persist_generated_insights(org)
            created = result["created"]
            total_created += len(created)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{org.name}: created {len(created)}, "
                    f"skipped {len(result['skipped'])}"
                )
            )
            for title in created:
                self.stdout.write(f"   + {title}")

        self.stdout.write(
            self.style.SUCCESS(f"Done. {total_created} insight(s) created.")
        )
