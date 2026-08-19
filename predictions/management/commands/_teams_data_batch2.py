"""
Batch 2 of team seed data — second tiers of the "big five" European
leagues, verified against current 2025/26 season sources.

Same format as _teams_data_batch1.py. seed_teams.py auto-discovers and
merges this file automatically - no other changes needed.
"""

TEAMS = {
    ("England", "EFL Championship"): [
        "Sheffield United", "Coventry City", "Bristol City", "Middlesbrough",
        "West Bromwich Albion", "Norwich City", "Watford", "Hull City",
        "Preston North End", "Blackburn Rovers", "Millwall", "Swansea City",
        "Stoke City", "Queens Park Rangers", "Derby County", "Oxford United",
        "Portsmouth", "Sheffield Wednesday", "Leicester City", "Ipswich Town",
        "Southampton", "Birmingham City", "Wrexham", "Charlton Athletic",
    ],
    ("Spain", "Segunda División"): [
        "Albacete", "Almería", "Andorra", "Burgos", "Cádiz", "Castellón",
        "Ceuta", "Córdoba", "Cultural Leonesa", "Deportivo La Coruña",
        "Eibar", "Granada", "Huesca", "Las Palmas", "Leganés", "Málaga",
        "Mirandés", "Racing Santander", "Real Sociedad B", "Sporting Gijón",
        "Valladolid", "Zaragoza",
    ],
    ("Germany", "2. Bundesliga"): [
        "Hertha BSC", "Arminia Bielefeld", "VfL Bochum",
        "Eintracht Braunschweig", "Darmstadt 98", "Dynamo Dresden",
        "Fortuna Düsseldorf", "SV Elversberg", "Greuther Fürth",
        "Hannover 96", "1. FC Kaiserslautern", "Karlsruher SC",
        "Holstein Kiel", "1. FC Magdeburg", "Preußen Münster",
        "1. FC Nürnberg", "SC Paderborn", "Schalke 04",
    ],
    ("Italy", "Serie B"): [
        "Monza", "Frosinone", "Catanzaro", "Juve Stabia", "Modena",
        "Palermo", "Empoli", "Bari", "Pescara", "Virtus Entella", "Venezia",
        "Sampdoria", "Spezia", "Mantova", "Reggiana", "Avellino", "Cesena",
        "Padova", "Carrarese", "Südtirol",
    ],
    ("France", "Ligue 2"): [
        "Reims", "Saint-Étienne", "Montpellier", "Dunkerque", "Guingamp",
        "Annecy", "Laval", "Bastia", "Grenoble", "Troyes", "Amiens", "Pau",
        "Rodez", "Red Star", "Clermont", "Nancy", "Le Mans", "Boulogne",
    ],
}