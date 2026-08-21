from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from predictions.sitemaps import PredictionSitemap, StaticViewSitemap, TipsListSitemap
from predictions.views import (
    RateLimitedLoginView,
    RateLimitedPasswordResetView,
    service_worker,
    web_manifest,
    robots_txt,
    cron_cleanup_matches,
)

sitemaps = {
    "predictions": PredictionSitemap,
    "static": StaticViewSitemap,
    "tips_list": TipsListSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    # Override the default LoginView/PasswordResetView from
    # django.contrib.auth.urls with rate-limited versions; must be listed
    # before the include() below so they take precedence.
    path("accounts/login/", RateLimitedLoginView.as_view(), name="login"),
    path("accounts/password_reset/", RateLimitedPasswordResetView.as_view(), name="password_reset"),
    path("accounts/", include("django.contrib.auth.urls")),
    # Served from the root (not /static/) so the service worker's default
    # scope covers the whole site, and outside collectstatic so its
    # filename never gets hash-renamed by ManifestStaticFilesStorage.
    path("sw.js", service_worker, name="service_worker"),
    # Generated at request time so its icon URLs always match whatever
    # hashed filenames collectstatic actually produced.
    path("manifest.json", web_manifest, name="web_manifest"),
    # Hit daily by Vercel Cron (see vercel.json "crons") to delete matches
    # once their day has ended.
    path("cron/cleanup-matches/", cron_cleanup_matches, name="cron_cleanup_matches"),
    path("", include("predictions.urls")),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
]
