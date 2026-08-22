from django.db import migrations

# Fourth batch, continuing from 0009/0010/0012. Two leagues here have
# known gaps -- confirmed teams are seeded, unconfirmed slots are left
# out rather than guessed (same approach as Eredivisie/Belgian Pro
# League in 0010):
# - English Championship: 21/24 confirmed. Coventry City, Ipswich Town
#   and Hull City left this season (promoted to the Premier League --
#   see 0009), but the 3 teams relegated down from the Championship and
#   the 3 promoted up from League One for 2026-27 weren't confirmed in
#   available sources at time of writing.
# - Argentine Primera Division: the league moved to a unified 30-team
#   format. The 26 teams below are the well-established traditional
#   top-flight clubs; a handful of smaller/newer clubs in the expanded
#   format aren't included.
LEAGUES = {
    "Liga MX": {
        "country": "Mexico",
        "teams": [
            ("Club America", "AME", "#FFD200"),
            ("Atlante", "ATL", "#003DA5"),
            ("Atlas", "ATA", "#B7002C"),
            ("Atletico San Luis", "TSL", "#DA291C"),
            ("Cruz Azul", "CAZ", "#00539F"),
            ("FC Juarez", "JUA", "#00843D"),
            ("Guadalajara", "GDL", "#B7002C"),
            ("Leon", "LEO", "#00843D"),
            ("Monterrey", "MTY", "#031C63"),
            ("Necaxa", "NEC", "#B7002C"),
            ("Pachuca", "PAC", "#003DA5"),
            ("Puebla", "PUE", "#00539F"),
            ("Pumas UNAM", "PUM", "#002B5C"),
            ("Queretaro", "QRO", "#000000"),
            ("Santos Laguna", "SAN", "#00843D"),
            ("Tigres UANL", "TIG", "#F5A800"),
            ("Tijuana", "TIJ", "#B7002C"),
            ("Toluca", "TOL", "#B7002C"),
        ],
    },
    "Turkish Super Lig": {
        "country": "Turkey",
        "teams": [
            ("Galatasaray", "GS", "#A90432"),
            ("Fenerbahce", "FB", "#0B3D91"),
            ("Besiktas", "BJK", "#000000"),
            ("Trabzonspor", "TS", "#7B0C2E"),
            ("Istanbul Basaksehir", "IBFK", "#F47920"),
            ("Alanyaspor", "ALA", "#F58220"),
            ("Gaziantep FK", "GZT", "#8A1538"),
            ("Kasimpasa", "KAS", "#0057A8"),
            ("Konyaspor", "KON", "#00693E"),
            ("Caykur Rizespor", "RIZ", "#00843D"),
            ("Samsunspor", "SAM", "#B7002C"),
            ("Kocaelispor", "KOC", "#00693E"),
            ("Genclerbirligi", "GEN", "#B7002C"),
            ("Goztepe", "GOZ", "#E2231A"),
            ("Eyupspor", "EYU", "#7B0C2E"),
            ("Erzurumspor", "ERZ", "#00539F"),
            ("Amedspor", "AMD", "#008C45"),
            ("Corum FK", "CRM", "#000000"),
        ],
    },
    "English Championship": {
        "country": "England",
        "teams": [
            ("Sheffield United", "SHU", "#EE2737"),
            ("Bristol City", "BRC", "#E21A23"),
            ("Middlesbrough", "MID", "#E31B23"),
            ("Millwall", "MIL", "#001C58"),
            ("Blackburn Rovers", "BLB", "#009EE0"),
            ("West Bromwich Albion", "WBA", "#122F67"),
            ("Norwich City", "NOR", "#00A650"),
            ("Watford", "WAT", "#FBEE23"),
            ("Sheffield Wednesday", "SHW", "#1F3E72"),
            ("Preston North End", "PNE", "#B2B2B2"),
            ("Stoke City", "STK", "#E03A3E"),
            ("Swansea City", "SWA", "#FFFFFF"),
            ("Hull City", "HUL", "#F18A01"),
            ("Derby County", "DBY", "#FFFFFF"),
            ("Portsmouth", "POR", "#001489"),
            ("Queens Park Rangers", "QPR", "#1D5BA4"),
            ("Oxford United", "OXU", "#FFD200"),
            ("Charlton Athletic", "CHA", "#D2122E"),
            ("Wrexham", "WRX", "#C8102E"),
            ("Birmingham City", "BCF", "#0000FF"),
            ("Leicester City", "LEI", "#003090"),
        ],
    },
    "Argentine Primera Division": {
        "country": "Argentina",
        "teams": [
            ("Boca Juniors", "BOC", "#00479D"),
            ("River Plate", "RIV", "#E1000F"),
            ("Racing Club", "RAC", "#87CEEB"),
            ("Independiente", "IND", "#C8102E"),
            ("San Lorenzo", "SLO", "#00205B"),
            ("Estudiantes de La Plata", "EDLP", "#C8102E"),
            ("Gimnasia La Plata", "GEL", "#003DA5"),
            ("Velez Sarsfield", "VEL", "#FFFFFF"),
            ("Newells Old Boys", "NOB", "#E30613"),
            ("Rosario Central", "ROS", "#003DA5"),
            ("Talleres", "TAL", "#002D5C"),
            ("Belgrano", "BEL", "#7EC0E8"),
            ("Instituto", "INS", "#B7002C"),
            ("Argentinos Juniors", "AAAJ", "#B7002C"),
            ("Huracan", "HUR", "#FFFFFF"),
            ("Lanus", "LAN", "#7A1C1C"),
            ("Banfield", "BAN", "#00843D"),
            ("Defensa y Justicia", "DYJ", "#821E33"),
            ("Godoy Cruz", "GOD", "#003DA5"),
            ("Union Santa Fe", "UNI", "#B7002C"),
            ("Central Cordoba SdE", "CCO", "#000000"),
            ("Platense", "PLA", "#6E0F1E"),
            ("Barracas Central", "BAR", "#E30613"),
            ("Tigre", "TIG", "#003DA5"),
            ("Sarmiento", "SAR", "#00843D"),
            ("Aldosivi", "ALD", "#00843D"),
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
        ("predictions", "0012_seed_mls_brazil_saudi"),
    ]

    operations = [
        migrations.RunPython(seed_leagues_and_teams, noop_reverse),
    ]
