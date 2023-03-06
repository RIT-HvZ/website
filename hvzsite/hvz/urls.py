from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView

from . import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)

urlpatterns = [
    path('player/<player_id>/', views.player_view),
    path('me/', views.me),
    path('team/<team_name>/', views.team_view),
    path('players/', views.players),
    path('teams/', views.teams),
    path('api/players', views.players_api),
    path('api/teams', views.teams_api),
    path('api/', include(router.urls)),
    path('tag/', views.tag),
    path('av/', views.av),
    path('blasterapproval/', views.blasterapproval),
    path('missions/', views.missions_view),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('', views.index),
    path('logout', LogoutView.as_view()),
    path('admin/create-av', views.admin_create_av),
    path('admin/create-body-armor', views.admin_create_body_armor),
    path('api/player_activation_api', views.player_activation_api),
    path('player_activation/', views.player_activation),
    path('api/player_activation_rest', views.player_activation_rest),
    path('rules/', views.rules),
    path('admin/player_admin/tools/<player_id>/<command>', views.player_admin_tools),
    path('admin/bodyarmors', views.bodyarmors),
    path('admin/bodyarmor/<armor_id>/', views.bodyarmor_view),
]
