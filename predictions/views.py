from urllib.parse import quote

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.decorators.cache import never_cache
from datetime import datetime, timedelta
from django_ratelimit.decorators import ratelimit

from .models import Prediction, Profile, Match, VIPCode
from .forms import CustomUserCreationForm

import logging

logger = logging.getLogger(__name__)


from django.contrib.auth.views import LoginView
from django.utils.decorators import method_decorator


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="post")
class RateLimitedLoginView(LoginView):
    """Same as Django's default LoginView, but rate-limited per IP to
    reduce brute-force login attempts."""
    template_name = "registration/login.html"
    redirect_authenticated_user = True


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


def _vip_status(request):
    if not request.user.is_authenticated:
        return False
    try:
        return request.user.profile.is_vip_active
    except Profile.DoesNotExist:
        Profile.objects.create(user=request.user)
        return False


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

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    data["todays_matches"] = Match.objects.filter(
        kickoff__gte=today_start,
        kickoff__lt=today_end,
        status="scheduled",
    ).select_related("league", "home_team", "away_team").order_by("league__name", "kickoff")[:20]

    data["live_matches"] = Match.objects.filter(
        status="live",
    ).select_related("home_team", "away_team").order_by("-kickoff")[:10]

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

    cache_key = f"predictions_list_{tip_type}_{day_param}"
    fixtures = cache.get(cache_key)
    if fixtures is None:
        day_start = timezone.make_aware(datetime.combine(active_date, datetime.min.time()))
        day_end = day_start + timedelta(days=1)

        matches = (
            Match.objects.filter(kickoff__gte=day_start, kickoff__lt=day_end)
            .select_related("league", "home_team", "away_team")
            .order_by("kickoff")
        )

        fixtures = []
        for match in matches:
            tips_count = match.predictions.filter(tip_type=tip_type).count()
            if tips_count:
                fixtures.append({"match": match, "tips_count": tips_count})

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


@login_required
def upgrade(request):
    profile = request.user.profile

    whatsapp_url = None
    if settings.WHATSAPP_NUMBER:
        message = (
            "Hi! I'd like to get VIP access on Matchday Pro "
            f"(username: {request.user.username})."
        )
        whatsapp_url = f"https://wa.me/{settings.WHATSAPP_NUMBER}?text={quote(message)}"

    return render(request, "predictions/upgrade.html", {
        "profile": profile,
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


@ratelimit(key="ip", rate="5/h", block=True)
def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = CustomUserCreationForm()
    return render(request, "predictions/register.html", {"form": form})
