"""
Batch 3 of team seed data — major single-tier leagues outside the "big
five", verified against current season sources (2025/26 for European
leagues, 2025 for MLS, 2026 for Brazil's calendar-year season, 2025-26
split-season for Liga MX).

Same format/discovery mechanism as previous batches - see
_teams_data_batch1.py for details.
"""

TEAMS = {
    ("United States", "Major League Soccer"): [
        "Atlanta United", "Austin FC", "CF Montréal", "Charlotte FC",
        "Chicago Fire", "FC Cincinnati", "Colorado Rapids", "Columbus Crew",
        "D.C. United", "FC Dallas", "Houston Dynamo", "Inter Miami CF",
        "LA Galaxy", "Los Angeles FC", "Minnesota United", "Nashville SC",
        "New England Revolution", "New York City FC", "New York Red Bulls",
        "Orlando City", "Philadelphia Union", "Portland Timbers",
        "Real Salt Lake", "San Diego FC", "San Jose Earthquakes",
        "Seattle Sounders FC", "Sporting Kansas City", "St. Louis City SC",
        "Toronto FC", "Vancouver Whitecaps FC",
    ],
    ("Netherlands", "Eredivisie"): [
        "PSV Eindhoven", "Ajax", "Feyenoord", "AZ Alkmaar", "FC Twente",
        "FC Utrecht", "Go Ahead Eagles", "Sparta Rotterdam", "NEC Nijmegen",
        "FC Groningen", "sc Heerenveen", "Fortuna Sittard", "PEC Zwolle",
        "NAC Breda", "Heracles Almelo", "FC Volendam", "Excelsior Rotterdam",
        "Telstar",
    ],
    ("Portugal", "Primeira Liga"): [
        "Sporting CP", "Benfica", "Porto", "Braga", "Vitória de Guimarães",
        "Moreirense", "Santa Clara", "Famalicão", "Casa Pia",
        "Estoril Praia", "Arouca", "Nacional", "Rio Ave", "Gil Vicente",
        "AVS", "Estrela da Amadora", "Tondela", "Alverca",
    ],
    ("Belgium", "Belgian Pro League"): [
        "Union SG", "Club Brugge", "Genk", "Anderlecht", "Charleroi",
        "Cercle Brugge", "Gent", "Standard Liège", "Westerlo", "OH Leuven",
        "Royal Antwerp", "Sint-Truiden", "Dender EH", "KV Mechelen",
        "Zulte Waregem", "La Louvière",
    ],
    ("Brazil", "Campeonato Brasileiro Série A"): [
        "Flamengo", "Corinthians", "Palmeiras", "Red Bull Bragantino",
        "Santos", "São Paulo", "Botafogo", "Fluminense", "Vasco da Gama",
        "Bahia", "Vitória", "Atlético Mineiro", "Cruzeiro",
        "Athletico Paranaense", "Coritiba", "Grêmio", "Internacional",
        "Remo", "Chapecoense", "Mirassol",
    ],
    ("Mexico", "Liga MX"): [
        "América", "Atlas", "Atlético San Luis", "Cruz Azul", "Guadalajara",
        "FC Juárez", "León", "Mazatlán", "Monterrey", "Necaxa", "Pachuca",
        "Puebla", "Pumas UNAM", "Querétaro", "Santos Laguna", "Tigres UANL",
        "Tijuana", "Toluca",
    ],
    ("Turkey", "Süper Lig"): [
        "Galatasaray", "Fenerbahçe", "Trabzonspor", "Beşiktaş",
        "Samsunspor", "Göztepe", "Eyüpspor", "Çaykur Rizespor", "Kasımpaşa",
        "Konyaspor", "Gaziantep FK", "Antalyaspor", "Kayserispor",
        "Alanyaspor", "İstanbul Başakşehir", "Kocaelispor", "Gençlerbirliği",
        "Fatih Karagümrük",
    ],
}