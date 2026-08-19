from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("tips/<str:tip_type>/", views.tips_list, name="tips_list"),
    path("tips/<str:tip_type>/match/<int:match_id>/", views.match_tips, name="match_tips"),
    path("tips/detail/<int:pk>/", views.tip_detail, name="tip_detail"),
    path("upgrade/", views.upgrade, name="upgrade"),
    path("upgrade/redeem/", views.redeem_vip_code, name="redeem_vip_code"),
    path("register/", views.register, name="register"),
]