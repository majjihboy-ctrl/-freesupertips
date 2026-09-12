from urllib.parse import quote
import re

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


def _build_accumulator(leg_count=5):
    """Picks up to `leg_count` legs for today's VIP accumulator: one match
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
    is_vip = _vip_status(request)
    if not is_vip:
        messages.info(request, "The VIP Accumulator is a VIP-only feature. Upgrade to unlock it.")
        return redirect("upgrade")

    acca = _build_accumulator(leg_count=5)
    return render(request, "predictions/accumulator.html", {**acca, "is_vip": is_vip})


@never_cache
def home(request):
    cache_key = "home_page_data"
    data = cache.get(cache_key)
    if not data:
        featured_free = list(
            Prediction.objects.filter(tip_type="free")
            .select_related("match", "match__league", "match__home_team", "match__away_team")
            .order_by("-created_at")[:5]
        )
        vip_teaser = list(
            Prediction.objects.filter(tip_type="vip")
            .select_related("match", "match__league", "match__home_team", "match__away_team")
            .order_by("-created_at")[:3]
        )

        data = {
            "featured_free": featured_free,
            "vip_teaser": vip_teaser,
        }
        cache.set(cache_key, data, 300)

    today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    data["todays_matches"] = Match.objects.filter(
        kickoff__gte=today_start,
        kickoff__lt=today_end,
        status="scheduled",
    ).select_related("league", "home_team", "away_team").prefetch_related(
        Prefetch(
            "predictions",
            queryset=Prediction.objects.filter(tip_type="free").order_by("-created_at"),
            to_attr="free_tips",
        )
    ).annotate(
        # Count only -- never prefetch the actual VIP Prediction objects
        # into this public view, so there's no way for the VIP market/odds
        # to leak into the page source for a non-VIP visitor.
        vip_tips_count=Count("predictions", filter=Q(predictions__tip_type="vip")),
    ).order_by("league__name", "kickoff")[:20]

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
_DAY_OFFSETS = {"today": 0, "tomorrow": 1, "day_after": 2}
_DAY_LABELS = {0: "Today", 1: "Tomorrow"}


def tips_list(request, tip_type):
    if tip_type not in ("free", "vip"):
        return redirect("home")

    if tip_type == "vip" and not _vip_status(request):
        messages.info(request, "VIP access is required to view these tips.")
        return redirect("upgrade")

    day_param = request.GET.get("day", "today")
    if day_param not in _DAY_OFFSETS:
        day_param = "today"
    offset = _DAY_OFFSETS[day_param]

    today = timezone.localdate()
    active_date = today + timedelta(days=offset)
    active_day_label = _DAY_LABELS.get(offset, active_date.strftime("%A"))

    day_tabs = [
        {
            "url": f"{reverse('tips_list', args=[tip_type])}?day={key}",
            "label": _DAY_LABELS.get(off, (today + timedelta(days=off)).strftime("%a %d")),
            "active": key == day_param,
        }
        for key, off in _DAY_OFFSETS.items()
    ]

    cache_key = f"predictions_list_v2_{tip_type}_{day_param}"
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
            if tips:
                fixtures.append({"match": match, "top_tip": tips[0], "tips_count": len(tips)})

        cache.set(cache_key, fixtures, 120)

    return render(request, "predictions/tips_list.html", {
        "fixtures": fixtures,
        "tip_type": tip_type,
        "day_tabs": day_tabs,
        "active_date": active_date,
        "active_day_label": active_day_label,
        "is_vip": _vip_status(request),
    })


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

    return render(request, "predictions/match_tips.html", {
        "match": match,
        "predictions": predictions,
        "tip_type": tip_type,
        "is_vip": _vip_status(request),
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
    lookback_days = 14
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

    return render(request, "predictions/results.html", {
        "predictions": predictions,
        "hits": hits,
        "total": total,
        "hit_rate": hit_rate,
        "lookback_days": lookback_days,
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
