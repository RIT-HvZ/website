from django.urls import path, re_path, include
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView

from . import views
#from rest_framework import routers
from rest_framework.schemas import get_schema_view

# router = routers.DefaultRouter()
# router.register(r'users', views.UserViewSet)
# router.register(r'groups', views.GroupViewSet)

urlpatterns = [
    # Primary Game View Routes
    re_path(r'^player/(?P<player_id>[^/]+)/?$', views.player_view),
    re_path(r'^me/?$', views.me),
    re_path(r'^team/(?P<team_name>[^/]+)/?$', views.team_view),
    re_path(r'^players/?$', views.players),
    re_path(r'^report/?$', views.create_report),
    re_path(r'^teams/?$', views.teams),
    re_path(r'^tag/?$', views.tag),
    re_path(r'^av/?$', views.av),
    re_path(r'^blasterapproval/?$', views.blasterapproval),
    re_path(r'^missions/?$', views.missions_view),
    re_path(r'^api-auth/?', include('rest_framework.urls', namespace='rest_framework')),
    path(r'', views.index),
    re_path(r'^logout/?$', LogoutView.as_view()),
    re_path(r'^rules/?$', views.rules),
    re_path(r'^infections/?$', views.infection),

    # Activation Routes
    re_path(r'^player_activation/?$', views.player_activation),
    re_path(r'^api/player_activation_api/?$', views.player_activation_api),
    re_path(r'^api/player_activation_rest/?$', views.player_activation_rest),

    # Admin Routes
    re_path(r'^admin/create-av/?$', views.admin_create_av),
    re_path(r'^admin/create-body-armor/?$', views.admin_create_body_armor),
    re_path(r'^admin/player_admin/tools/(?P<player_id>[^/]+)/(?P<command>[^/]+)/?$', views.player_admin_tools),
    re_path(r'^admin/bodyarmors/?$', views.bodyarmors),
    re_path(r'^admin/bodyarmor/(?P<armor_id>[^/]+)/?$', views.bodyarmor_view),
    re_path(r'^admin/editmissions/?$', views.editmissions),
    re_path(r'^admin/editmission/(?P<mission_id>[^/]+)/?$', views.editmission),
    re_path(r'^admin/editpostgamesurvey/(?P<postgamesurvey_id>[^/]+)/?$', views.editpostgamesurvey),
    re_path(r'^admin/editpostgamesurveys/?$', views.editpostgamesurveys),
    re_path(r'^admin/reports/?$', views.reports),
    re_path(r'^admin/report/(?P<report_id>[^/]+)/?$', views.report),
    re_path(r'^admin/update_rules/?$', views.rules_update),
    re_path(r'^admin/print/?$', views.print_ids),
    re_path(r'^admin/print_preview/?$', views.print_preview),
    re_path(r'^admin/mark_printed/?$', views.mark_printed),

    # API Routes
    # re_path(r'^api/?', include(router.urls)),
    re_path(r'^api/discord-id/?$', views.ApiDiscordId.as_view()),
    re_path(r'^api/player/?$', views.ApiPlayerId.as_view()),
    re_path(r'^api/teams/?$', views.ApiTeams.as_view()),
    re_path(r'^api/players/?$', views.ApiPlayers.as_view()),
    re_path(r'^api/tag/?$', views.ApiTag.as_view()),
    re_path(r'^api/missions/?$', views.ApiMissions.as_view()),
    re_path(r'^api/reports/?$', views.ApiReports.as_view()),
    re_path(r'^api/create-av/?$', views.ApiCreateAv.as_view()),
    re_path(r'^api/create-armor/?$', views.ApiCreateBodyArmor.as_view()),

    # Api Documentation
    re_path(r'^openapi/?$', get_schema_view(
            title="HvZ @ RIT API",
            description="API Endpoint descriptions for HvZ @ RIT Website",
            version="1.0.0"
        ), name='openapi-schema'),
    re_path(r'^swagger-ui/?$', TemplateView.as_view(
        template_name='swagger-ui.html',
        extra_context={'schema_url':'openapi-schema'}
    ), name='swagger-ui'),

    # API Data-Table Routes
    re_path(r'^api/datatables/players/?$', views.players_api),
    re_path(r'^api/datatables/teams/?$', views.teams_api),
]
