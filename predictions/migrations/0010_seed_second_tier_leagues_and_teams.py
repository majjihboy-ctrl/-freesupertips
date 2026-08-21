from django.db import migrations

# Current (2026-27) rosters for a second tier of popular domestic leagues.
# Two notes on incompleteness, both flagged rather than guessed:
# - Eredivisie: 17 of 18 teams confirmed; the 18th promotion/play-off spot
#   was not yet resolved in available sources at the time this was written.
# - Belgian Pro League: the league's format/size for this season is itself
#   still disputed (ongoing procedures could keep it at 16 teams or expand
#   to 18) -- 16 confirmed teams seeded, expansion slots deliberately
#   left out rather than guessed.
LEAGUES = {
    "Eredivisie": {
        "country": "Netherlands",
        "teams": [
            ("PSV Eindhoven", "PSV", "#ED1C24"),
            ("Ajax", "AJA", "#D2122E"),
            ("Feyenoord", "FEY", "#ED1C24"),
            ("AZ Alkmaar", "AZ", "#DC143C"),
            ("FC Twente", "TWE", "#ED1B34"),
            ("Go Ahead Eagles", "GAE", "#FFCC00"),
            ("FC Utrecht", "UTR", "#C7202E"),
            ("NEC Nijmegen", "NEC", "#FF0000"),
            ("Sparta Rotterdam", "SPA", "#C8102E"),
            ("Fortuna Sittard", "FOR", "#FFD200"),
            ("Heerenveen", "HEE", "#0033A0"),
            ("PEC Zwolle", "PEC", "#0072BC"),
            ("Groningen", "GRO", "#00A651"),
            ("Excelsior", "EXC", "#FDB913"),
            ("Telstar", "TEL", "#FF6600"),
            ("ADO Den Haag", "ADO", "#FFD200"),
            ("Cambuur", "CAM", "#002D62"),
        ],
    },
    "Primeira Liga": {
        "country": "Portugal",
        "teams": [
            ("Porto", "POR", "#0033A0"),
            ("Sporting CP", "SCP", "#007A33"),
            ("Benfica", "BEN", "#E30613"),
            ("Braga", "BRA", "#DC0000"),
            ("Vitoria Guimaraes", "VIT", "#7A7A7A"),
            ("Gil Vicente", "GIL", "#FF0000"),
            ("Santa Clara", "SCL", "#00A651"),
            ("Moreirense", "MOR", "#00843D"),
            ("Famalicao", "FAM", "#7A7A7A"),
            ("Arouca", "ARO", "#FFD200"),
            ("Rio Ave", "RIO", "#00A99D"),
            ("Casa Pia", "CPI", "#7CB342"),
            ("Nacional", "NAC", "#000000"),
            ("Estoril", "EST", "#FFD200"),
            ("Estrela da Amadora", "EAM", "#006633"),
            ("Alverca", "ALV", "#C8102E"),
            ("Maritimo", "MAR", "#009846"),
            ("Academico de Viseu", "AVI", "#FFD200"),
        ],
    },
    "Belgian Pro League": {
        "country": "Belgium",
        "teams": [
            ("Club Brugge", "CLU", "#0060AB"),
            ("Union SG", "USG", "#6DAADA"),
            ("Anderlecht", "AND", "#7B1E3A"),
            ("Genk", "KRC", "#005CA9"),
            ("Gent", "GNT", "#003B7A"),
            ("Standard Liege", "STA", "#C8102E"),
            ("Antwerp", "ANT", "#E2001A"),
            ("Cercle Brugge", "CER", "#00A651"),
            ("KV Mechelen", "MEC", "#FFD200"),
            ("Sint-Truiden", "STV", "#FFD200"),
            ("Westerlo", "WES", "#FFD200"),
            ("OH Leuven", "OHL", "#FFD200"),
            ("Charleroi", "CHA", "#000080"),
            ("La Louviere", "LLV", "#00843D"),
            ("Zulte Waregem", "ZUL", "#FFD200"),
            ("Beveren", "BEV", "#FFD200"),
        ],
    },
    "Scottish Premiership": {
        "country": "Scotland",
        "teams": [
            ("Celtic", "CEL", "#018749"),
            ("Rangers", "RAN", "#1D3E7C"),
            ("Aberdeen", "ABE", "#D71920"),
            ("Heart of Midlothian", "HEA", "#7C0A02"),
            ("Hibernian", "HIB", "#00954C"),
            ("Dundee United", "DUT", "#FF6600"),
            ("Dundee", "DUN", "#001E62"),
            ("Motherwell", "MOT", "#FFD200"),
            ("Kilmarnock", "KIL", "#0033A0"),
            ("St Mirren", "STM", "#000000"),
            ("St Johnstone", "STJ", "#002D62"),
            ("Falkirk", "FAL", "#002D62"),
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
        ("predictions", "0009_seed_top_leagues_and_teams"),
    ]

    operations = [
        migrations.RunPython(seed_leagues_and_teams, noop_reverse),
    ]
