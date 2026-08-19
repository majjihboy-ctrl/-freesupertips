"""
Batch 4 of team seed data — second tiers of several batch-3 leagues,
verified against current season sources. Note: US and Brazil run
calendar-year seasons, so these reflect the *current* 2026 season for
Brazil (Série B) and the most recently completed 2025 season for the US
(USL Championship 2026 was mid-flux with a labor dispute and roster
changes at fetch time, so 2025's confirmed 24-team season was used
instead - update when 2026 settles).

Same format/discovery mechanism as previous batches.
"""

TEAMS = {
    ("United States", "USL Championship"): [
        "Colorado Springs Switchbacks FC", "El Paso Locomotive FC",
        "Las Vegas Lights FC", "Lexington SC", "Monterey Bay FC",
        "New Mexico United", "Oakland Roots SC", "Orange County SC",
        "Phoenix Rising FC", "Sacramento Republic FC", "San Antonio FC",
        "FC Tulsa", "Birmingham Legion FC", "Charleston Battery",
        "Detroit City FC", "Hartford Athletic", "Indy Eleven",
        "Loudoun United FC", "Louisville City FC", "Miami FC",
        "North Carolina FC", "Pittsburgh Riverhounds SC", "Rhode Island FC",
        "Tampa Bay Rowdies",
    ],
    ("Netherlands", "Eerste Divisie"): [
        "Cambuur", "ADO Den Haag", "FC Dordrecht", "De Graafschap",
        "FC Emmen", "FC Den Bosch", "Jong AZ", "FC Eindhoven",
        "Roda JC Kerkrade", "Helmond Sport", "VVV-Venlo", "MVV Maastricht",
        "TOP Oss", "Vitesse", "Jong PSV", "Jong Ajax", "Jong FC Utrecht",
        "Almere City", "RKC Waalwijk", "Willem II",
    ],
    ("Portugal", "Liga Portugal 2"): [
        "Académico de Viseu", "Marítimo", "Oliveirense", "Paços de Ferreira",
        "Farense", "Benfica B", "Porto B", "Sporting CP B", "Penafiel",
        "Portimonense", "Torreense", "União de Leiria", "Vizela",
        "Feirense", "Felgueiras", "Leixões", "Chaves", "Lusitânia Lourosa",
    ],
    ("Belgium", "Challenger Pro League"): [
        "KV Kortrijk", "Beerschot", "SK Beveren", "RSCA Futures",
        "KAS Eupen", "Club NXT", "Jong Genk", "Lommel SK", "RWDM Brussels",
        "Jong KAA Gent", "Francs Borains", "RFC Seraing",
        "Patro Eisden Maasmechelen", "Lokeren-Temse", "Olympic Charleroi",
        "Lierse Kempenzonen", "RFC Liège",
    ],
    ("Brazil", "Campeonato Brasileiro Série B"): [
        "Atlético Goianiense", "Goiás", "Vila Nova", "Operário Ferroviário",
        "Avaí", "Criciúma", "Botafogo-SP", "Novorizontino",
        "América Mineiro", "Athletic", "CRB", "Cuiabá", "Londrina",
        "Náutico", "Ponte Preta", "São Bernardo", "Juventude", "Sport",
        "Fortaleza", "Ceará",
    ],
}