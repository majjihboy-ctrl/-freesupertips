from urllib.parse import quote
import re
import random
from collections import Counter
from itertools import groupby

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Prefetch, Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.core.cache import cache
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.decorators.cache import never_cache
from datetime import datetime, timedelta
from django_ratelimit.decorators import ratelimit

from .models import Prediction, Profile, Match, VIPCode
from .market_picks import extract_market_candidates
from .forms import CustomUserCreationForm

import logging

logger = logging.getLogger(__name__)


def _fetch_consensus_odds(event_external_id, market, outcome, timeout=4):
    """Best-effort consensus decimal odds from Bzzoiro. Returns float or None."""
    if not event_external_id or not market or not outcome:
        return None
    api_key = getattr(settings, "BZZOIRO_API_KEY", "") or ""
    if not api_key:
        return None
    try:
        import requests
        resp = requests.get(
            "https://sports.bzzoiro.com/api/v2/odds/",
            headers={"Authorization": f"Token {api_key}"},
            params={
                "event_id": event_external_id,
                "market": market,
                "outcome": outcome,
                "limit": 5,
            },
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        rows = (resp.json() or {}).get("results") or []
        prices = []
        for row in rows:
            price = row.get("decimal_odds")
            if price is not None:
                try:
                    prices.append(float(price))
                except (TypeError, ValueError):
                    pass
        if not prices:
            return None
        return round(sum(prices) / len(prices), 2)
    except Exception:
        logger.debug("consensus odds fetch failed", exc_info=True)
        return None



from django.contrib.auth.views import LoginView, PasswordResetView
from django.utils.decorators import method_decorator


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="post")
class RateLimitedLoginView(LoginView):
    """Same as Django's default LoginView, but rate-limited per IP to
    reduce brute-force login attempts, plus an optional "remember me"
    that shortens the session to browser-close when unchecked."""
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.request.POST.get("remember_me"):
            self.request.session.set_expiry(0)  # expires on browser close
        messages.success(self.request, f"Welcome back, {self.request.user.username}!")
        return response


@method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True), name="post")
class RateLimitedPasswordResetView(PasswordResetView):
    """Same as Django's default PasswordResetView, but rate-limited per
    IP -- otherwise anyone can mail-bomb an arbitrary inbox by repeatedly
    submitting their email to this form."""


@never_cache
def service_worker(request):
    """Served from the site root (see matchday/urls.py) rather than
    /static/, so the SW's default control scope covers the whole site
    instead of just /static/predictions/, and outside collectstatic so
    its filename never gets hash-renamed by ManifestStaticFilesStorage."""
    path = settings.BASE_DIR / "predictions" / "static" / "predictions" / "sw.js"
    return HttpResponse(path.read_text(), content_type="application/javascript")


@never_cache
def web_manifest(request):
    """Generated at request time so icon URLs always match whatever
    hashed filenames collectstatic actually produced, instead of the
    hardcoded paths a static manifest.json can't keep in sync with."""
    manifest = {
        "name": "Matchday Pro",
        "short_name": "Matchday",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#16a34a",
        "icons": [
            {
                "src": staticfiles_storage.url("predictions/icon-192.png"),
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": staticfiles_storage.url("predictions/icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
    }
    return JsonResponse(manifest, content_type="application/manifest+json")


def robots_txt(request):
    """Generated at request time (rather than a static template) so the
    Sitemap: line always matches whatever domain is actually serving the
    request -- a hardcoded domain here would go stale the moment the
    site moves between a custom domain and Vercel's free domain."""
    sitemap_url = request.build_absolute_uri(reverse("django.contrib.sitemaps.views.sitemap"))
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@never_cache
def cron_cleanup_matches(request):
    """Triggered daily by Vercel Cron (see vercel.json). Vercel sends
    'Authorization: Bearer <CRON_SECRET>' automatically when CRON_SECRET is
    set as an env var -- reject anything that doesn't match so this can't
    be triggered by a random public request."""
    from io import StringIO
    from django.core.management import call_command

    expected = f"Bearer {settings.CRON_SECRET}" if settings.CRON_SECRET else None
    if not expected or request.headers.get("Authorization") != expected:
        return HttpResponse(status=401)

    out = StringIO()
    call_command("cleanup_old_matches", stdout=out)
    return HttpResponse(out.getvalue(), content_type="text/plain")


@never_cache
def cron_import_bzzoiro(request):
    """Triggered daily by Vercel Cron (see vercel.json). Same shared-secret
    check as cron_cleanup_matches -- see that docstring for why."""
    from io import StringIO
    from django.core.management import call_command

    expected = f"Bearer {settings.CRON_SECRET}" if settings.CRON_SECRET else None
    if not expected or request.headers.get("Authorization") != expected:
        return HttpResponse(status=401)

    out = StringIO()
    call_command("import_bzzoiro", stdout=out)
    return HttpResponse(out.getvalue(), content_type="text/plain")


def _vip_status(request):
    if not request.user.is_authenticated:
        return False
    if request.user.is_staff:
        return True
    try:
        return request.user.profile.is_vip_active
    except Profile.DoesNotExist:
        Profile.objects.create(user=request.user)
        return False


# Order controls diversity priority when building the accumulator: we try to
# fill one leg from each market type before doubling back to any type, so a
# 5-leg acca isn't just five 1X2 picks.
ACCA_MARKET_ORDER = ["match_result", "btts", "over_under", "corners", "draw_no_bet"]
ACCA_MIN_CONFIDENCE = 55


def _acca_candidates_for_match(prediction):
    """Given a Prediction with a populated `markets` JSON blob (from the
    Bzzoiro import), return every market on that match that clears the
    confidence floor, as (market_type, label, probability) tuples."""
    candidates = extract_market_candidates(
        prediction.markets, prediction.match.home_team, prediction.match.away_team
    )
    return [c for c in candidates if c[2] >= ACCA_MIN_CONFIDENCE]


def _build_accumulator(leg_count=7):
    """Picks up to `leg_count` legs for today's accumulator: one match
    per leg, diversified across market types where possible, every leg at
    or above ACCA_MIN_CONFIDENCE. Returns a list of dicts ready for the
    template, plus combined odds/probability."""
    today = timezone.localtime().date()
    day_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    day_end = day_start + timedelta(days=1)

    predictions = (
        Prediction.objects.filter(
            source="bzzoiro",
            match__kickoff__gte=day_start,
            match__kickoff__lt=day_end,
            match__status="scheduled",
        )
        .select_related("match", "match__league", "match__home_team", "match__away_team")
    )

    # market_type -> list of (prediction, market_type, label, prob), best first
    by_type = {t: [] for t in ACCA_MARKET_ORDER}
    for prediction in predictions:
        for market_type, label, prob in _acca_candidates_for_match(prediction):
            by_type.setdefault(market_type, []).append((prediction, market_type, label, prob))
    for market_type in by_type:
        by_type[market_type].sort(key=lambda row: -row[3])

    legs = []
    used_match_ids = set()

    def try_take(market_type):
        for prediction, m_type, label, prob in by_type.get(market_type, []):
            if prediction.match_id not in used_match_ids:
                used_match_ids.add(prediction.match_id)
                legs.append({"prediction": prediction, "market_type": m_type, "label": label, "probability": prob})
                return True
        return False

    # Pass 1: one leg per market type, in priority order, for diversity.
    for market_type in ACCA_MARKET_ORDER:
        if len(legs) >= leg_count:
            break
        try_take(market_type)

    # Pass 2: if we still need more legs, cycle through the types again
    # (a match can't be reused, but a market type can supply a 2nd leg).
    guard = 0
    while len(legs) < leg_count and guard < leg_count * len(ACCA_MARKET_ORDER):
        guard += 1
        progressed = False
        for market_type in ACCA_MARKET_ORDER:
            if len(legs) >= leg_count:
                break
            if try_take(market_type):
                progressed = True
        if not progressed:
            break

    combined_prob = 1.0
    combined_odds = 1.0
    for leg in legs:
        combined_prob *= leg["probability"] / 100
        implied_odds = 100 / leg["probability"]
        leg["odds"] = round(implied_odds, 2)
        combined_odds *= implied_odds

    return {
        "legs": legs,
        "combined_odds": round(combined_odds, 2) if legs else None,
        "combined_probability": round(combined_prob * 100) if legs else None,
        "is_complete": len(legs) == leg_count,
    }


def accumulator(request):
    """Daily accumulator — free to view. Aims for up to 7 legs (minimum useful
    set is 4 when enough high-confidence picks exist). Diversified markets.
    """
    is_vip = _vip_status(request)
    acca = _build_accumulator(leg_count=7)
    # Treat 4+ legs as a solid daily board; more legs (up to 7) when available
    n = len(acca.get("legs") or [])
    acca["is_complete"] = n >= 4
    return render(request, "predictions/accumulator.html", {
        **acca,
        "is_vip": is_vip,
        "leg_target": 7,
        "leg_min": 4,
    })


@never_cache
def home(request):
    data = _fixtures_context(request, "free", "home")

    today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    data["live_matches"] = Match.objects.filter(
        status="live",
    ).select_related("home_team", "away_team").order_by("-kickoff")[:10]

    data["banker"] = (
        Prediction.objects.filter(
            source="bzzoiro",
            match__kickoff__gte=today_start,
            match__kickoff__lt=today_end,
            match__status="scheduled",
        )
        .select_related("match", "match__league", "match__home_team", "match__away_team")
        .order_by("-confidence")
        .first()
    )

    data["is_vip"] = _vip_status(request)
    return render(request, "predictions/home.html", data)


# Day tabs shown above the tips list. Keys are what's passed on the
# "?day=" query string; "today" is the default when it's absent/invalid.
_DAY_OFFSETS = {
    "today": 0,
    "tomorrow": 1,
    "day2": 2,
    "day3": 3,
    "day4": 4,
    "day5": 5,
    "day6": 6,
}
_DAY_LABELS = {0: "Today", 1: "Tomorrow"}


MARKET_TABS = [
    ("all", "All Markets"),
    ("match_result", "1X2"),
    ("btts", "BTTS"),
    ("over_under", "Over/Under"),
    ("corners", "Corners"),
    ("draw_no_bet", "Draw No Bet"),
    ("score", "Correct Score"),
]


def _market_pick_for(prediction, market_type):
    """Re-derives the pick for one specific market family from a
    Prediction's stored `markets` JSON, instead of whichever market was
    globally best for that match. Returns (label, probability, odds) or
    None if that match has no data for this market."""
    if market_type == "score":
        line = (prediction.markets or {}).get("score", {}).get("most_likely")
        return (f"Correct Score: {line}", None, None) if line else None

    candidates = extract_market_candidates(
        prediction.markets, prediction.match.home_team, prediction.match.away_team
    )
    match = next((c for c in candidates if c[0] == market_type), None)
    if not match:
        return None
    _, label, probability = match
    odds = round(100 / probability, 2) if probability else None
    return (label, probability, odds)


def _fixtures_context(request, tip_type, tabs_url_name, tabs_url_args=None):
    """Builds the day-tabs + market-tabs + fixtures list shared by the
    homepage and (for VIP, if ever reinstated) tips_list. tabs_url_name/
    tabs_url_args control which URL the tab links point back to, since the
    homepage and tips_list use different routes."""
    tabs_url_args = tabs_url_args or []

    day_param = request.GET.get("day", "today")
    if day_param not in _DAY_OFFSETS:
        day_param = "today"
    offset = _DAY_OFFSETS[day_param]

    market_param = request.GET.get("market", "all")
    if market_param not in dict(MARKET_TABS):
        market_param = "all"

    today = timezone.localdate()
    active_date = today + timedelta(days=offset)
    active_day_label = _DAY_LABELS.get(offset, active_date.strftime("%A"))

    base_url = reverse(tabs_url_name, args=tabs_url_args)
    day_tabs = [
        {
            "url": f"{base_url}?day={key}&market={market_param}",
            "label": _DAY_LABELS.get(off, (today + timedelta(days=off)).strftime("%a %d")),
            "active": key == day_param,
        }
        for key, off in _DAY_OFFSETS.items()
    ]
    market_tabs = [
        {
            "url": f"{base_url}?day={day_param}&market={key}",
            "label": label,
            "active": key == market_param,
        }
        for key, label in MARKET_TABS
    ]

    cache_key = f"predictions_list_v4_{tip_type}_{day_param}_{market_param}"
    fixtures = cache.get(cache_key)
    if fixtures is None:
        day_start = timezone.make_aware(datetime.combine(active_date, datetime.min.time()))
        day_end = day_start + timedelta(days=1)

        matches = (
            Match.objects.filter(kickoff__gte=day_start, kickoff__lt=day_end)
            .select_related("league", "home_team", "away_team")
            .prefetch_related(
                Prefetch(
                    "predictions",
                    queryset=Prediction.objects.filter(tip_type=tip_type).order_by("-confidence", "-created_at"),
                    to_attr="matching_tips",
                )
            )
            .order_by("kickoff")
        )

        fixtures = []
        for match in matches:
            tips = match.matching_tips
            if not tips:
                continue
            if market_param == "all":
                # Always surface the highest-confidence tip for the match.
                top_tip = tips[0]  # queryset already ordered by -confidence
                # Value filter: skip weak picks on the free list
                if top_tip.confidence is not None and top_tip.confidence < 58:
                    continue
                fixtures.append({"match": match, "top_tip": top_tip, "tips_count": len(tips)})
                continue
            top_tip = tips[0]
            picked = _market_pick_for(top_tip, market_param)
            if picked is None:
                continue  # this match has no data for the selected market -- not a "low score" exclusion, just missing data
            label, probability, odds = picked
            fixtures.append({
                "match": match,
                "top_tip": top_tip,
                "tips_count": len(tips),
                "market_override": {"label": label, "probability": probability, "odds": odds},
            })

        cache.set(cache_key, fixtures, 120)

    def _conf(f):
        if f.get("market_override") and f["market_override"].get("probability") is not None:
            return f["market_override"]["probability"]
        tip = f.get("top_tip")
        return (tip.confidence if tip and tip.confidence is not None else 0)

    # Strongest tips first within each league
    fixtures.sort(key=lambda f: (-_conf(f), f["match"].kickoff))

    fixtures_by_league = [
        {"league": league, "fixtures": list(group)}
        for league, group in groupby(
            sorted(fixtures, key=lambda f: (f["match"].league.name, -_conf(f))),
            key=lambda f: f["match"].league,
        )
    ]

    league_counts = sorted(
        Counter(f["match"].league for f in fixtures).items(),
        key=lambda kv: kv[0].name,
    )

    return {
        "fixtures": fixtures,
        "fixtures_by_league": fixtures_by_league,
        "tip_type": tip_type,
        "day_tabs": day_tabs,
        "market_tabs": market_tabs,
        "market_param": market_param,
        "active_date": active_date,
        "active_day_label": active_day_label,
        "league_counts": league_counts,
    }


def tips_list(request, tip_type):
    if tip_type not in ("free", "vip"):
        return redirect("home")

    # VIP singles are retired — individual tips are free for everyone.
    # The VIP product is the Accumulator only. Always serve free tips here
    # so the bottom-nav "Tips" tab works for all users.
    if tip_type == "vip":
        query = request.META.get("QUERY_STRING", "")
        return redirect(f"{reverse('tips_list', args=['free'])}{'?' + query if query else ''}")

    context = _fixtures_context(request, "free", "tips_list", tabs_url_args=["free"])
    context["is_vip"] = _vip_status(request)
    context["tip_type"] = "free"
    return render(request, "predictions/tips_list.html", context)


def match_tips(request, tip_type, match_id):
    if tip_type not in ("free", "vip"):
        return redirect("home")

    if tip_type == "vip" and not _vip_status(request):
        messages.info(request, "VIP access is required to view these tips.")
        return redirect("upgrade")

    match = get_object_or_404(
        Match.objects.select_related("league", "home_team", "away_team"), pk=match_id
    )
    predictions = list(match.predictions.filter(tip_type=tip_type).order_by("-created_at"))
    if not predictions:
        raise Http404("No tips for this match.")

    board = []
    primary = predictions[0] if predictions else None
    if primary and primary.markets:
        from .market_picks import board_rows
        board = board_rows(
            primary.markets,
            str(match.home_team),
            str(match.away_team),
        )

    # Model vs market comparison for the primary pick
    market_odds = None
    model_odds = None
    value_edge = None
    if primary:
        from .market_picks import model_implied_odds, map_pick_to_odds_query, is_value_pick
        model_odds = model_implied_odds(primary.confidence)
        mkt, outcome = map_pick_to_odds_query(
            primary.market_type,
            primary.prediction,
            str(match.home_team),
            str(match.away_team),
        )
        market_odds = _fetch_consensus_odds(match.external_id, mkt, outcome)
        if market_odds and model_odds and market_odds > 1 and model_odds > 1:
            # Positive edge when book pays more than model-implied fair price
            value_edge = round(market_odds - model_odds, 2)

    return render(request, "predictions/match_tips.html", {
        "match": match,
        "predictions": predictions,
        "tip_type": tip_type,
        "is_vip": _vip_status(request),
        "market_board": board,
        "model_odds": model_odds,
        "market_odds": market_odds,
        "value_edge": value_edge,
        "is_value": bool(primary and primary.confidence and primary.confidence >= 70),
    })


def tip_detail(request, pk):
    prediction = get_object_or_404(
        Prediction.objects.select_related("match", "match__league", "match__home_team", "match__away_team"),
        pk=pk,
    )
    is_vip = _vip_status(request)

    if prediction.tip_type == "vip" and not is_vip:
        messages.error(request, "This is a VIP tip. Upgrade to unlock.")
        return redirect("upgrade")

    return render(request, "predictions/tip_detail.html", {
        "prediction": prediction,
        "is_vip": is_vip,
    })


def _grade_prediction(prediction, home_score, away_score):
    """Returns (actual_result_label, was_hit) for a finished match, graded
    according to the prediction's own market_type -- a BTTS pick and a
    match_result pick need different logic to know what "correct" means."""
    market_type = prediction.market_type or "match_result"
    home_team = prediction.match.home_team
    away_team = prediction.match.away_team

    if market_type == "btts":
        actual = "BTTS: Yes" if (home_score > 0 and away_score > 0) else "BTTS: No"
        return actual, prediction.prediction == actual

    if market_type == "over_under":
        # prediction text is always "Over X Goals" (see market_picks.py --
        # we only ever generate Over candidates, never Under).
        match_line = re.search(r"Over ([\d.]+) Goals", prediction.prediction)
        if not match_line:
            return "—", None
        line = float(match_line.group(1))
        total_goals = home_score + away_score
        actual = f"{total_goals} goals"
        return actual, total_goals > line

    if market_type == "draw_no_bet":
        if home_score == away_score:
            return "Draw (push)", None  # neither a hit nor a miss -- stake refunded in real DNB betting
        winner = str(home_team) if home_score > away_score else str(away_team)
        actual = f"Draw No Bet: {winner}"
        return actual, prediction.prediction == actual

    if market_type == "corners":
        # We don't store final corner counts anywhere, so there's no ground
        # truth to grade this against.
        return "Not tracked", None

    # match_result (the default/fallback)
    if home_score > away_score:
        actual = "Home Win"
    elif home_score < away_score:
        actual = "Away Win"
    else:
        actual = "Draw"
    return actual, prediction.prediction == actual


def results(request):
    """Public accuracy history: our last N days of model-sourced picks on
    finished matches, marked hit/miss according to each pick's own market
    type. Manual predictions aren't included since we don't have a
    structured way to score arbitrary tip text against a final score."""
    lookback_days = 30
    since = timezone.now() - timedelta(days=lookback_days)

    predictions = list(
        Prediction.objects.filter(
            source="bzzoiro",
            match__status="finished",
            match__kickoff__gte=since,
            match__home_score__isnull=False,
            match__away_score__isnull=False,
        )
        .exclude(market_type="corners")  # no stored ground truth to grade against
        .select_related("match", "match__league", "match__home_team", "match__away_team")
        .order_by("-match__kickoff")[:200]
    )

    for p in predictions:
        actual, was_hit = _grade_prediction(p, p.match.home_score, p.match.away_score)
        p.actual_result = actual
        p.was_hit = was_hit

    # "push" results (was_hit is None, e.g. a Draw No Bet on an actual draw)
    # don't count toward the hit rate either way.
    gradeable = [p for p in predictions if p.was_hit is not None]
    hits = sum(1 for p in gradeable if p.was_hit)
    total = len(gradeable)
    hit_rate = round((hits / total) * 100) if total else None

    # Breakdown by market type
    by_market = {}
    for p in gradeable:
        key = p.market_type or "other"
        bucket = by_market.setdefault(key, {"hits": 0, "total": 0})
        bucket["total"] += 1
        if p.was_hit:
            bucket["hits"] += 1
    market_stats = []
    labels = {
        "match_result": "1X2",
        "btts": "BTTS",
        "over_under": "Over/Under",
        "draw_no_bet": "Draw No Bet",
        "corners": "Corners",
        "score": "Correct Score",
        "other": "Other",
    }
    for key, bucket in sorted(by_market.items(), key=lambda kv: -kv[1]["total"]):
        t = bucket["total"]
        h = bucket["hits"]
        market_stats.append({
            "key": key,
            "label": labels.get(key, key.replace("_", " ").title()),
            "hits": h,
            "total": t,
            "hit_rate": round((h / t) * 100) if t else None,
        })

    return render(request, "predictions/results.html", {
        "predictions": predictions,
        "hits": hits,
        "total": total,
        "hit_rate": hit_rate,
        "lookback_days": lookback_days,
        "market_stats": market_stats,
    })


def upgrade(request):
    whatsapp_url = None
    if request.user.is_authenticated and settings.WHATSAPP_NUMBER:
        message = (
            "Hi! I'd like to get VIP access on Matchday Pro "
            f"(username: {request.user.username})."
        )
        whatsapp_url = f"https://wa.me/{settings.WHATSAPP_NUMBER}?text={quote(message)}"

    return render(request, "predictions/upgrade.html", {
        "whatsapp_url": whatsapp_url,
    })


@login_required
def profile_view(request):
    return render(request, "predictions/profile.html", {})


@login_required
@ratelimit(key="user", rate="10/h", block=True)
def redeem_vip_code(request):
    if request.method != "POST":
        return redirect("upgrade")

    raw_code = request.POST.get("code", "").strip().upper()
    if not raw_code:
        messages.error(request, "Enter a code first.")
        return redirect("upgrade")

    try:
        vip_code = VIPCode.objects.get(code=raw_code)
    except VIPCode.DoesNotExist:
        messages.error(request, "That code isn't valid. Double-check it and try again.")
        return redirect("upgrade")

    if vip_code.is_used:
        messages.error(request, "That code has already been used.")
        return redirect("upgrade")

    profile = request.user.profile
    now = timezone.now()
    # Extend from the current expiry if VIP is still active, otherwise
    # start the clock from now.
    base = profile.vip_expires_at if profile.is_vip_active and profile.vip_expires_at else now
    profile.is_vip = True
    profile.vip_expires_at = base + timedelta(days=vip_code.duration_days)
    profile.save()

    vip_code.is_used = True
    vip_code.used_by = request.user
    vip_code.used_at = now
    vip_code.save()

    messages.success(
        request,
        f"VIP activated! You now have access until "
        f"{timezone.localtime(profile.vip_expires_at).strftime('%B %d, %Y')}.",
    )
    return redirect("home")


def _send_verification_email(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = request.build_absolute_uri(
        reverse("verify_email", args=[uidb64, token])
    )
    send_mail(
        subject="Confirm your Matchday Pro account",
        message=(
            f"Hi {user.username},\n\n"
            "Click the link below to confirm your email and activate your "
            "Matchday Pro account:\n\n"
            f"{verify_url}\n\n"
            "If you didn't sign up for Matchday Pro, you can ignore this email."
        ),
        from_email=None,  # falls back to DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
        fail_silently=False,
    )


@ratelimit(key="ip", rate="5/h", block=True)
def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Inactive until they click the emailed confirmation link --
            # Django's own login form already refuses inactive users, so
            # this alone blocks a bot/spam signup from doing anything on
            # the site until a real inbox has confirmed the address.
            user.is_active = False
            user.save()
            _send_verification_email(request, user)
            return redirect("check_email")
    else:
        form = CustomUserCreationForm()
    return render(request, "predictions/register.html", {"form": form})


def check_email(request):
    return render(request, "predictions/check_email.html")


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and not user.is_active and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Email confirmed! Welcome to Matchday Pro.")
        return redirect("home")

    messages.error(
        request,
        "That confirmation link is invalid or has expired. "
        "Request a new one below.",
    )
    return redirect("resend_verification")


@ratelimit(key="ip", rate="5/h", block=True)
def resend_verification(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        try:
            user = User.objects.get(email__iexact=email, is_active=False)
            _send_verification_email(request, user)
        except User.DoesNotExist:
            # Don't reveal whether the address is registered.
            pass
        messages.success(
            request,
            "If that email is awaiting confirmation, a new link has been sent.",
        )
        return redirect("check_email")
    return render(request, "predictions/resend_verification.html")
