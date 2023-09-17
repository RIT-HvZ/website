
from django.http import JsonResponse
from django.utils import timezone

from rest_framework.decorators import api_view

from .decorators import authentication_required_api
from .models import Clan, ClanHistoryItem, ClanInvitation, ClanJoinRequest, Person
from .views import for_all_methods


@for_all_methods(authentication_required_api)
class UserAPIViews(object):
    @api_view(["POST"])
    def clan_api(request, clan_name, command, person_id):
        clan = Clan.objects.get(name=clan_name)
        if command=="leave":
            if request.user.clan == clan and clan.leader != request.user:
                request.user.clan=None
                request.user.save()
                new_history_item = ClanHistoryItem.objects.create(clan=clan, actor=request.user, history_item_type='l')
                new_history_item.save()
                return JsonResponse({"status":"success"})
            return JsonResponse({"status":"not allowed"})
        if command == "request_to_join":
            if not request.user.has_ever_played:
                return JsonResponse({"status":"you must have been a player ever in order to use this"})
            existing_requests = ClanJoinRequest.objects.filter(clan=clan, requestor=request.user, status__in=['n','r','e'])
            if existing_requests.count() > 0:
                return JsonResponse({"status":"request already exists"})
            existing_leadership = Clan.objects.filter(leader=request.user)
            if existing_leadership.count() > 0:
                return JsonResponse({"status":"cannot request to join another clan while leading one"})
            join_request = ClanJoinRequest.objects.create(requestor=request.user, clan=clan)
            join_request.save()
            return JsonResponse({"status":"success"})

        if (request.user != clan.leader) and not request.user.admin_this_game:
            return JsonResponse({"status":"not authorized"})
        target = Person.objects.get(player_uuid=person_id)
        if command == "promote":
            if not target.clan == clan:
                return JsonResponse({"status":"player not in clan"})
            if request.user == target:
                return JsonResponse({"status":"cannot promote self"})
            clan.leader = target
            clan.save()
            new_history_item = ClanHistoryItem.objects.create(clan=clan, actor=request.user, other=target, history_item_type='x')
            new_history_item.save()
            return JsonResponse({"status":"success"})
        if command == "kick":
            if not target.clan == clan:
                return JsonResponse({"status":"player not in clan"})
            if request.user == target:
                return JsonResponse({"status":"cannot kick self"})
            target.clan = None
            target.save()
            new_history_item = ClanHistoryItem.objects.create(clan=clan, actor=request.user, other=target, history_item_type='k')
            new_history_item.save()
            return JsonResponse({"status":"success"})
        if command == "invite":
            if request.user == target:
                return JsonResponse({"status":"cannot invite self"})
            existing_invitations = ClanInvitation.objects.filter(clan=clan, invitee=target, status='n')
            if existing_invitations.count() > 0:
                return JsonResponse({"status":"invitation already exists"})
            existing_leadership = Clan.objects.filter(leader=target)
            if existing_leadership.count() > 0:
                return JsonResponse({"status":"cannot invite leader of another clan"})
            invitation = ClanInvitation.objects.create(inviter=request.user, invitee=target, clan=clan)
            invitation.save()
            return JsonResponse({"status":"success"})
        if command == "cancel_invite":
            if request.user == target:
                return JsonResponse({"status":"cannot cancel invite to self"})
            invites = ClanInvitation.objects.filter(invitee=target, clan=clan)
            done_something = False
            for invite in invites:
                invite.status = 'e'
                invite.response_timestamp = timezone.now()
                invite.save()
                done_something = True
            if done_something:
                return JsonResponse({"status":"success"})
            return JsonResponse({"status":"no invites to cancel"})
        if command == "disband":
            clan.disband_timestamp = timezone.now()
            clan.leader = None
            clan.save()
            for member in Person.objects.filter(clan=clan):
                member.clan = None
                member.save()
            new_history_item = ClanHistoryItem.objects.create(clan=clan, actor=request.user, history_item_type='d')
            new_history_item.save()
            return JsonResponse({"status":"success"})


    @api_view(["POST"])
    def clan_api_userresponse(request, invite_id, command):
        invite = ClanInvitation.objects.get(id=invite_id)
        if not invite.invitee == request.user:
            return JsonResponse({"status","not authorized"})
        if invite.status != "n":
            return JsonResponse({"status","invitation already responded to"})
        if command == "accept":
            invite.status = "a"
            invite.response_timestamp = timezone.now()
            invite.save()
            request.user.clan = invite.clan
            request.user.save()
            other_invitations = ClanInvitation.objects.filter(invitee=request.user, status='n')
            for other_invitation in other_invitations:
                other_invitation.status = 'e'
                other_invitation.response_timestamp = timezone.now()
                other_invitation.save()
            new_history_item = ClanHistoryItem.objects.create(clan=invite.clan, actor=request.user, history_item_type='i')
            new_history_item.save()
            return JsonResponse({"status":"success", "redirect_url": f"/clan/{invite.clan.name}/"})
        if command == "reject":
            invite.status = "r"
            invite.response_timestamp = timezone.now()
            invite.save()
            return JsonResponse({"status":"success"})
        

    @api_view(["POST"])
    def clan_api_leaderresponse(request, request_id, command):
        joinrequest = ClanJoinRequest.objects.get(id=request_id)
        if not joinrequest.clan.leader == request.user:
            return JsonResponse({"status","not authorized"})
        if joinrequest.status != "n":
            return JsonResponse({"status","request already responded to"})
        if command == "accept":
            joinrequest.status = "a"
            joinrequest.response_timestamp = timezone.now()
            joinrequest.save()
            joinrequest.requestor.clan = joinrequest.clan
            joinrequest.requestor.save()
            other_requests = ClanJoinRequest.objects.filter(requestor=joinrequest.requestor, status='n')
            for other_request in other_requests:
                other_request.status = 'e'
                other_request.response_timestamp = timezone.now()
                other_request.save()
            new_history_item = ClanHistoryItem.objects.create(clan=joinrequest.clan, actor=request.user, other=joinrequest.requestor, history_item_type='r')
            new_history_item.save()
            return JsonResponse({"status":"success"})
        if command == "reject":
            joinrequest.status = "r"
            joinrequest.response_timestamp = timezone.now()
            joinrequest.save()
            return JsonResponse({"status":"success"})
        
    