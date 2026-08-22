from django.db import migrations

# Sixth batch, continuing from 0009/0010/0012/0013/0014. Notes on gaps:
# - Egyptian Premier League: 17 confirmed non-relegated clubs out of a
#   league that's currently 21 teams; the exact makeup for 2026-27
#   (how many are promoted back in) wasn't confirmed in available
#   sources, so promoted replacements are left out rather than guessed.
# - Danish Superliga: 10/12 confirmed. Fredericia and Vejle were
#   relegated after 2025-26, but the 2 clubs promoted from the 1st
#   Division for 2026-27 weren't confirmed in available sources.
LEAGUES = {
    "Chinese Super League": {
        "country": "China",
        "teams": [
            ("Shanghai Port", "SHP", "#003DA5"),
            ("Shanghai Shenhua", "SHS", "#00539F"),
            ("Chengdu Rongcheng", "CHR", "#B7002C"),
            ("Chongqing Tonglianglong", "CTL", "#F5A800"),
            ("Dalian Yingbo", "DAL", "#00539F"),
            ("Yunnan Yukun", "YUN", "#00843D"),
            ("Shandong Taishan", "SHD", "#00539F"),
            ("Qingdao West Coast", "QWC", "#B7002C"),
            ("Liaoning Tieren", "LIA", "#00539F"),
            ("Zhejiang", "ZHE", "#B7002C"),
            ("Shenzhen Peng City", "SPC", "#00539F"),
            ("Beijing Guoan", "BJG", "#00843D"),
            ("Henan", "HEN", "#B7002C"),
            ("Qingdao Hainiu", "QDH", "#F5A800"),
            ("Wuhan Three Towns", "WUH", "#00539F"),
            ("Tianjin Jinmen Tiger", "TJT", "#F5A800"),
        ],
    },
    "Egyptian Premier League": {
        "country": "Egypt",
        "teams": [
            ("Al Ahly", "AHL", "#B7002C"),
            ("Zamalek", "ZAM", "#FFFFFF"),
            ("Pyramids FC", "PYR", "#00843D"),
            ("Al Ittihad Alexandria", "ITT", "#00539F"),
            ("Al Masry", "MAS", "#00539F"),
            ("Ceramica Cleopatra", "CER", "#B7002C"),
            ("ENPPI", "ENP", "#00539F"),
            ("Smouha", "SMO", "#F5A800"),
            ("El Gouna", "ELG", "#00843D"),
            ("Talaea El Gaish", "TEG", "#000000"),
            ("Ghazl El Mahalla", "GEM", "#B7002C"),
            ("National Bank of Egypt", "NBE", "#00539F"),
            ("Modern Sport", "MOD", "#00843D"),
            ("Zed FC", "ZED", "#000000"),
            ("Future FC", "FUT", "#F5A800"),
            ("Al Mokawloon Al Arab", "MOK", "#00539F"),
            ("Baladeyet El Mahalla", "BEM", "#B7002C"),
        ],
    },
    "Indian Super League": {
        "country": "India",
        "teams": [
            ("Mohun Bagan Super Giant", "MBSG", "#7A1216"),
            ("East Bengal", "EBFC", "#B7002C"),
            ("Bengaluru FC", "BFC", "#00539F"),
            ("Chennaiyin FC", "CFC", "#00539F"),
            ("FC Goa", "GOA", "#7A1538"),
            ("Jamshedpur FC", "JFC", "#B7002C"),
            ("Kerala Blasters", "KBFC", "#F5A800"),
            ("Mumbai City FC", "MCFC", "#00539F"),
            ("NorthEast United FC", "NEU", "#B7002C"),
            ("Odisha FC", "ODI", "#B7002C"),
            ("Punjab FC", "PBFC", "#000000"),
            ("Inter Kashi", "IKA", "#F5A800"),
            ("Churchill Brothers", "CHU", "#00843D"),
            ("Diamond Harbour FC", "DHF", "#00539F"),
        ],
    },
    "Danish Superliga": {
        "country": "Denmark",
        "teams": [
            ("FC Copenhagen", "FCK", "#FFFFFF"),
            ("AGF", "AGF", "#00539F"),
            ("Midtjylland", "FCM", "#B7002C"),
            ("Nordsjaelland", "FCN", "#00539F"),
            ("Silkeborg", "SIL", "#B7002C"),
            ("Randers", "RAN", "#000000"),
            ("OB", "OB", "#B7002C"),
            ("Sonderjyske", "SJK", "#B7002C"),
            ("Viborg", "VIB", "#000000"),
            ("Brondby", "BIF", "#FFD200"),
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
        ("predictions", "0014_seed_greece_russia_australia_japan"),
    ]

    operations = [
        migrations.RunPython(seed_leagues_and_teams, noop_reverse),
    ]
