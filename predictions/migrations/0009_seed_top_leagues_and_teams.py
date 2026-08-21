from django.db import migrations

# Current (2026-27) rosters for the top 5 European leagues. short_name is a
# 3-4 letter code for compact display; crest_color is each club's primary
# shirt colour, used as a fallback badge colour when no crest image exists.
LEAGUES = {
    "Premier League": {
        "country": "England",
        "teams": [
            ("Arsenal", "ARS", "#EF0107"),
            ("Aston Villa", "AVL", "#95BFE5"),
            ("Bournemouth", "BOU", "#DA291C"),
            ("Brentford", "BRE", "#E30613"),
            ("Brighton & Hove Albion", "BHA", "#0057B8"),
            ("Chelsea", "CHE", "#034694"),
            ("Coventry City", "COV", "#78D0F7"),
            ("Crystal Palace", "CRY", "#1B458F"),
            ("Everton", "EVE", "#003399"),
            ("Fulham", "FUL", "#FFFFFF"),
            ("Hull City", "HUL", "#F18A01"),
            ("Ipswich Town", "IPS", "#3A64A3"),
            ("Leeds United", "LEE", "#FFCD00"),
            ("Liverpool", "LIV", "#C8102E"),
            ("Manchester City", "MCI", "#6CABDD"),
            ("Manchester United", "MUN", "#DA291C"),
            ("Newcastle United", "NEW", "#241F20"),
            ("Nottingham Forest", "NFO", "#DD0000"),
            ("Sunderland", "SUN", "#EB172B"),
            ("Tottenham Hotspur", "TOT", "#132257"),
        ],
    },
    "La Liga": {
        "country": "Spain",
        "teams": [
            ("Real Madrid", "RMA", "#FEBE10"),
            ("Barcelona", "BAR", "#A50044"),
            ("Atletico Madrid", "ATM", "#CB3524"),
            ("Athletic Bilbao", "ATH", "#EE2523"),
            ("Villarreal", "VIL", "#FFE667"),
            ("Real Betis", "BET", "#00954C"),
            ("Celta Vigo", "CEL", "#8AC3EE"),
            ("Rayo Vallecano", "RAY", "#E3262F"),
            ("Osasuna", "OSA", "#D91A21"),
            ("Real Sociedad", "RSO", "#0067B1"),
            ("Valencia", "VAL", "#EE3524"),
            ("Sevilla", "SEV", "#D8102A"),
            ("Getafe", "GET", "#005AA7"),
            ("Alaves", "ALA", "#0055A5"),
            ("Espanyol", "ESP", "#0A4C93"),
            ("Levante", "LEV", "#B3122A"),
            ("Elche", "ELC", "#87CEEB"),
            ("Racing Santander", "RAC", "#00A650"),
            ("Deportivo La Coruna", "DEP", "#0055A4"),
            ("Malaga", "MAL", "#0066CC"),
        ],
    },
    "Serie A": {
        "country": "Italy",
        "teams": [
            ("Inter Milan", "INT", "#010E80"),
            ("Napoli", "NAP", "#12A0D7"),
            ("Atalanta", "ATA", "#1E71B8"),
            ("Juventus", "JUV", "#000000"),
            ("AC Milan", "MIL", "#FB090B"),
            ("Bologna", "BOL", "#941D24"),
            ("Roma", "ROM", "#8E1F2F"),
            ("Lazio", "LAZ", "#87D8F7"),
            ("Fiorentina", "FIO", "#642F8E"),
            ("Torino", "TOR", "#881D1D"),
            ("Udinese", "UDI", "#000000"),
            ("Genoa", "GEN", "#0F2350"),
            ("Cagliari", "CAG", "#B71234"),
            ("Parma", "PAR", "#FFE001"),
            ("Como", "COM", "#0066B3"),
            ("Lecce", "LEC", "#FDE314"),
            ("Sassuolo", "SAS", "#149E4F"),
            ("Venezia", "VEN", "#FF7900"),
            ("Frosinone", "FRO", "#FFCC00"),
            ("Monza", "MON", "#D4001A"),
        ],
    },
    "Bundesliga": {
        "country": "Germany",
        "teams": [
            ("Bayern Munich", "BAY", "#DC052D"),
            ("Bayer Leverkusen", "B04", "#E32221"),
            ("RB Leipzig", "RBL", "#DD0741"),
            ("Borussia Dortmund", "BVB", "#FDE100"),
            ("Eintracht Frankfurt", "SGE", "#E1000F"),
            ("SC Freiburg", "SCF", "#000000"),
            ("Mainz 05", "M05", "#C3141E"),
            ("Borussia Monchengladbach", "BMG", "#000000"),
            ("Werder Bremen", "SVW", "#1D9053"),
            ("VfB Stuttgart", "VFB", "#E32219"),
            ("Union Berlin", "FCU", "#EB1923"),
            ("FC Augsburg", "FCA", "#BA3733"),
            ("TSG Hoffenheim", "TSG", "#1C63B7"),
            ("Hamburger SV", "HSV", "#0F1A2E"),
            ("1. FC Koln", "KOE", "#ED1C24"),
            ("Schalke 04", "S04", "#004D9D"),
            ("SV Elversberg", "ELV", "#004B93"),
            ("SC Paderborn", "SCP", "#1B57A5"),
        ],
    },
    "Ligue 1": {
        "country": "France",
        "teams": [
            ("Paris Saint-Germain", "PSG", "#004170"),
            ("Marseille", "OM", "#2FAEE0"),
            ("Monaco", "ASM", "#E51A23"),
            ("Lille", "LIL", "#E01E13"),
            ("Lyon", "OL", "#DA0F26"),
            ("Nice", "OGC", "#CC0000"),
            ("Lens", "RCL", "#FFD100"),
            ("Rennes", "SRFC", "#E2001A"),
            ("Strasbourg", "RCS", "#0055A4"),
            ("Toulouse", "TFC", "#4B1E78"),
            ("Auxerre", "AJA", "#004B93"),
            ("Angers", "SCO", "#000000"),
            ("Brest", "SB29", "#E2001A"),
            ("Le Havre", "HAC", "#00549F"),
            ("Paris FC", "PFC", "#0C0C6E"),
            ("Lorient", "FCL", "#F68A1E"),
            ("Troyes", "ESTAC", "#0072CE"),
            ("Le Mans", "LM72", "#FFFFFF"),
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
    # Deliberately not deleting seeded data on reverse -- by the time this
    # migration would be reversed, real match/prediction data may already
    # reference these teams, and deleting League/Team would cascade-delete
    # that too.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("predictions", "0008_grant_admin_superuser"),
    ]

    operations = [
        migrations.RunPython(seed_leagues_and_teams, noop_reverse),
    ]
