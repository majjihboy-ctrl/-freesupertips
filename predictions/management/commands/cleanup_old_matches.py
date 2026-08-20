from django.core.management.base import BaseCommand
from django.utils import timezone

from predictions.models import Match


class Command(BaseCommand):
    help = (
        "Delete matches whose kickoff date has fully passed (before local "
        "midnight, per TIME_ZONE). Predictions for those matches are removed "
        "automatically via cascade delete."
    )

    def handle(self, *args, **options):
        # timezone.localtime() converts "now" into settings.TIME_ZONE before
        # truncating to midnight, so "today" lines up with the actual local
        # calendar day (e.g. Africa/Nairobi) rather than UTC's.
        today_start = timezone.localtime().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        old_matches = Match.objects.filter(kickoff__lt=today_start)
        count = old_matches.count()
        old_matches.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} match(es) with kickoff before {today_start.date()}."
            )
        )
