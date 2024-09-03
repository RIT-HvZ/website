from django.urls import path, re_path, include
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView

from . import views
#from rest_framework import routers
from .views_api_admin import AdminAPIViews
from .views_api_staff import StaffAPIViews
from .views_api_user import UserAPIViews
from .views_html_active_player import ActivePlayerHTMLViews
from .views_html_admin import AdminHTMLViews
from .views_html_staff import StaffHTMLViews
from .views_html_user import UserHTMLViews
from rest_framework.schemas import get_schema_view

# router = routers.DefaultRouter()
# router.register(r'users', views.UserViewSet)
# router.register(r'groups', views.GroupViewSet)

urlpatterns = [
    # Primary Game View Routes
    re_path(r'^player/(?P<player_id>[^/]+)/?$', views.player_view),
    re_path(r'^me/?$', UserHTMLViews.me),
    re_path(r'^name-change/?$', UserHTMLViews.name_change),
    re_path(r'^cancel_name_change/?$', UserHTMLViews.cancel_name_change),
    re_path(r'^clan/(?P<clan_name>[^/]+)/?$', views.clan_view),
    re_path(r'^players/?$', views.players),
    re_path(r'^report/?$', views.create_report),
    re_path(r'^clans/?$', views.clans),
    re_path(r'^tag/?$', ActivePlayerHTMLViews.tag),
    re_path(r'^av/?$', ActivePlayerHTMLViews.av),
    re_path(r'^blasterapproval/?$', AdminHTMLViews.blasterapproval),
    re_path(r'^missions/?$', ActivePlayerHTMLViews.missions_view),
    re_path(r'^api-auth/?', include('rest_framework.urls', namespace='rest_framework')),
    path(r'', views.index),
    re_path(r'^logout/?$', LogoutView.as_view()),
    re_path(r'^rules/?$', views.rules),
    re_path(r'^about/?$', views.about),
    re_path(r'^infections/?$', views.infection),
    re_path(r'^discord-link/?$', UserHTMLViews.discord_link),
    re_path(r'^create_clan/?$', ActivePlayerHTMLViews.create_clan_view),
    re_path(r'^clan/clan_management/(?P<clan_name>[^/]+)/(?P<command>[^/]+)/(?P<person_id>[^/]+)/?$', UserAPIViews.clan_api),
    re_path(r'^clan/invitation_response/(?P<invite_id>[^/]+)/(?P<command>[^/]+)?$', UserAPIViews.clan_api_userresponse),
    re_path(r'^clan/request_response/(?P<request_id>[^/]+)/(?P<command>[^/]+)?$', UserAPIViews.clan_api_leaderresponse),
    re_path(r'^modify_clan/(?P<clan_name>[^/]+)/', UserHTMLViews.modify_clan_view),
    re_path(r'^announcement/(?P<announcement_id>[^/]+)/?$', views.view_announcement),
    re_path(r'^tags/?$', views.view_tags),
    re_path(r'^ext/(?P<redir_name>[^/]+)/?$', views.redirect_view),

    # Activation Routes
    re_path(r'^player_activation/?$', AdminHTMLViews.player_activation),
    re_path(r'^api/player_activation_api/?$', AdminAPIViews.player_activation_api),
    re_path(r'^api/player_activation_rest/?$', AdminAPIViews.player_activation_rest),
    re_path(r'^player_oz_activation/?$', AdminHTMLViews.player_oz_activation),
    re_path(r'^api/player_oz_activation_api/?$', AdminAPIViews.player_oz_activation_api),
    re_path(r'^api/player_oz_activation_rest/?$', AdminAPIViews.player_oz_activation_rest),
    re_path(r'^api/player_oz_enable/?$', AdminAPIViews.player_oz_enable),

    # Admin Routes
    re_path(r'^admin/reset-game/?$', AdminHTMLViews.admin_reset_game),
    re_path(r'^admin/cullaccounts/?$', AdminHTMLViews.cull_accounts),
    re_path(r'^api/account_culling_api/?$', AdminAPIViews.get_cullable_accounts),
    re_path(r'^api/account_culling_rest/?$', AdminAPIViews.account_culling_rest),
    
    re_path(r'^admin/create-av/?$', AdminHTMLViews.admin_create_av),
    re_path(r'^admin/view-avs/?$', AdminHTMLViews.admin_view_avs),
    re_path(r'^admin/view-tags/?$', AdminHTMLViews.admin_view_tags),
    re_path(r'^admin/tag_api/(?P<tag_id>[^/]+)/(?P<command>[^/]+)?$', AdminAPIViews.admin_tag_api),
    re_path(r'^admin/av/(?P<av_id>[^/]+)/?$', AdminHTMLViews.av_view),
    re_path(r'^admin/create-body-armor/?$', AdminHTMLViews.admin_create_body_armor),
    re_path(r'^admin/player_admin/tools/(?P<player_id>[^/]+)/(?P<command>[^/]+)/?$', AdminAPIViews.player_admin_tools),
    re_path(r'^admin/bodyarmors/?$', AdminHTMLViews.bodyarmors),
    re_path(r'^admin/bodyarmor/(?P<armor_id>[^/]+)/?$', AdminHTMLViews.bodyarmor_view),
    re_path(r'^admin/bodyarmor/tools/(?P<armor_id>[^/]+)/(?P<command>[^/]+)/?$', AdminAPIViews.bodyarmor_admin_tools),
    re_path(r'^admin/editmissions/?$', AdminHTMLViews.editmissions),
    re_path(r'^admin/editmission/(?P<mission_id>[^/]+)/?$', AdminHTMLViews.editmission),
    re_path(r'^admin/editpostgamesurvey/(?P<postgamesurvey_id>[^/]+)/?$', AdminHTMLViews.editpostgamesurvey),
    re_path(r'^admin/editpostgamesurveys/?$', AdminHTMLViews.editpostgamesurveys),
    re_path(r'^admin/reports/?$', AdminHTMLViews.reports),
    re_path(r'^admin/report/(?P<report_id>[^/]+)/?$', AdminHTMLViews.report),
    re_path(r'^admin/update_rules/?$', AdminHTMLViews.rules_update),
    re_path(r'^admin/update_about/?$', AdminHTMLViews.about_update),
    re_path(r'^admin/unsigned_waivers/?$', AdminHTMLViews.view_unsigned_waivers),
    re_path(r'^admin/print/?$', AdminHTMLViews.print_choice),
    re_path(r'^admin/view_print/?$', AdminHTMLViews.print_ids),
    re_path(r'^admin/print_one/(?P<player_uuid>[^/]+)/?$', AdminHTMLViews.print_one),
    # re_path(r'^admin/mark_printed/?$', AdminHTMLViews.mark_printed),
    re_path(r'^admin/manage_announcements/?$', AdminHTMLViews.manage_announcements),
    re_path(r'^admin/announcement/(?P<announcement_id>[^/]+)/?$', AdminHTMLViews.edit_announcement),
    re_path(r'^admin/badge_grant/(?P<badge_type_id>[^/]+)/?$', StaffHTMLViews.badge_grant),
    re_path(r'^admin/badge_grant_list/?$', StaffHTMLViews.badge_grant_list),
    re_path(r'^admin/badge_grant_api/(?P<badge_type_id>[^/]+)/(?P<player_id>[^/]+)/?$', StaffAPIViews.badge_grant_api),
    re_path(r'^admin/view_failed_av_list/?$', AdminHTMLViews.view_failed_av_list),
    re_path(r'^admin/name_change_requests/?$', AdminHTMLViews.view_name_change_requests),
    re_path(r'^admin/name_change_response/(?P<request_id>[^/]+)/(?P<command>[^/]+)?$', AdminAPIViews.name_change_response),

    # PII Media
    re_path(r'^media/profile_pictures/(?P<player_uuid>[^/]+)/(?P<fname>[^/]+)/?$', views.profile_picture_view),

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
    re_path(r'^api/datatables/bodyarmor_get_loan_targets/?$', AdminAPIViews.bodyarmor_get_loan_targets),
    re_path(r'^api/datatables/players/?$', views.players_api),
]
