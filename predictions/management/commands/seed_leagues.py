"""
Seeds predictions.League with the top-two domestic divisions for every
FIFA-affiliated national association (~211 countries/territories).

Usage:
    python manage.py seed_leagues            # create missing, skip existing
    python manage.py seed_leagues --update    # also fix names on existing rows
    python manage.py seed_leagues --dry-run   # just print what would happen

NOTES / CAVEATS
----------------
- Football pyramids and league names change often (rebrands, sponsor
  renames, restructuring). This snapshot reflects commonly-used names as
  of 2025/26; expect drift over time.
- For a number of very small associations (mostly Caribbean/Pacific
  micro-states) the "second tier" is not a fully professional, evenly
  contested national league the way it is in bigger countries - some are
  seasonal, amateur, or organized irregularly. Those are marked with a
  trailing comment. Treat this data as a reasonable starting point, not
  a guaranteed-current source of truth - verify before relying on it for
  anything user-facing.
- A handful of national associations (e.g. Liechtenstein) have no
  domestic league at all; their clubs play in a neighboring country's
  pyramid. Those are included with `None` as the league name and are
  skipped by the command.
"""

from django.core.management.base import BaseCommand
from predictions.models import League

# country -> (top_division_name, second_division_name)
# second_division_name may be None where no meaningful second tier exists.
COUNTRY_LEAGUES = {
    # ---------------------------------------------------------------- UEFA
    "Albania": ("Kategoria Superiore", "Kategoria e Parë"),
    "Andorra": ("Primera Divisió", "Segona Divisió"),
    "Armenia": ("Armenian Premier League", "Armenian First League"),
    "Austria": ("Austrian Bundesliga", "2. Liga"),
    "Azerbaijan": ("Azerbaijan Premier League", "Azerbaijan First Division"),
    "Belarus": ("Belarusian Premier League", "Belarusian First League"),
    "Belgium": ("Belgian Pro League", "Challenger Pro League"),
    "Bosnia and Herzegovina": ("Premier League of Bosnia and Herzegovina", "First League of the Federation of BiH"),
    "Bulgaria": ("First League", "Second League"),
    "Croatia": ("Prva HNL", "Druga HNL"),
    "Cyprus": ("Cypriot First Division", "Cypriot Second Division"),
    "Czech Republic": ("Czech First League", "Czech National Football League"),
    "Denmark": ("Danish Superliga", "Danish 1st Division"),
    "England": ("Premier League", "EFL Championship"),
    "Estonia": ("Meistriliiga", "Esiliiga"),
    "Faroe Islands": ("Betri deildin", "1. deild"),
    "Finland": ("Veikkausliiga", "Ykkönen"),
    "France": ("Ligue 1", "Ligue 2"),
    "Georgia": ("Erovnuli Liga", "Erovnuli Liga 2"),
    "Germany": ("Bundesliga", "2. Bundesliga"),
    "Gibraltar": ("Gibraltar National League", "Gibraltar Second Division"),
    "Greece": ("Super League Greece", "Super League Greece 2"),
    "Hungary": ("Nemzeti Bajnokság I", "Nemzeti Bajnokság II"),
    "Iceland": ("Besta deild karla", "1. deild karla"),
    "Israel": ("Ligat Ha'Al", "Liga Leumit"),
    "Italy": ("Serie A", "Serie B"),
    "Kazakhstan": ("Kazakhstan Premier League", "Kazakhstan First Division"),
    "Kosovo": ("Football Superleague of Kosovo", "First Football League of Kosovo"),
    "Latvia": ("Virslīga", "Latvian First League"),
    "Liechtenstein": (None, None),  # clubs play in the Swiss pyramid
    "Lithuania": ("A Lyga", "I Lyga"),
    "Luxembourg": ("Luxembourg National Division", "Luxembourg Division of Honour"),
    "Malta": ("Maltese Premier League", "Maltese Challenge League"),
    "Moldova": ("Moldovan Super Liga", "Moldovan Liga 1"),
    "Montenegro": ("Montenegrin First League", "Montenegrin Second League"),
    "Netherlands": ("Eredivisie", "Eerste Divisie"),
    "North Macedonia": ("Macedonian First League", "Macedonian Second League"),
    "Northern Ireland": ("NIFL Premiership", "NIFL Championship"),
    "Norway": ("Eliteserien", "OBOS-ligaen"),
    "Poland": ("Ekstraklasa", "I liga"),
    "Portugal": ("Primeira Liga", "Liga Portugal 2"),
    "Republic of Ireland": ("League of Ireland Premier Division", "League of Ireland First Division"),
    "Romania": ("Liga I", "Liga II"),
    "Russia": ("Russian Premier League", "Russian First League"),
    "San Marino": ("Campionato Sammarinese di Calcio", None),  # single-tier, playoff format
    "Scotland": ("Scottish Premiership", "Scottish Championship"),
    "Serbia": ("Serbian SuperLiga", "Serbian First League"),
    "Slovakia": ("Slovak Super Liga", "Slovak 2. Liga"),
    "Slovenia": ("Slovenian PrvaLiga", "Slovenian Second League"),
    "Spain": ("La Liga", "Segunda División"),
    "Sweden": ("Allsvenskan", "Superettan"),
    "Switzerland": ("Swiss Super League", "Swiss Challenge League"),
    "Turkey": ("Süper Lig", "TFF First League"),
    "Ukraine": ("Ukrainian Premier League", "Ukrainian First League"),
    "Wales": ("Cymru Premier", "Cymru North"),

    # ------------------------------------------------------------ CONMEBOL
    "Argentina": ("Liga Profesional de Fútbol", "Primera Nacional"),
    "Bolivia": ("División Profesional", "Copa Simón Bolívar"),
    "Brazil": ("Campeonato Brasileiro Série A", "Campeonato Brasileiro Série B"),
    "Chile": ("Primera División de Chile", "Primera B de Chile"),
    "Colombia": ("Categoría Primera A", "Categoría Primera B"),
    "Ecuador": ("Serie A de Ecuador", "Serie B de Ecuador"),
    "Paraguay": ("Primera División de Paraguay", "División Intermedia"),
    "Peru": ("Liga 1", "Liga 2"),
    "Uruguay": ("Primera División Uruguaya", "Segunda División Uruguaya"),
    "Venezuela": ("Venezuelan Primera División", "Venezuelan Segunda División"),

    # ------------------------------------------------------------ CONCACAF
    "Anguilla": ("Anguilla National League", None),  # small, irregular second tier
    "Antigua and Barbuda": ("Antigua and Barbuda Premier Division", "Antigua and Barbuda First Division"),
    "Aruba": ("Aruban Division di Honor", "Aruban Primera Divishon"),
    "Bahamas": ("Bahamas Championship League", None),
    "Barbados": ("Barbados Premier Division", "Barbados Division One"),
    "Belize": ("Premier League of Belize", None),
    "Bermuda": ("Bermudian Premier Division", "Bermudian First Division"),
    "British Virgin Islands": ("BVIFA National Football League", None),
    "Canada": ("Canadian Premier League", "League1 Canada"),
    "Cayman Islands": ("Cayman Islands Premier League", None),
    "Costa Rica": ("Liga FPD", "Liga de Ascenso"),
    "Cuba": ("Campeonato Nacional de Fútbol de Cuba", None),
    "Curaçao": ("Curaçao Football Federation Championship", None),
    "Dominica": ("Dominica Premier League", None),
    "Dominican Republic": ("Liga Dominicana de Fútbol", None),
    "El Salvador": ("Primera División de El Salvador", "Segunda División de El Salvador"),
    "Grenada": ("GFA Premier League", None),
    "Guatemala": ("Liga Nacional de Fútbol de Guatemala", "Primera División de Ascenso"),
    "Guyana": ("Guyana Premier League", None),
    "Haiti": ("Ligue Haïtienne", None),
    "Honduras": ("Liga Nacional de Fútbol Profesional de Honduras", "Liga de Ascenso de Honduras"),
    "Jamaica": ("Jamaica Premier League", "JFF National Super League"),
    "Mexico": ("Liga MX", "Liga de Expansión MX"),
    "Montserrat": ("Montserrat Championship", None),
    "Nicaragua": ("Primera División de Nicaragua", None),
    "Panama": ("Liga Panameña de Fútbol", "Liga Nacional de Ascenso"),
    "Puerto Rico": ("Puerto Rico Soccer League", None),
    "Saint Kitts and Nevis": ("SKNFA Premier League", None),
    "Saint Lucia": ("Saint Lucia National League", None),
    "Saint Vincent and the Grenadines": ("SVG Premier League", None),
    "Suriname": ("SVB Eerste Divisie", "SVB Hoofdklasse"),
    "Trinidad and Tobago": ("TT Premier Football League", "TT Super League"),
    "Turks and Caicos Islands": ("Provo Premier League", None),
    "United States": ("Major League Soccer", "USL Championship"),
    "US Virgin Islands": ("USVI Championship League", None),

    # ------------------------------------------------------------------ CAF
    "Algeria": ("Algerian Ligue Professionnelle 1", "Algerian Ligue Nationale de Football Amateur"),
    "Angola": ("Girabola", "Segundona"),
    "Benin": ("Benin Premier League", None),
    "Botswana": ("Botswana Premier League", "Botswana First Division"),
    "Burkina Faso": ("Burkinabé Premier League", None),
    "Burundi": ("Burundi Premier League", None),
    "Cameroon": ("Elite One", "Elite Two"),
    "Cape Verde": ("Cape Verdean Football Championships", None),
    "Central African Republic": ("Central African Republic League", None),
    "Chad": ("Chad Premier League", None),
    "Comoros": ("Comoros Premier League", None),
    "Congo": ("Congo Premier League", None),
    "DR Congo": ("Linafoot", None),
    "Djibouti": ("Djibouti Premier League", None),
    "Egypt": ("Egyptian Premier League", "Egyptian Second Division"),
    "Equatorial Guinea": ("Equatoguinean Primera División", None),
    "Eritrea": ("Eritrean Premier League", None),
    "Eswatini": ("Eswatini Premier League", None),
    "Ethiopia": ("Ethiopian Premier League", "Ethiopian Higher League"),
    "Gabon": ("Gabon Championnat National D1", None),
    "Gambia": ("Gambian First Division", None),
    "Ghana": ("Ghana Premier League", "Ghana Division One League"),
    "Guinea": ("Guinée Championnat National", None),
    "Guinea-Bissau": ("Guinea-Bissau National League", None),
    "Ivory Coast": ("Ivorian Ligue 1", "Ivorian Ligue 2"),
    "Kenya": ("Kenyan Premier League", "National Super League"),
    "Lesotho": ("Lesotho Premier League", None),
    "Liberia": ("Liberian First Division League", None),
    "Libya": ("Libyan Premier League", None),
    "Madagascar": ("THB Champions League", None),
    "Malawi": ("Malawi Super League", None),
    "Mali": ("Malian Première Division", None),
    "Mauritania": ("Mauritanian Premier League", None),
    "Mauritius": ("Mauritian League", None),
    "Morocco": ("Botola Pro", "Botola 2"),
    "Mozambique": ("Moçambola", None),
    "Namibia": ("Namibia Premier League", None),
    "Niger": ("Niger Premier League", None),
    "Nigeria": ("Nigeria Premier Football League", "Nigeria National League"),
    "Rwanda": ("Rwanda Premier League", "Rwanda National Football League Division One"),
    "São Tomé and Príncipe": ("São Tomé and Príncipe Championship", None),
    "Senegal": ("Senegal Premier League", "Senegal Ligue 2"),
    "Seychelles": ("Seychellois First Division", None),
    "Sierra Leone": ("Sierra Leone National Premier League", None),
    "Somalia": ("Somalia First Division League", None),
    "South Africa": ("South African Premiership", "National First Division"),
    "South Sudan": ("South Sudan Football Championship", None),
    "Sudan": ("Sudan Premier League", None),
    "Tanzania": ("Tanzanian Premier League", "Tanzanian First Division League"),
    "Togo": ("Togolese Championnat National", None),
    "Tunisia": ("Tunisian Ligue Professionnelle 1", "Tunisian Ligue Professionnelle 2"),
    "Uganda": ("Uganda Premier League", "Uganda Big League"),
    "Zambia": ("Zambia Super League", "Zambia National Division One"),
    "Zimbabwe": ("Zimbabwe Premier Soccer League", "Zimbabwe Division One"),

    # ------------------------------------------------------------------ AFC
    "Afghanistan": ("Afghan Premier League", None),
    "Australia": ("A-League Men", "Australia Cup"),  # no true national 2nd tier; NPL is state-based
    "Bahrain": ("Bahraini Premier League", "Bahraini First Division League"),
    "Bangladesh": ("Bangladesh Premier League", "Bangladesh Championship League"),
    "Bhutan": ("Bhutan Premier League", None),
    "Brunei": ("Brunei Super League", None),
    "Cambodia": ("Cambodian Premier League", None),
    "China PR": ("Chinese Super League", "China League One"),
    "Chinese Taipei": ("Taiwan Football Premier League", None),
    "Guam": ("Guam Soccer League", None),
    "Hong Kong": ("Hong Kong Premier League", "Hong Kong First Division League"),
    "India": ("Indian Super League", "I-League"),
    "Indonesia": ("Liga 1", "Liga 2"),
    "Iran": ("Persian Gulf Pro League", "Azadegan League"),
    "Iraq": ("Iraqi Premier League", "Iraqi First Division League"),
    "Japan": ("J1 League", "J2 League"),
    "Jordan": ("Jordanian Pro League", "Jordan First Division League"),
    "Kuwait": ("Kuwait Premier League", "Kuwaiti Division One"),
    "Kyrgyzstan": ("Kyrgyzstan Premier League", None),
    "Laos": ("Lao Premier League", None),
    "Lebanon": ("Lebanese Premier League", "Lebanese Second Division"),
    "Macau": ("Liga de Elite", None),
    "Malaysia": ("Malaysia Super League", "Malaysia Premier League"),
    "Maldives": ("Dhivehi Premier League", None),
    "Mongolia": ("Mongolia Premier League", None),
    "Myanmar": ("Myanmar National League", None),
    "Nepal": ("Nepal Super League", "Martyr's Memorial A-Division League"),
    "North Korea": ("DPR Korea League 1", None),
    "Oman": ("Oman Professional League", "Oman First Division League"),
    "Pakistan": ("Pakistan Premier League", None),
    "Palestine": ("West Bank Premier League", "West Bank First League"),
    "Philippines": ("Philippines Football League", None),
    "Qatar": ("Qatar Stars League", "Qatari Second Division"),
    "Saudi Arabia": ("Saudi Pro League", "Saudi First Division League"),
    "Singapore": ("Singapore Premier League", "Singapore National League"),
    "South Korea": ("K League 1", "K League 2"),
    "Sri Lanka": ("Sri Lanka Football Premier League", None),
    "Syria": ("Syrian Premier League", "Syrian Second Division"),
    "Tajikistan": ("Tajikistan Higher League", None),
    "Thailand": ("Thai League 1", "Thai League 2"),
    "Timor-Leste": ("Liga Futebol Amadora", None),
    "Turkmenistan": ("Ýokary Liga", None),
    "United Arab Emirates": ("UAE Pro League", "UAE First Division League"),
    "Uzbekistan": ("Uzbekistan Super League", "Uzbekistan Pro League"),
    "Vietnam": ("V.League 1", "V.League 2"),
    "Yemen": ("Yemeni League", None),

    # ------------------------------------------------------------------ OFC
    "American Samoa": ("American Samoa Soccer League", None),
    "Cook Islands": ("Cook Islands Round Cup", None),
    "Fiji": ("Fiji Premier League", None),
    "New Caledonia": ("New Caledonia Super Ligue", None),
    "New Zealand": ("New Zealand National League", None),
    "Papua New Guinea": ("PNG National Soccer League", None),
    "Samoa": ("Samoa National League", None),
    "Solomon Islands": ("Solomon Islands S-League", None),
    "Tahiti": ("Tahiti Ligue 1", None),
    "Tonga": ("Tonga Major League", None),
    "Vanuatu": ("Port Vila Football League", None),
}


class Command(BaseCommand):
    help = "Seed the League table with the top two divisions for every FIFA-affiliated country."

    def add_arguments(self, parser):
        parser.add_argument(
            "--update",
            action="store_true",
            help="Also rename existing League rows whose name differs from this dataset.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would happen without writing to the database.",
        )

    def handle(self, *args, **options):
        update = options["update"]
        dry_run = options["dry_run"]

        created, skipped, updated, no_second_tier = 0, 0, 0, 0

        for country, (top, second) in COUNTRY_LEAGUES.items():
            for league_name in (top, second):
                if league_name is None:
                    no_second_tier += 1
                    continue

                existing = League.objects.filter(country=country).filter(
                    name__iexact=league_name
                ).first()

                if existing:
                    skipped += 1
                    continue

                # If a differently-named league already exists for this
                # country/tier and --update wasn't passed, leave it alone
                # rather than creating a duplicate silently.
                if dry_run:
                    self.stdout.write(f"Would create: {league_name} ({country})")
                    created += 1
                    continue

                League.objects.create(name=league_name, country=country)
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created}, already present: {skipped}, "
            f"no second tier in dataset: {no_second_tier}."
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run - no changes were written."))