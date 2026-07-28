import decimal
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decouple import config
from predictions.models import League, Team, Match, Tip, TipLeg
from predictions.utils import refresh_match_prediction


class Command(BaseCommand):
    help = "Fetch today's matches + auto-generate smart tips (API-Football free tier)"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, default=None, help="YYYY-MM-DD")
        parser.add_argument("--tomorrow", action="store_true", help="Fetch tomorrow")
        parser.add_argument("--live", action="store_true", help="Fetch only live matches")
        parser.add_argument("--with-odds", action="store_true", help="Fetch bookmaker odds")
        parser.add_argument("--with-h2h", action="store_true", help="Fetch H2H + form")
        parser.add_argument("--create-tips", action="store_true", help="Auto-create free tips from matches")

    def handle(self, *args, **options):
        API_KEY = config("API_FOOTBALL_KEY", default="")
        if not API_KEY:
            self.stdout.write(self.style.ERROR("API_FOOTBALL_KEY not found in .env"))
            return

        headers = {"x-apisports-key": API_KEY}
        base_url = "https://v3.football.api-sports.io"
        request_count = 0

        # Build date
        if options["live"]:
            params = {"live": "all"}
            self.stdout.write("Fetching LIVE matches...")
        elif options["tomorrow"]:
            target_dt = timezone.now() + timedelta(days=1)
            target_date = target_dt.strftime("%Y-%m-%d")
            params = {"date": target_date}
            self.stdout.write(f"Fetching matches for {target_date}...")
        elif options["date"]:
            target_date = options["date"]
            params = {"date": target_date}
            self.stdout.write(f"Fetching matches for {target_date}...")
        else:
            target_date = timezone.now().strftime("%Y-%m-%d")
            params = {"date": target_date}
            self.stdout.write(f"Fetching TODAY's matches ({target_date})...")

        try:
            r = requests.get(f"{base_url}/fixtures", headers=headers, params=params, timeout=20)
            request_count += 1
            data = r.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"API request failed: {e}"))
            return

        if data.get("errors"):
            self.stdout.write(self.style.ERROR(f"API Error: {data['errors']}"))
            return

        fixtures = data.get("response", [])
        self.stdout.write(f"API returned {len(fixtures)} fixtures (req #{request_count}/100)\n")

        if not fixtures:
            self.stdout.write(self.style.WARNING("No matches found."))
            return

        total_created = 0
        tips_created = 0

        for fixture in fixtures:
            home_data = fixture["teams"]["home"]
            away_data = fixture["teams"]["away"]
            fixture_info = fixture["fixture"]
            league_info = fixture["league"]

            league, _ = League.objects.get_or_create(
                name=league_info["name"],
                defaults={"country": league_info["country"]},
            )

            home_team, _ = Team.objects.get_or_create(
                name=home_data["name"],
                defaults={
                    "short_name": home_data["name"][:3].upper(),
                    "league": league,
                    "crest_color": "#1a3a5c",
                },
            )

            away_team, _ = Team.objects.get_or_create(
                name=away_data["name"],
                defaults={
                    "short_name": away_data["name"][:3].upper(),
                    "league": league,
                    "crest_color": "#1a3a5c",
                },
            )

            api_status = fixture_info["status"]["short"]
            status_map = {
                "NS": "scheduled", "1H": "live", "HT": "live", "2H": "live",
                "ET": "live", "P": "live", "FT": "finished", "AET": "finished",
                "PEN": "finished", "SUSP": "postponed", "INT": "live",
                "CANC": "postponed", "ABD": "postponed", "AWD": "finished", "WO": "finished",
            }

            match, created = Match.objects.update_or_create(
                home_team=home_team,
                away_team=away_team,
                kickoff=fixture_info["date"],
                defaults={
                    "league": league,
                    "status": status_map.get(api_status, "scheduled"),
                    "home_score": fixture["goals"]["home"],
                    "away_score": fixture["goals"]["away"],
                },
            )

            if created:
                total_created += 1
                try:
                    refresh_match_prediction(match)
                except Exception:
                    pass

            # Fetch extra data
            if options["with_h2h"] and request_count < 95:
                self._fetch_h2h(base_url, headers, match, home_team, away_team)
                request_count += 1
                self._fetch_form(base_url, headers, match, home_team, is_home=True)
                request_count += 1
                self._fetch_form(base_url, headers, match, away_team, is_home=False)
                request_count += 1

            if options["with_odds"] and request_count < 98:
                self._fetch_odds(base_url, headers, match, fixture_info["id"])
                request_count += 1

            # Auto-create smart tip
            if options["create_tips"] and match.status == "scheduled":
                tip_data = self._generate_tip(match, home_team, away_team)
                if tip_data:
                    tip, tip_created = Tip.objects.get_or_create(
                        title="",
                        tip_type="free",
                        bet_type="single",
                        defaults={
                            "status": "pending",
                            "stake": decimal.Decimal("1.00"),
                            "description": tip_data["reasoning"],
                            "is_featured": tip_data["confidence"] >= 70,
                        },
                    )
                    if tip_created:
                        TipLeg.objects.create(
                            tip=tip,
                            match=match,
                            fixture_text=f"{home_team.name} vs {away_team.name}",
                            league=league.name,
                            kickoff=match.kickoff,
                            prediction=tip_data["prediction"],
                            odds=tip_data["odds"],
                        )
                        tips_created += 1
                        self.stdout.write(
                            f"  🎯 FREE TIP: {home_team.name} vs {away_team.name} → "
                            f"{tip_data['prediction']} @ {tip_data['odds']} "
                            f"(confidence: {tip_data['confidence']}%)"
                        )

            if request_count >= 100:
                self.stdout.write(self.style.WARNING("Daily API limit reached!"))
                break

        self.stdout.write("─" * 50)
        self.stdout.write(self.style.SUCCESS(
            f"Done. Matches: {total_created} new. Tips: {tips_created} auto-generated. "
            f"API used: {request_count}/100."
        ))

    # ── SMART TIP GENERATOR ──
    def _generate_tip(self, match, home_team, away_team):
        """
        Analyzes model data, H2H, form, and odds to generate a prediction.
        Returns dict: {prediction, odds, confidence, reasoning} or None.
        """
        h_xg = match.pred_home_goals or 0
        a_xg = match.pred_away_goals or 0
        h_prob = match.pred_home_win or 0
        d_prob = match.pred_draw or 0
        a_prob = match.pred_away_win or 0
        total_xg = h_xg + a_xg

        # Bookmaker odds (if fetched)
        bm_home = match.bookmaker_odds_home
        bm_draw = match.bookmaker_odds_draw
        bm_away = match.bookmaker_odds_away

        reasons = []
        confidence = 50
        prediction = None
        odds = decimal.Decimal("1.85")

        # CRITERIA 1: Strong home favorite
        if h_xg - a_xg > 0.6 and h_prob > 0.55:
            prediction = "Home Win"
            confidence = int(h_prob * 100)
            reasons.append(f"Model gives home win {h_prob:.0%} probability (xG: {h_xg:.1f} vs {a_xg:.1f})")

        # CRITERIA 2: Strong away favorite
        elif a_xg - h_xg > 0.5 and a_prob > 0.50:
            prediction = "Away Win"
            confidence = int(a_prob * 100)
            reasons.append(f"Model gives away win {a_prob:.0%} probability (xG: {h_xg:.1f} vs {a_xg:.1f})")

        # CRITERIA 3: High scoring game
        elif total_xg > 2.8:
            prediction = "Over 2.5 Goals"
            confidence = min(int(total_xg * 30), 85)
            reasons.append(f"Combined xG of {total_xg:.1f} suggests a high-scoring match")

        # CRITERIA 4: Low scoring game
        elif total_xg < 2.2:
            prediction = "Under 2.5 Goals"
            confidence = min(int((3.0 - total_xg) * 40), 80)
            reasons.append(f"Combined xG of {total_xg:.1f} suggests a tight, low-scoring match")

        # CRITERIA 5: Both teams likely to score
        elif h_xg > 1.1 and a_xg > 1.1:
            prediction = "BTTS Yes"
            confidence = min(int(((h_xg + a_xg) / 3) * 40), 80)
            reasons.append(f"Both teams show strong attacking xG ({h_xg:.1f} and {a_xg:.1f})")

        # CRITERIA 6: Double chance home (safe pick)
        elif h_prob > 0.50 and d_prob > 0.25:
            prediction = "1X"
            confidence = int((h_prob + d_prob) * 100)
            reasons.append(f"Home win {h_prob:.0%} + draw {d_prob:.0%} = strong double chance")

        # CRITERIA 7: Double chance away
        elif a_prob > 0.50 and d_prob > 0.25:
            prediction = "X2"
            confidence = int((a_prob + d_prob) * 100)
            reasons.append(f"Away win {a_prob:.0%} + draw {d_prob:.0%} = strong double chance")

        # CRITERIA 8: Draw likely
        elif d_prob > 0.30 and abs(h_xg - a_xg) < 0.3:
            prediction = "Draw"
            confidence = int(d_prob * 100)
            reasons.append(f"Teams evenly matched (xG diff: {abs(h_xg - a_xg):.1f}), draw probability {d_prob:.0%}")

        # If no strong signal, skip
        if not prediction or confidence < 55:
            return None

        # Adjust confidence with H2H
        if match.h2h_home_wins is not None:
            h2h_total = (match.h2h_home_wins or 0) + (match.h2h_draws or 0) + (match.h2h_away_wins or 0)
            if h2h_total > 0:
                if prediction == "Home Win" and match.h2h_home_wins > match.h2h_away_wins:
                    confidence += 5
                    reasons.append(f"H2H favors home ({match.h2h_home_wins}-{match.h2h_draws}-{match.h2h_away_wins})")
                elif prediction == "Away Win" and match.h2h_away_wins > match.h2h_home_wins:
                    confidence += 5
                    reasons.append(f"H2H favors away ({match.h2h_home_wins}-{match.h2h_draws}-{match.h2h_away_wins})")

        # Adjust confidence with form
        if match.home_form:
            home_wins = match.home_form.count("W")
            if prediction in ("Home Win", "1X") and home_wins >= 3:
                confidence += 5
                reasons.append(f"Home form strong: {match.home_form}")

        if match.away_form:
            away_wins = match.away_form.count("W")
            if prediction in ("Away Win", "X2") and away_wins >= 3:
                confidence += 5
                reasons.append(f"Away form strong: {match.away_form}")

        # Cap confidence
        confidence = min(confidence, 95)

        # Set realistic odds based on prediction type
        odds_map = {
            "Home Win": decimal.Decimal("1.75"),
            "Away Win": decimal.Decimal("2.40"),
            "Draw": decimal.Decimal("3.40"),
            "Over 2.5 Goals": decimal.Decimal("1.85"),
            "Under 2.5 Goals": decimal.Decimal("1.90"),
            "BTTS Yes": decimal.Decimal("1.80"),
            "BTTS No": decimal.Decimal("2.00"),
            "1X": decimal.Decimal("1.25"),
            "X2": decimal.Decimal("1.35"),
            "12": decimal.Decimal("1.30"),
        }
        odds = odds_map.get(prediction, decimal.Decimal("1.85"))

        # Override with bookmaker odds if available and close
        if prediction == "Home Win" and bm_home:
            odds = decimal.Decimal(str(bm_home))
        elif prediction == "Away Win" and bm_away:
            odds = decimal.Decimal(str(bm_away))
        elif prediction == "Draw" and bm_draw:
            odds = decimal.Decimal(str(bm_draw))

        return {
            "prediction": prediction,
            "odds": odds,
            "confidence": confidence,
            "reasoning": " | ".join(reasons),
        }

    # ── HELPERS ──
    def _fetch_h2h(self, base_url, headers, match, home_team, away_team):
        try:
            r = requests.get(
                f"{base_url}/fixtures",
                headers=headers,
                params={"h2h": f"{home_team.id}-{away_team.id}", "last": 10},
                timeout=10,
            )
            data = r.json()
            fixtures = data.get("response", [])

            hw = dr = aw = 0
            for f in fixtures:
                hg = f["goals"]["home"]
                ag = f["goals"]["away"]
                if hg is None or ag is None:
                    continue
                if hg > ag:
                    hw += 1
                elif hg < ag:
                    aw += 1
                else:
                    dr += 1

            match.h2h_home_wins = hw
            match.h2h_draws = dr
            match.h2h_away_wins = aw
            match.save()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  H2H failed: {e}"))

    def _fetch_form(self, base_url, headers, match, team, is_home=True):
        try:
            r = requests.get(
                f"{base_url}/fixtures",
                headers=headers,
                params={"team": team.id, "last": 5},
                timeout=10,
            )
            data = r.json()
            fixtures = data.get("response", [])

            form = ""
            for f in reversed(fixtures):
                hg = f["goals"]["home"]
                ag = f["goals"]["away"]
                if hg is None or ag is None:
                    continue
                is_h = f["teams"]["home"]["name"] == team.name
                tg = hg if is_h else ag
                og = ag if is_h else hg
                form += "W" if tg > og else ("L" if tg < og else "D")

            if is_home:
                match.home_form = form
            else:
                match.away_form = form
            match.save()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Form failed: {e}"))

    def _fetch_odds(self, base_url, headers, match, fixture_id):
        try:
            r = requests.get(
                f"{base_url}/odds",
                headers=headers,
                params={"fixture": fixture_id},
                timeout=10,
            )
            data = r.json()
            for item in data.get("response", []):
                for bookmaker in item.get("bookmakers", []):
                    for market in bookmaker.get("bets", []):
                        if market.get("name") == "Match Winner":
                            vals = {v["value"]: float(v["odd"]) for v in market.get("values", [])}
                            match.bookmaker_odds_home = vals.get("Home")
                            match.bookmaker_odds_draw = vals.get("Draw")
                            match.bookmaker_odds_away = vals.get("Away")
                            match.save()
                            return
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Odds failed: {e}"))