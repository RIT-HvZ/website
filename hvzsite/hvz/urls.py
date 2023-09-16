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
    re_path(r'^name-change/?$', views.name_change),
    re_path(r'^cancel_name_change/?$', views.cancel_name_change),
    re_path(r'^clan/(?P<clan_name>[^/]+)/?$', views.clan_view),
    re_path(r'^players/?$', views.players),
    re_path(r'^report/?$', views.create_report),
    re_path(r'^clans/?$', views.clans),
    re_path(r'^tag/?$', views.tag),
    re_path(r'^av/?$', views.av),
    re_path(r'^blasterapproval/?$', views.blasterapproval),
    re_path(r'^missions/?$', views.missions_view),
    re_path(r'^api-auth/?', include('rest_framework.urls', namespace='rest_framework')),
    path(r'', views.index),
    re_path(r'^logout/?$', LogoutView.as_view()),
    re_path(r'^rules/?$', views.rules),
    re_path(r'^about/?$', views.about),
    re_path(r'^infections/?$', views.infection),
    re_path(r'^discord-link/?$', views.discord_link),
    re_path(r'^create_clan/?$', views.create_clan_view),
    re_path(r'^clan/clan_management/(?P<clan_name>[^/]+)/(?P<command>[^/]+)/(?P<person_id>[^/]+)/?$', views.clan_api),
    re_path(r'^clan/invitation_response/(?P<invite_id>[^/]+)/(?P<command>[^/]+)?$', views.clan_api_userresponse),
    re_path(r'^clan/request_response/(?P<request_id>[^/]+)/(?P<command>[^/]+)?$', views.clan_api_leaderresponse),
    re_path(r'^modify_clan/(?P<clan_name>[^/]+)/', views.modify_clan_view),
    re_path(r'^announcement/(?P<announcement_id>[^/]+)/?$', views.view_announcement),

    # Activation Routes
    re_path(r'^player_activation/?$', views.player_activation),
    re_path(r'^api/player_activation_api/?$', views.player_activation_api),
    re_path(r'^api/player_activation_rest/?$', views.player_activation_rest),
    re_path(r'^player_oz_activation/?$', views.player_oz_activation),
    re_path(r'^api/player_oz_activation_api/?$', views.player_oz_activation_api),
    re_path(r'^api/player_oz_activation_rest/?$', views.player_oz_activation_rest),
    re_path(r'^api/player_oz_enable/?$', views.player_oz_enable),

    # Admin Routes
    re_path(r'^admin/reset-game/?$', views.admin_reset_game),
    re_path(r'^admin/create-av/?$', views.admin_create_av),
    re_path(r'^admin/view-avs/?$', views.admin_view_avs),
    re_path(r'^admin/av/(?P<av_id>[^/]+)/?$', views.av_view),
    re_path(r'^admin/create-body-armor/?$', views.admin_create_body_armor),
    re_path(r'^admin/player_admin/tools/(?P<player_id>[^/]+)/(?P<command>[^/]+)/?$', views.player_admin_tools),
    re_path(r'^admin/bodyarmors/?$', views.bodyarmors),
    re_path(r'^admin/bodyarmor/(?P<armor_id>[^/]+)/?$', views.bodyarmor_view),
    re_path(r'^admin/bodyarmor/tools/(?P<armor_id>[^/]+)/(?P<command>[^/]+)/?$', views.bodyarmor_admin_tools),
    re_path(r'^admin/editmissions/?$', views.editmissions),
    re_path(r'^admin/editmission/(?P<mission_id>[^/]+)/?$', views.editmission),
    re_path(r'^admin/editpostgamesurvey/(?P<postgamesurvey_id>[^/]+)/?$', views.editpostgamesurvey),
    re_path(r'^admin/editpostgamesurveys/?$', views.editpostgamesurveys),
    re_path(r'^admin/reports/?$', views.reports),
    re_path(r'^admin/report/(?P<report_id>[^/]+)/?$', views.report),
    re_path(r'^admin/update_rules/?$', views.rules_update),
    re_path(r'^admin/update_about/?$', views.about_update),
    re_path(r'^admin/print/?$', views.print_ids),
    re_path(r'^admin/unsigned_waivers/?$', views.view_unsigned_waivers),
    re_path(r'^admin/print_one/(?P<player_uuid>[^/]+)/?$', views.print_one),
    re_path(r'^admin/print_preview/?$', views.print_preview),
    re_path(r'^admin/mark_printed/?$', views.mark_printed),
    re_path(r'^admin/manage_announcements/?$', views.manage_announcements),
    re_path(r'^admin/announcement/(?P<announcement_id>[^/]+)/?$', views.edit_announcement),
    re_path(r'^admin/badge_grant/(?P<badge_type_id>[^/]+)/?$', views.badge_grant),
    re_path(r'^admin/badge_grant_list/?$', views.badge_grant_list),
    re_path(r'^admin/badge_grant_api/(?P<badge_type_id>[^/]+)/(?P<player_id>[^/]+)/?$', views.badge_grant_api),
    re_path(r'^admin/view_failed_av_list/?$', views.view_failed_av_list),
    re_path(r'^admin/name_change_requests/?$', views.view_name_change_requests),
    re_path(r'^admin/name_change_response/(?P<request_id>[^/]+)/(?P<command>[^/]+)?$', views.name_change_response),

    # API Routes
    # re_path(r'^api/?', include(router.urls)),
    re_path(r'^api/discord-id/?$', views.ApiDiscordId.as_view()),
    re_path(r'^api/link-discord-id/?$', views.ApiLinkDiscordId.as_view()),
    re_path(r'^api/player/?$', views.ApiPlayerId.as_view()),
    re_path(r'^api/clans/?$', views.ApiClans.as_view()),
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
    re_path(r'^api/datatables/bodyarmor_get_loan_targets/?$', views.bodyarmor_get_loan_targets),
    re_path(r'^api/datatables/players/?$', views.players_api)
]
