from django.db import migrations

# Third batch of popular leagues, continuing where 0009/0010 left off.
# Brazilian Serie A note: the 20 teams below reflect the confirmed 2025
# season lineup. The exact 2025->2026 promotion/relegation swap wasn't
# confirmed in available sources at time of writing, so 2-3 of these may
# need a manual swap once that's settled -- easy to fix via /admin/.
LEAGUES = {
    "MLS": {
        "country": "United States/Canada",
        "teams": [
            ("Atlanta United", "ATL", "#80000A"),
            ("Austin FC", "ATX", "#00B140"),
            ("CF Montreal", "MTL", "#000080"),
            ("Charlotte FC", "CLT", "#1A85C8"),
            ("Chicago Fire", "CHI", "#A80D2A"),
            ("Colorado Rapids", "COL", "#960A2D"),
            ("Columbus Crew", "CLB", "#FEDD00"),
            ("D.C. United", "DCU", "#000000"),
            ("FC Cincinnati", "CIN", "#FF6B00"),
            ("FC Dallas", "DAL", "#C0102D"),
            ("Houston Dynamo", "HOU", "#F68712"),
            ("Inter Miami", "MIA", "#F7B5CD"),
            ("LA Galaxy", "LAG", "#00245D"),
            ("Los Angeles FC", "LAFC", "#C39E6D"),
            ("Minnesota United", "MIN", "#8CDBFF"),
            ("Nashville SC", "NSH", "#ECE83A"),
            ("New England Revolution", "NER", "#0A2240"),
            ("New York City FC", "NYC", "#6CACE4"),
            ("New York Red Bulls", "NYRB", "#ED1E36"),
            ("Orlando City", "ORL", "#633492"),
            ("Philadelphia Union", "PHI", "#B19257"),
            ("Portland Timbers", "POR", "#004812"),
            ("Real Salt Lake", "RSL", "#B30838"),
            ("San Diego FC", "SD", "#4A2E83"),
            ("San Jose Earthquakes", "SJ", "#000000"),
            ("Seattle Sounders", "SEA", "#5D9741"),
            ("Sporting Kansas City", "SKC", "#93B1D7"),
            ("St. Louis City", "STL", "#DA291C"),
            ("Toronto FC", "TOR", "#B81137"),
            ("Vancouver Whitecaps", "VAN", "#00245E"),
        ],
    },
    "Brazilian Serie A": {
        "country": "Brazil",
        "teams": [
            ("Flamengo", "FLA", "#E31937"),
            ("Palmeiras", "PAL", "#006437"),
            ("Botafogo", "BOT", "#000000"),
            ("Sao Paulo", "SAO", "#FE0000"),
            ("Corinthians", "COR", "#000000"),
            ("Internacional", "INT", "#E30613"),
            ("Gremio", "GRE", "#0093D0"),
            ("Fluminense", "FLU", "#7A1216"),
            ("Bahia", "BAH", "#0865B0"),
            ("Fortaleza", "FTL", "#1E3C8C"),
            ("Atletico Mineiro", "CAM", "#000000"),
            ("Cruzeiro", "CRU", "#002B7F"),
            ("Vasco da Gama", "VAS", "#000000"),
            ("Red Bull Bragantino", "RBB", "#E0001B"),
            ("Santos", "SAN", "#000000"),
            ("Ceara", "CEA", "#000000"),
            ("Mirassol", "MIR", "#FFD200"),
            ("Sport Recife", "SPT", "#B70A2A"),
            ("Juventude", "JUV", "#6DBA48"),
            ("Vitoria", "VIT", "#B7071A"),
        ],
    },
    "Saudi Pro League": {
        "country": "Saudi Arabia",
        "teams": [
            ("Al-Hilal", "HIL", "#005DAA"),
            ("Al-Nassr", "NAS", "#FCE300"),
            ("Al-Ittihad", "ITT", "#000000"),
            ("Al-Ahli", "AHL", "#007A3D"),
            ("Al-Qadsiah", "QAD", "#6A1B2E"),
            ("Al-Taawoun", "TAA", "#FFD200"),
            ("Al-Shabab", "SHB", "#8A8D8F"),
            ("Al-Ettifaq", "ETT", "#00693E"),
            ("Al-Fateh", "FAT", "#1B8A3B"),
            ("Al-Fayha", "FAY", "#F5A800"),
            ("Al-Khaleej", "KHA", "#0E6E4A"),
            ("Al-Riyadh", "RIY", "#C9A227"),
            ("Al-Kholood", "KHO", "#1E3A5F"),
            ("Al-Wehda", "WEH", "#1B4F9C"),
            ("Neom SC", "NEO", "#00B2A9"),
            ("Abha", "ABH", "#005BAA"),
            ("Al-Faisaly", "FAI", "#1D8348"),
            ("Al-Diriyah", "DIR", "#7A5C2E"),
        ],
    },
}


def seed_leagues_and_teams(apps, schema_editor):
    League = apps.get_model("predictions", "League")
    Team = apps.get_model("predictions", "Team")

    for league_name, info in LEAGUES.items():
        league, _ = League.objects.get_or_create(
            name=league_name, defaults={"country": info["country"]}
        )
        for name, short_name, crest_color in info["teams"]:
            Team.objects.get_or_create(
                name=name,
                league=league,
                defaults={"short_name": short_name, "crest_color": crest_color},
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("predictions", "0011_remove_fixed_1x2_prediction_fields"),
    ]

    operations = [
        migrations.RunPython(seed_leagues_and_teams, noop_reverse),
    ]
