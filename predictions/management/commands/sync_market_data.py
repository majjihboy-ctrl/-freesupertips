import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from predictions import market_data
from predictions import multibet_service as mbs
from predictions.models import Match


class Command(BaseCommand):
    help = (
        "Fetch per-match market data from the Bzzoiro API: final corner counts "
        "(so corner multibets can be graded) and bookmaker consensus odds (so "
        "multibet legs are priced from the market). Then refresh today's "
        "multibet snapshot if no game has kicked off. Time-budgeted so it fits "
        "a serverless function."
    )

    def add_arguments(self, parser):
        parser.add_argument("--corners-budget", type=int, default=20, help="Seconds for the corners pass.")
        parser.add_argument("--odds-budget", type=int, default=25, help="Seconds for the odds pass.")

    def handle(self, *args, **options):
        api_key = getattr(settings, "BZZOIRO_API_KEY", "")
        if not api_key:
            self.stderr.write(self.style.ERROR("BZZOIRO_API_KEY is not set."))
            return

        session = requests.Session()
        session.headers.update({"Authorization": f"Token {api_key}"})

        corners = market_data.sync_corners(session, budget_seconds=options["corners_budget"])
        odds = market_data.sync_odds(session, budget_seconds=options["odds_budget"])
        self.stdout.write(self.style.SUCCESS(
            f"Corners filled for {corners} match(es); consensus odds for {odds} match(es)."
        ))

        # Re-snapshot today's multibets with the fresh prices -- only while
        # nothing has kicked off yet (the snapshot is frozen afterwards).
        try:
            today = timezone.localdate()
            day_start, _end = mbs._day_bounds(today)
            if Match.objects.filter(kickoff__gte=day_start, kickoff__lte=timezone.now()).exists():
                self.stdout.write("Multibet snapshot left as is: today's games already started.")
            else:
                for slug, _label, _market in mbs.TABS:
                    mbs.get_multibets(today, slug)
                self.stdout.write("Multibets re-snapshotted with market prices.")
        except Exception as exc:  # never fail the sync because of this
            self.stdout.write(self.style.WARNING(f"Multibet snapshot skipped: {exc}"))
