from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Prediction


class PredictionSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Prediction.objects.all()

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return reverse("tip_detail", args=[obj.pk])


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "weekly"

    def items(self):
        # "tips_list" requires a tip_type arg, so it's listed separately
        # below via TipsListSitemap rather than here.
        return ["home"]

    def location(self, item):
        return reverse(item)


class TipsListSitemap(Sitemap):
    priority = 0.5
    changefreq = "daily"

    def items(self):
        return ["free", "vip"]

    def location(self, tip_type):
        return reverse("tips_list", args=[tip_type])