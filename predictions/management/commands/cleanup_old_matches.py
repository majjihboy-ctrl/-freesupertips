from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from predictions.models import Match


class Command(BaseCommand):
    help = (
        "Delete matches older than the retention window so finished tips "
        "remain available on the Results page for accuracy tracking. "
        "Default keeps 45 days of history."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=45,
            help="Keep matches with kickoff within the last N days. Default 45.",
        )

    def handle(self, *args, **options):
        retain_days = max(7, options["days"])
        cutoff = timezone.localtime().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=retain_days)

        old_matches = Match.objects.filter(kickoff__lt=cutoff)
        count = old_matches.count()
        old_matches.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} match(es) with kickoff before {cutoff.date()} "
                f"(kept last {retain_days} days for Results history)."
            )
        )
