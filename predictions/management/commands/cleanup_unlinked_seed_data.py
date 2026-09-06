from django.core.management.base import BaseCommand
from django.db import transaction

from predictions.models import League, Team


class Command(BaseCommand):
    help = (
        "Deletes hand-seeded League/Team rows (from seed_leagues/seed_teams) "
        "that were never linked to a real fixture from the Bzzoiro import "
        "and have zero matches attached. Rows with any match attached are "
        "never touched, even if unlinked -- this is a safety guarantee, not "
        "a default that can be overridden by a flag. Run with --dry-run "
        "first to see what would be removed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report what would be deleted without deleting anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        stale_leagues = League.objects.filter(external_id__isnull=True, matches__isnull=True).distinct()
        stale_teams = Team.objects.filter(
            external_id__isnull=True, home_matches__isnull=True, away_matches__isnull=True
        ).distinct()

        league_count = stale_leagues.count()
        team_count = stale_teams.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[dry run] Would delete {league_count} unused seeded league(s) "
                f"and {team_count} unused seeded team(s). No changes made."
            ))
            return

        with transaction.atomic():
            # Teams first (they FK to League) to avoid any ordering surprises,
            # though CASCADE would handle it either way since neither has matches.
            deleted_teams, _ = stale_teams.delete()
            deleted_leagues, _ = stale_leagues.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Deleted {deleted_leagues} unused seeded league(s) and "
            f"{deleted_teams} unused seeded team(s). Leagues/teams with any "
            f"real match attached were left untouched."
        ))
