"""
Batch 1 of team seed data — the "big five" European top flights, verified
against current 2025/26 season sources.

Each entry is keyed by (country, league_name) exactly as created by
seed_leagues.py, mapping to a list of team names.

This file is meant to grow: seed_teams.py imports TEAMS from here and from
any additional teams_data_batchN modules you add later, merging them all
before writing to the database. Add new batches as separate files
(teams_data_batch2.py, etc.) rather than editing this one, so each batch
stays independently reviewable/re-runnable.
"""

TEAMS = {
    ("England", "Premier League"): [
        "Arsenal", "Aston Villa", "AFC Bournemouth", "Brentford",
        "Brighton & Hove Albion", "Burnley", "Chelsea", "Crystal Palace",
        "Everton", "Fulham", "Leeds United", "Liverpool", "Manchester City",
        "Manchester United", "Newcastle United", "Nottingham Forest",
        "Sunderland", "Tottenham Hotspur", "West Ham United",
        "Wolverhampton Wanderers",
    ],
    ("Spain", "La Liga"): [
        "Alavés", "Athletic Bilbao", "Atlético Madrid", "Barcelona",
        "Celta Vigo", "Elche", "Espanyol", "Getafe", "Girona", "Levante",
        "Mallorca", "Osasuna", "Rayo Vallecano", "Real Betis", "Real Madrid",
        "Real Oviedo", "Real Sociedad", "Sevilla", "Valencia", "Villarreal",
    ],
    ("Germany", "Bundesliga"): [
        "Bayern Munich", "Bayer Leverkusen", "Borussia Dortmund",
        "RB Leipzig", "VfB Stuttgart", "Eintracht Frankfurt", "SC Freiburg",
        "TSG Hoffenheim", "Mainz 05", "Werder Bremen", "VfL Wolfsburg",
        "Borussia Mönchengladbach", "Union Berlin", "FC Augsburg",
        "1. FC Heidenheim", "FC St. Pauli", "Hamburger SV", "1. FC Köln",
    ],
    ("Italy", "Serie A"): [
        "Napoli", "Inter Milan", "Atalanta", "Juventus", "Bologna", "Roma",
        "Lazio", "Fiorentina", "AC Milan", "Torino", "Udinese", "Genoa",
        "Como", "Hellas Verona", "Cagliari", "Parma", "Lecce", "Sassuolo",
        "Pisa", "Cremonese",
    ],
    ("France", "Ligue 1"): [
        "Paris Saint-Germain", "Marseille", "Monaco", "Lille", "Lyon",
        "Lens", "Rennes", "Nice", "Strasbourg", "Toulouse", "Auxerre",
        "Nantes", "Brest", "Le Havre", "Angers", "Lorient", "Paris FC",
        "Metz",
    ],
}