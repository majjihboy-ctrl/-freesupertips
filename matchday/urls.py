from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from predictions.sitemaps import PredictionSitemap, StaticViewSitemap, TipsListSitemap
from predictions.views import RateLimitedLoginView, service_worker, web_manifest, cron_cleanup_matches

sitemaps = {
    "predictions": PredictionSitemap,
    "static": StaticViewSitemap,
    "tips_list": TipsListSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    # Override the default LoginView from django.contrib.auth.urls with a
    # rate-limited version; must be listed before the include() below so
    # it takes precedence.
    path("accounts/login/", RateLimitedLoginView.as_view(), name="login"),
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
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
]
