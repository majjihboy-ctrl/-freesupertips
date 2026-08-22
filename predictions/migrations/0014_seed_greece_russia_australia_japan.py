from django.db import migrations

# Fifth batch, continuing from 0009/0010/0012/0013. Notes on gaps:
# - Russian Premier League: 14/16 confirmed. 2 teams were relegated
#   after 2025-26 (Pari NN, Sochi) but the 2 promoted from the Russian
#   First League for 2026-27 weren't confirmed in available sources.
# - J1 League: reflects the well-established current lineup; Japan's
#   exact 2026 promotion/relegation swap wasn't independently confirmed.
LEAGUES = {
    "Greek Super League": {
        "country": "Greece",
        "teams": [
            ("Olympiacos", "OLY", "#E2231A"),
            ("Panathinaikos", "PAO", "#00843D"),
            ("AEK Athens", "AEK", "#FFD200"),
            ("PAOK", "PAOK", "#000000"),
            ("Aris", "ARI", "#F5A800"),
            ("OFI Crete", "OFI", "#00843D"),
            ("Panetolikos", "PANE", "#8A1538"),
            ("Asteras Tripolis", "AST", "#00539F"),
            ("Atromitos", "ATR", "#00843D"),
            ("Levadiakos", "LEV", "#0057A8"),
            ("AE Kifisia", "KIF", "#B7002C"),
            ("Volos", "VOL", "#00539F"),
            ("Iraklis", "IRA", "#000000"),
            ("Kalamata", "KAL", "#FFD200"),
        ],
    },
    "Russian Premier League": {
        "country": "Russia",
        "teams": [
            ("Zenit", "ZEN", "#00539F"),
            ("Spartak Moscow", "SPM", "#E2231A"),
            ("CSKA Moscow", "CSKA", "#B7002C"),
            ("Dynamo Moscow", "DYN", "#00539F"),
            ("Lokomotiv Moscow", "LOK", "#E2231A"),
            ("Krasnodar", "KRD", "#000000"),
            ("Rubin Kazan", "RUB", "#00843D"),
            ("Akhmat Grozny", "AKH", "#00843D"),
            ("Rostov", "ROS", "#FFD200"),
            ("Krylia Sovetov", "KRS", "#0057A8"),
            ("Akron Tolyatti", "AKR", "#B7002C"),
            ("Baltika Kaliningrad", "BAL", "#00539F"),
            ("Orenburg", "ORE", "#B7002C"),
            ("Ural", "URA", "#00539F"),
        ],
    },
    "A-League Men": {
        "country": "Australia",
        "teams": [
            ("Adelaide United", "ADL", "#B7002C"),
            ("Auckland FC", "AKL", "#4B2E83"),
            ("Brisbane Roar", "BRI", "#F5A800"),
            ("Central Coast Mariners", "CCM", "#FEDD00"),
            ("Macarthur FC", "MCF", "#7A1216"),
            ("Melbourne City", "MCY", "#6CACE4"),
            ("Melbourne Victory", "MVC", "#00539F"),
            ("Newcastle Jets", "NEW", "#0057A8"),
            ("Perth Glory", "PER", "#5B2A86"),
            ("Sydney FC", "SYD", "#00539F"),
            ("Wellington Phoenix", "WEL", "#FFD200"),
            ("Western Sydney Wanderers", "WSW", "#E2231A"),
        ],
    },
    "J1 League": {
        "country": "Japan",
        "teams": [
            ("Vissel Kobe", "VIS", "#B7002C"),
            ("Kashima Antlers", "ANT", "#B7002C"),
            ("Urawa Red Diamonds", "URA", "#E2231A"),
            ("Yokohama F. Marinos", "YFM", "#00539F"),
            ("Kawasaki Frontale", "KAW", "#00539F"),
            ("FC Tokyo", "FCT", "#00539F"),
            ("Gamba Osaka", "GAM", "#00539F"),
            ("Cerezo Osaka", "CER", "#B7002C"),
            ("Sanfrecce Hiroshima", "SAN", "#4B2E83"),
            ("Nagoya Grampus", "NAG", "#E2231A"),
            ("Shonan Bellmare", "SHO", "#00843D"),
            ("Kyoto Sanga", "KYO", "#7A1216"),
            ("Avispa Fukuoka", "AVI", "#000000"),
            ("Yokohama FC", "YFC", "#00539F"),
            ("Tokyo Verdy", "VER", "#00843D"),
            ("Machida Zelvia", "MAC", "#00539F"),
            ("Albirex Niigata", "ALB", "#E2231A"),
            ("Shimizu S-Pulse", "SPU", "#F5A800"),
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
        ("predictions", "0013_seed_ligamx_superlig_championship_argentina"),
    ]

    operations = [
        migrations.RunPython(seed_leagues_and_teams, noop_reverse),
    ]
