
from django.http import JsonResponse
from rest_framework.decorators import api_view

from .decorators import staff_required_api
from .models import BadgeType, BadgeInstance, PlayerStatus, Person
from .models import get_active_game
from .views import for_all_methods


@for_all_methods(staff_required_api)
class StaffAPIViews(object):
    @api_view(["POST"])
    def badge_grant_api(request, badge_type_id, player_id):
        print(f"AAAAAAAAAAAAA, {badge_type_id}, {player_id}")
        try:
            badge_type = BadgeType.objects.get(id=badge_type_id, active=True)
        except:
            return JsonResponse({"status":"badge type not found"})
        if (request.user.admin_this_game) or (request.user.mod_this_game and badge_type.mod_grantable):
            pass
        else:
            return JsonResponse({"status":"not authorized"})
        try:
            status = PlayerStatus.objects.get(zombie_uuid=player_id)
            player = status.player
        except:
            return JsonResponse({"status":"player not found"})
        try:
            BadgeInstance(badge_type=badge_type, player=player, game_awarded=get_active_game()).save()
            return JsonResponse({"status":"success", "playername": str(player)})
        except:
            return JsonResponse({"status":"failed to save"})

    @api_view(["POST"])
    def badge_grant_id_api(request, badge_type_id, player_id):
        try:
            badge_type = BadgeType.objects.get(id=badge_type_id, active=True)
        except:
            return JsonResponse({"status": "badge type not found"})
        if (request.user.admin_this_game) or (request.user.mod_this_game and badge_type.mod_grantable):
            pass
        else:
            return JsonResponse({"status": "not authorized"})
        try:
            player = Person.objects.get(player_uuid=player_id)
        except:
            return JsonResponse({"status": "player not found"})
        try:
            BadgeInstance(badge_type=badge_type, player=player, game_awarded=get_active_game()).save()
            return JsonResponse({"status": "success", "playername": str(player)})
        except:
            return JsonResponse({"status": "failed to save"})
