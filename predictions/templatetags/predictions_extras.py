from django import template
from django.templatetags.static import static as _static
import re

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def short_pick(label):
    """
    Compact market labels for mobile cards.
    'Draw No Bet: Internacional de Bogotá' -> 'DNB · Home' is not always possible
    without side context, so we shorten generically:
      Draw No Bet: Team Name  -> DNB · Team Name (truncated)
      Over 1.5 Goals          -> O1.5
      Over 2.5 Goals          -> O2.5
      BTTS: Yes / No          -> BTTS Yes / BTTS No
      Corners Over 9.5        -> Corners O9.5
      Home Win / Away Win / Draw stay as-is
    """
    if not label:
        return label
    text = str(label).strip()

    m = re.match(r"^Over\s+([\d.]+)\s+Goals$", text, re.I)
    if m:
        return f"O{m.group(1)}"

    m = re.match(r"^Under\s+([\d.]+)\s+Goals$", text, re.I)
    if m:
        return f"U{m.group(1)}"

    m = re.match(r"^Corners\s+Over\s+([\d.]+)$", text, re.I)
    if m:
        return f"Corners O{m.group(1)}"

    m = re.match(r"^BTTS:\s*(Yes|No)$", text, re.I)
    if m:
        return f"BTTS {m.group(1).title()}"

    m = re.match(r"^Draw No Bet:\s*(.+)$", text, re.I)
    if m:
        name = m.group(1).strip()
        # Prefer short last token if very long
        if len(name) > 14:
            parts = name.split()
            name = parts[-1] if parts else name[:12]
        return f"DNB · {name}"

    return text


@register.filter
def team_logo_url(team):
    """Bzzoiro public image proxy — no auth required."""
    if team is None:
        return ""
    ext = getattr(team, "external_id", None)
    if not ext:
        return ""
    return f"https://sports.bzzoiro.com/img/team/{ext}/?bg=transparent"


@register.filter
def league_logo_url(league):
    if league is None:
        return ""
    ext = getattr(league, "external_id", None)
    if not ext:
        return ""
    return f"https://sports.bzzoiro.com/img/league/{ext}/?bg=transparent"


@register.filter
def conf_tier(value):
    """CSS modifier for high-confidence picks."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    if v >= 80:
        return "is-hot"
    if v >= 70:
        return "is-strong"
    return ""



@register.simple_tag
def market_board(markets, home_name="Home", away_name="Away"):
    """Full probability board groups for match detail."""
    from predictions.market_picks import board_rows
    return board_rows(markets, home_name, away_name)


@register.simple_tag(takes_context=True)
def abs_static(context, path):
    """Absolute URL for a static file. Open Graph / Twitter card crawlers
    (Facebook, X, WhatsApp) ignore relative image URLs, so link previews
    need the full https://host/static/... form."""
    request = context.get("request")
    url = _static(path)
    return request.build_absolute_uri(url) if request else url


@register.simple_tag(takes_context=True)
def canonical_url(context):
    """Canonical URL = scheme + host + path, without the query string, so
    ?day=/?market=/tracking parameters don't each become their own page."""
    request = context.get("request")
    return request.build_absolute_uri(request.path) if request else ""


# BigCat's banner script loads synchronously and renders the same creative
# wherever it is placed, so we include it once per page and leave any further
# BigCat slots empty (the Mozzart slots are separate and unaffected).
_BIGCAT_VARIANTS = {"banner", "top", "mid", "button", "sidebar"}


@register.simple_tag(takes_context=True)
def aff_variant(context, variant):
    request = context.get("request")
    if variant not in _BIGCAT_VARIANTS or request is None:
        return variant
    if getattr(request, "_bigcat_rendered", False):
        return ""
    request._bigcat_rendered = True
    return variant
