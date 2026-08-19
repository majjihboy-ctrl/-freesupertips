"""
Seeds predictions.Team from every _teams_data_batchN.py module found next
to this command. Each batch module just needs to define a TEAMS dict:

    TEAMS = {
        ("Country", "League Name"): ["Team One", "Team Two", ...],
        ...
    }

Add more batches over time as separate _teams_data_batchN.py files - this
command auto-discovers and merges all of them, so you never edit this file
itself to add data.

Usage:
    python manage.py seed_teams --dry-run   # preview
    python manage.py seed_teams             # create missing teams

Team.short_name (max 10 chars) is auto-derived from the team name since we
don't hand-author one per team. Fix any you don't like afterwards in
/admin/ - it's a free-text field there.
"""

import importlib
import pkgutil
import re

from django.core.management.base import BaseCommand, CommandError
from predictions.models import League, Team

_SUFFIXES = (
    " Football Club", " FC", " CF", " AFC", " SC", " CD", " UD", " SAD",
)


def _derive_short_name(name: str) -> str:
    cleaned = name
    for suf in _SUFFIXES:
        if cleaned.endswith(suf):
            cleaned = cleaned[: -len(suf)]
            break
    cleaned = re.sub(r"[^A-Za-z0-9 ]", "", cleaned).strip()
    return cleaned[:10] if cleaned else name[:10]


def _discover_batches():
    """Import every sibling module named _teams_data_batch*.py and yield
    its TEAMS dict. Skips (with a warning, not a crash) any module that
    fails to import or has no TEAMS attribute."""
    package = "predictions.management.commands"
    pkg = importlib.import_module(package)
    for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
        if not module_name.startswith("_teams_data_batch"):
            continue
        module = importlib.import_module(f"{package}.{module_name}")
        teams = getattr(module, "TEAMS", None)
        if teams is None:
            continue
        yield module_name, teams


class Command(BaseCommand):
    help = "Seed Team rows from all _teams_data_batchN.py modules found alongside this command."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        batches = list(_discover_batches())
        if not batches:
            raise CommandError(
                "No _teams_data_batchN.py modules found. Add one (see this "
                "command's docstring for the format) and re-run."
            )

        created, skipped, missing_leagues = 0, 0, []

        for module_name, teams in batches:
            self.stdout.write(f"--- {module_name} ---")
            for (country, league_name), team_names in teams.items():
                league = League.objects.filter(
                    country=country, name__iexact=league_name
                ).first()
                if not league:
                    missing_leagues.append(f"{league_name} ({country})")
                    continue

                for team_name in team_names:
                    exists = Team.objects.filter(
                        league=league, name__iexact=team_name
                    ).exists()
                    if exists:
                        skipped += 1
                        continue

                    if dry_run:
                        self.stdout.write(f"Would create: {team_name} [{league}]")
                        created += 1
                        continue

                    Team.objects.create(
                        name=team_name,
                        short_name=_derive_short_name(team_name),
                        league=league,
                    )
                    created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created}, already present: {skipped}."
        ))
        if missing_leagues:
            self.stdout.write(self.style.WARNING(
                "These leagues weren't found in the DB (run seed_leagues "
                "first, or check spelling matches exactly): "
                + ", ".join(sorted(set(missing_leagues)))
            ))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run - no changes were written."))