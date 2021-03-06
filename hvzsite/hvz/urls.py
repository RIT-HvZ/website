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
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('', views.index),
    path('accounts/', include('allauth.urls')),
    path('logout', LogoutView.as_view()),
]