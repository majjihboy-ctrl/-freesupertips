from django.contrib import admin
from django.utils.html import format_html
from django.core.cache import cache
from .models import League, Team, Match, Profile, Prediction, VIPCode


def _invalidate_prediction_caches():
    """Clear cached pages whose data depends on Prediction content."""
    cache.delete("home_page_data")
    for tip_type in ("free", "vip"):
        for day in ("today", "tomorrow", "day_after"):
            cache.delete(f"predictions_list_{tip_type}_{day}")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "is_vip", "vip_expires_at"]
    list_filter = ["is_vip"]
    list_editable = ["is_vip"]
    search_fields = ["user__username"]
    actions = ["grant_vip_30_days"]

    @admin.action(description="Grant VIP for 30 days")
    def grant_vip_30_days(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        for profile in queryset:
            profile.is_vip = True
            profile.vip_expires_at = timezone.now() + timedelta(days=30)
            profile.save()
        self.message_user(request, f"VIP granted to {queryset.count()} user(s).")


@admin.register(VIPCode)
class VIPCodeAdmin(admin.ModelAdmin):
    """Generate codes here (leave 'code' blank and save -- it self-fills),
    hand them out manually (e.g. over WhatsApp) after payment is arranged,
    then the customer redeems one on the Upgrade page."""

    list_display = ["code", "duration_days", "is_used", "used_by", "used_at", "created_at"]
    list_filter = ["is_used", "duration_days"]
    search_fields = ["code", "used_by__username"]
    readonly_fields = ["used_by", "used_at", "is_used"]
    fields = ["code", "duration_days", "is_used", "used_by", "used_at"]

    def has_change_permission(self, request, obj=None):
        # Codes are write-once by design (generated, then redeemed by the
        # system) -- prevent accidentally hand-editing a used/unused code
        # after the fact. Still viewable and deletable.
        return False


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ["name", "country"]
    list_filter = ["country"]
    search_fields = ["name", "country"]
    ordering = ["name"]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "short_name", "league"]
    list_filter = ["league__country", "league"]
    search_fields = ["name", "short_name", "league__name", "league__country"]
    list_per_page = 50
    autocomplete_fields = ["league"]


class PredictionInline(admin.TabularInline):
    model = Prediction
    extra = 1
    fields = ["tip_type", "prediction", "odds"]


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "kickoff",
        "status",
        "home_score",
        "away_score",
        "win_probs",
        "pick",
        "proj_score",
    ]
    list_filter = ["status", "league", "kickoff", "pick"]
    search_fields = ["home_team__name", "away_team__name"]
    list_editable = ["status", "home_score", "away_score"]
    date_hierarchy = "kickoff"
    list_per_page = 50
    actions = ["mark_finished"]
    autocomplete_fields = ["league", "home_team", "away_team"]
    inlines = [PredictionInline]

    fieldsets = (
        ("Fixture", {
            "fields": ("league", "home_team", "away_team", "kickoff", "status")
        }),
        ("Result", {
            "fields": ("home_score", "away_score"),
        }),
        ("Prediction (entered manually)", {
            "fields": (
                ("win_prob_home", "win_prob_draw", "win_prob_away"),
                "pick",
                ("proj_home_score", "proj_away_score"),
            ),
            "description": "Win probabilities should add up to roughly 100%. "
                            "Leave all blank to show this match as not yet "
                            "predicted on the site.",
        }),
    )

    @admin.display(description="Win Prob 1/X/2")
    def win_probs(self, obj):
        if obj.win_prob_home is None:
            return "—"
        return format_html(
            '<span style="color:#22c55e">{}%</span> / '
            '<span style="color:#f2b544">{}%</span> / '
            '<span style="color:#4d9fef">{}%</span>',
            obj.win_prob_home, obj.win_prob_draw, obj.win_prob_away,
        )

    @admin.display(description="Proj. Score")
    def proj_score(self, obj):
        if obj.proj_home_score is None or obj.proj_away_score is None:
            return "—"
        return f"{obj.proj_home_score}-{obj.proj_away_score}"

    @admin.action(description="Mark as FINISHED (enter scores first)")
    def mark_finished(self, request, queryset):
        updated = 0
        for match in queryset:
            if match.home_score is not None and match.away_score is not None:
                match.status = "finished"
                match.save()
                updated += 1
        self.message_user(request, f"Marked {updated} matches as finished.")


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ["match", "tip_type", "prediction", "odds", "created_at"]
    list_filter = ["tip_type", "created_at"]
    search_fields = ["prediction", "match__home_team__name", "match__away_team__name"]
    list_editable = ["tip_type", "prediction", "odds"]
    date_hierarchy = "created_at"
    list_per_page = 50
    autocomplete_fields = ["match"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _invalidate_prediction_caches()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        _invalidate_prediction_caches()

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        _invalidate_prediction_caches()