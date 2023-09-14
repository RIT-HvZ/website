from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseForbidden, HttpResponseNotFound
from django.conf import settings
from django.core import exceptions
from rest_framework.response import Response
from django.db.models import Count
from django.utils import timezone
from django.db.utils import IntegrityError
from django.contrib.auth.models import Group
from rest_framework import viewsets
from rest_framework import permissions
from .serializers import UserSerializer, GroupSerializer
from .models import Announcement, AntiVirus, Mission, Person, BadgeInstance, BadgeType, PlayerStatus, Tag, Blaster, Clan, ClanHistoryItem, ClanInvitation, ClanJoinRequest, Report, ReportUpdate, Game, Rules, About, FailedAVAttempt, get_active_game, reset_active_game, PostGameSurvey, PostGameSurveyResponse, PostGameSurveyOption, BodyArmor, DiscordLinkCode, OZEntry
from .forms import AnnouncementForm, TagForm, AVForm, AVCreateForm, BlasterApprovalForm, ReportUpdateForm, ReportForm, ClanCreateForm, RulesUpdateForm, AboutUpdateForm, BodyArmorCreateForm, MissionForm, PostGameSurveyForm
from rest_framework.decorators import api_view
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.sites.shortcuts import get_current_site
from rest_framework.views import APIView
from rest_framework_api_key.models import APIKey
from rest_framework_api_key.permissions import HasAPIKey
import json
import discord
import base64
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import random

report_webhook = None
if settings.DISCORD_REPORT_WEBHOOK_URL:
    report_webhook = discord.SyncWebhook.from_url(settings.DISCORD_REPORT_WEBHOOK_URL)

def index(request):
    game = get_active_game()
    humancount = PlayerStatus.objects.filter(game=game).filter(Q(status='h') | Q(status='v') | Q(status='e')).count()
    zombiecount = PlayerStatus.objects.filter(game=game).filter(Q(status='z') | Q(status='x') | Q(status='o')).count()
    most_tags = PlayerStatus.objects.filter(game=game).annotate(tag_count=Count("player__taggers", filter=Q(player__taggers__game=game))).filter(tag_count__gt=0).order_by("-tag_count")
    recent_tags = [ t for t in Tag.objects.filter(game=get_active_game()).order_by('-timestamp') ]
    recent_avs = [ a for a in AntiVirus.objects.filter(game=get_active_game(), used_by__isnull=False).order_by('-time_used') ]
    merged_recents = []
    while len(merged_recents) < 10:
        if len(recent_tags) == 0 and len(recent_avs) == 0:
            break
        if len(recent_avs) <= 0 or (len(recent_tags) > 0 and recent_tags[0].timestamp < recent_avs[0].time_used):
            merged_recents.append(recent_tags.pop(0))
        elif len(recent_tags) <= 0 or (len(recent_avs) > 0 and recent_tags[0].timestamp > recent_avs[0].time_used):
            merged_recents.append(recent_avs.pop(0))
        else:
            break


    return render(request, "index.html", {'game': game, 'humancount': humancount, 'zombiecount': zombiecount, 'most_tags': most_tags[:10], 'recent_events': merged_recents})


def me(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    return player_view(request, request.user.player_uuid, is_me=True)


def infection(request):
    game = get_active_game()
    ozs = PlayerStatus.objects.filter(game=game, status='o')
    tags = Tag.objects.filter(game=game)
    return render(request, "infection.html", {'ozs':ozs, 'tags':tags})


def discord_link(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")

    user = request.user
    link_codes = DiscordLinkCode.objects.filter(account=user)
    code = None
    
    if len(link_codes) > 0:
        for mini_code in link_codes:
            if mini_code.expiration_time < timezone.localtime():
                mini_code.delete()
            else:
                code = mini_code

    if code == None:
        code = DiscordLinkCode()
        code.account = user
        code.expiration_time = timezone.localtime() + timedelta(days=1)
        code.save()
    
    return player_view(request, request.user.player_uuid, is_me=True, discord_code=code.code)


def missions_view(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    this_game = get_active_game()
    if request.method == "POST":
        survey_option = request.POST.get("survey_option")
        if not survey_option or not str(survey_option).isnumeric():
            return HttpResponseRedirect('/')
        response = PostGameSurveyOption.objects.get(id=survey_option)
        print(f"Chosen response: {response}")
        survey = response.survey
        if not survey.is_open:
            return HttpResponseRedirect("/")
        status = request.user.current_status
        # See if we have an existing Response for this survey
        existing_responses = PostGameSurveyResponse.objects.filter(survey=survey, player=request.user)
        if (survey.mission.team == 'h' and status.is_human()) or (survey.mission.team == "z" and status.is_zombie()) or status.is_admin() or survey.mission.team == "a":
            # All authorization steps complete
            print("Authorized")
            if existing_responses.count() > 0:
                # A response for this survey for this user already exists. Update it.
                existing_response = existing_responses[0]
                print(f"Existing response: {existing_response}")
                existing_response.response = response
                existing_response.save()
                print(f"Updated response: {existing_response}")
            else:
                # No response for this survey for this user exists. Create one.
                print("No response.")
                new_response = PostGameSurveyResponse.objects.create(player=request.user, survey=survey, response=response)
                new_response.save()
                print(f"New response: {new_response}")
        else:
            return HttpResponseRedirect("/")
    if request.user.current_status.is_zombie():
        missions = Mission.objects.filter(game=this_game, team__in=['a','z'], story_form_go_live_time__lt=timezone.now())
    elif request.user.current_status.is_human():
        missions = Mission.objects.filter(game=this_game, team__in=['a','h'], story_form_go_live_time__lt=timezone.now())
    elif request.user.current_status.is_staff():
        missions = Mission.objects.filter(game=this_game, story_form_go_live_time__lt=timezone.now())
    return render(request, "missions.html", {'missions':missions.order_by("-go_live_time")})


def editmissions(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    this_game = get_active_game()
    missions = Mission.objects.filter(game=this_game)
    return render(request, "editmissions.html", {'missions':missions.order_by("-go_live_time")})


def editmission(request, mission_id):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    
    if request.method == "GET":
        if mission_id == "new":
            form = MissionForm()
        else:
            form = MissionForm(instance=Mission.objects.get(id=mission_id))
    else:
        if mission_id == "new":
            form = MissionForm(request.POST)
            if form.is_valid():
                print(form.cleaned_data)
                mission = form.save()
        else:
            form = MissionForm(request.POST, instance=Mission.objects.get(id=mission_id))
            if form.is_valid():
                mission = form.save()

        return HttpResponseRedirect("/admin/editmissions/")
    return render(request, "editmission.html", {'form': form, 'mission': mission_id})


def editpostgamesurvey(request, postgamesurvey_id):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    if request.method == "GET":
        if postgamesurvey_id == "new":
            form = PostGameSurveyForm()
        else:
            form = PostGameSurveyForm(instance=PostGameSurvey.objects.get(id=postgamesurvey_id))
    else:
        if postgamesurvey_id == "new":
            form = PostGameSurveyForm(request.POST)
            if form.is_valid():
                form.save()
        else:
            form = PostGameSurveyForm(request.POST, instance=PostGameSurvey.objects.get(id=postgamesurvey_id))
            if form.is_valid():
                form.save()

        return HttpResponseRedirect("/admin/editpostgamesurveys/")
    return render(request, "editpostgamesurvey.html", {'form': form, 'postgamesurvey': postgamesurvey_id})


def editpostgamesurveys(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    this_game = get_active_game()
    surveys = PostGameSurvey.objects.filter(game=this_game)
    return render(request, "editpostgamesurveys.html", {'surveys':surveys.order_by("-go_live_time")})


def tag(request):
    if not request.user.is_authenticated or request.user.current_status.is_nonplayer():
        return HttpResponseRedirect("/")
    player = request.user
    if player.current_status.is_zombie() or player.current_status.is_staff():
        qr = player.current_status.zombie_uuid
    elif player.current_status.status == 'h':
        qr = player.current_status.tag1_uuid
    elif player.current_status.status == 'v':
        qr = player.current_status.tag2_uuid
    else:
        qr = None
    scanned_values = request.GET.get('scan')
    scanned_status = None
    if scanned_values is not None:
        scan_tag1, scan_tag2, scan_zombie = scanned_values.split("|")
        statuses = PlayerStatus.objects.filter(tag1_uuid=scan_tag1,tag2_uuid=scan_tag2,zombie_uuid=scan_zombie)
        if len(statuses) > 0:
            scanned_status = statuses[0]
    if request.method == "GET":
        data = {}
        player = request.user
        status = player.current_status
        if status.is_zombie() or status.is_staff():
            data['tagger_id'] = status.zombie_uuid
        elif status.is_human():
            if status.status == 'h':
                data['taggee_id'] = status.tag1_uuid
            elif status.status == 'v':
                data['taggee_id'] = status.tag2_uuid
        prefilled_zombie = request.GET.get('z',None)
        prefilled_human = request.GET.get('h',None)
        if scanned_status:
            if scanned_status.is_human():
                if scanned_status.status == "h":
                    data['taggee_id'] = scanned_status.tag1_uuid
                elif scanned_status.status == "v":
                    data['taggee_id'] = scanned_status.tag2_uuid
            elif scanned_status.is_zombie() or scanned_status.is_staff():
                data['tagger_id'] = scanned_status.zombie_uuid
                
        if prefilled_zombie:
            data['tagger_id'] = prefilled_zombie
        if prefilled_human:
            data["taggee_id"] = prefilled_human
        form = TagForm(initial=data)
    else:
        form = TagForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['type'] == "player":
                tag = Tag.objects.create(tagger=form.cleaned_data['tagger'].player, taggee=form.cleaned_data['taggee'].player, game=get_active_game())
                tag.handle_streak_badges()
                tag.save()
                if form.cleaned_data['taggee'].status == 'v':
                    form.cleaned_data['taggee'].status = 'x'
                else:
                    form.cleaned_data['taggee'].status = 'z'
                form.cleaned_data['taggee'].save()
            else:
                tag = Tag.objects.create(tagger=form.cleaned_data['tagger'].player, armor_taggee=form.cleaned_data['taggee'], game=get_active_game())
                tag.handle_streak_badges()
                tag.save()
            form = TagForm()
            return render(request, "tag.html", {'form':form, 'tagcomplete': True, 'tag': tag, 'qr': qr})
    
    return render(request, "tag.html", {'form':form, 'tagcomplete': False, 'qr': qr})


def av(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")

    user_status = request.user.current_status

    if not user_status.can_av:
        return HttpResponseRedirect("/")
    
    if request.method == "GET":     
        form = AVForm()
    else:
        form = AVForm(request.POST)
        if form.is_valid():
            user_status.status = 'v'
            user_status.save()
            form.cleaned_data['av'].used_by = request.user
            form.cleaned_data['av'].time_used = datetime.now()
            form.cleaned_data['av'].save()
            newform = AVForm()
            return render(request, "av.html", {'form':newform, 'avcomplete': True, 'av': form.cleaned_data['av']})
        else:
            new_failed_av = FailedAVAttempt.objects.create(player=request.user, game=get_active_game(), code_used=form.cleaned_data['av_code'])
            new_failed_av.save()
    return render(request, "av.html", {'form':form, 'avcomplete': False})


def blasterapproval(request):
    if (not request.user.is_authenticated) or (not request.user.admin_this_game):
        return HttpResponseRedirect("/")
    if request.method == "GET":     
        form = BlasterApprovalForm()
        form.fields['owner'].queryset = Person.objects.filter(playerstatus__game=get_active_game()) \
                                                      .filter(playerstatus__status__in=['h','v','e','z','o','x']) \
                                                      .annotate(num_status=Count('playerstatus')) \
                                                      .filter(num_status=1)
    else:
        form = BlasterApprovalForm(request.POST, request.FILES)
        if form.is_valid():
            blaster = Blaster()
            blaster.name = form.cleaned_data['name']
            blaster.owner = form.cleaned_data['owner']
            blaster.game_approved_in = get_active_game()
            blaster.picture = form.cleaned_data['picture']
            blaster.avg_chrono = form.cleaned_data['avg_chrono']
            blaster.save()
            blaster.approved_by.add(request.user)
            blaster.save()
            newform = BlasterApprovalForm()
            return render(request, "blasterapproval.html", {'form':newform, 'approvalcomplete': True})
    return render(request, "blasterapproval.html", {'form':form, 'approvalcomplete': False})


def admin_create_av(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")

    if not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    
    if request.method == "GET":     
        form = AVCreateForm()
    else:
        form = AVCreateForm(request.POST)

        if form.is_valid():
            av = form.save()
            newform = AVCreateForm()
            return render(request, "create_av.html", {'form':newform, 'createcomplete': True})
    return render(request, "create_av.html", {'form':form, 'createcomplete': False})


def admin_view_avs(request):
    game = get_active_game()
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    anti_viruses = AntiVirus.objects.filter(game=game)
    context = {"avs": anti_viruses.order_by("-expiration_time")}
    return render(request, "view_avs.html", context)


def admin_reset_game(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")

    if not request.user.admin_this_game:
        return HttpResponseRedirect("/")

    reset_active_game()
    return HttpResponseRedirect("/")


def admin_create_body_armor(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")

    if not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    
    if request.method == "GET":     
        form = BodyArmorCreateForm()
    else:
        form = BodyArmorCreateForm(request.POST)

        if form.is_valid():
            bodyarmor = BodyArmor.objects.create(armor_code=form.cleaned_data['armor_code'], expiration_time=form.cleaned_data['expiration_time'], game = get_active_game())
            bodyarmor.save()
            newform = BodyArmorCreateForm()
            return render(request, "create_body_armor.html", {'form':newform, 'createcomplete': True, 'bodyarmor': bodyarmor})
    return render(request, "create_body_armor.html", {'form':form, 'createcomplete': False})


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Person.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


def player_view(request, player_id, is_me=False, game=None, discord_code=None):
    player = Person.objects.get(player_uuid=player_id)
    if game is None:
        game = get_active_game()

    context = {
        'user': request.user,
        'player': player,
        'is_me': is_me,
        'badges': BadgeInstance.objects.filter(player=player), 
        'tags': Tag.objects.filter(tagger=player, game=game),
        'status': PlayerStatus.objects.get_or_create(player=player, game=game)[0],
        'blasters': Blaster.objects.filter(owner=player, game_approved_in=game),
        'domain': request.build_absolute_uri('/tag/'),
        'discord_code': discord_code,
        'reportees': Report.objects.filter(reportees__exact=player),
        'reporters': Report.objects.filter(reporter=player),
        'failedavs': FailedAVAttempt.objects.filter(player=player, game=game),
        'is_user_clan_leader': Clan.objects.filter(leader=request.user).count() > 0 if request.user.is_authenticated else False,
        'is_player_clan_leader': Clan.objects.filter(leader=player).count() > 0
    }
    
    return render(request, "player.html", context)


@api_view(["POST"])
def player_admin_tools(request, player_id, command):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return JsonResponse({"status": "not authorized"})

    try:
        player = Person.objects.get(player_uuid = player_id)
        playerstatus = PlayerStatus.objects.get(player = player, game = get_active_game())
    except:
        return JsonResponse({"status": "player not found"})
    if command == "print_id":
        return print_one(request, player_id)
    elif command == "make_oz":
        playerstatus.status = 'o'
    elif command == "make_nonplayer":
        playerstatus.status = 'n'
    elif command == "make_human":
        playerstatus.status = 'h'
    elif command == "make_human_av":
        playerstatus.status = 'v'
    elif command == "make_human_extracted":
        playerstatus.status = 'e'
    elif command == "make_zombie":
        playerstatus.status = 'z'
    elif command == "make_zombie_av":
        playerstatus.status = 'x'
    elif command == "make_mod":
        playerstatus.status = 'm'
    elif command == "avban":
        playerstatus.av_banned = True
    elif command == "avunban":
        playerstatus.av_banned = False
    elif command == "ban":
        playerstatus.status = 'n'
        player.is_banned = True
        player.ban_timestamp = timezone.now()
        player.clan = None
        player.save()
        existing_leadership = Clan.objects.filter(leader=player)
        # Remove from leadership of any clans
        for led_clan in existing_leadership:
            ClanHistoryItem(clan=led_clan, actor=player, history_item_type="a").save() # "Leader banned" history item
            other_members = Person.objects.filter(clan=led_clan)

            # If this clan didn't have any other members, disband it
            if other_members.count() == 0:
                led_clan.leader = None
                led_clan.disband_timestamp = timezone.now()
                led_clan.save()
                ClanHistoryItem(clan=led_clan, history_item_type="e").save() # "Disbanded by system" history item

            # Otherwise, attempt to find a suitable new leader
            else:
                suitable_leaders = other_members.filter(playerstatus__game=get_active_game(), playerstatus__status__in=['h','v','e','z','o','x','a','m'])

                # If no suitable leaders can be found, disband the clan
                if suitable_leaders.count() == 0:
                    for clan_member in other_members:
                        clan_member.clan = None
                        clan_member.save()
                    
                    led_clan.leader = None
                    led_clan.disband_timestamp = timezone.now()
                    led_clan.save()
                    ClanHistoryItem(clan=led_clan, history_item_type="e").save() # "Disbanded by system" history item
                
                # Otherwise, pick a new leader at random
                else:
                    new_leader = random.choice(suitable_leaders)
                    led_clan.leader = new_leader
                    led_clan.save()
                    ClanHistoryItem(clan=led_clan, actor=new_leader, history_item_type="b").save() # "Promoted to leader by system" history item

    else:
        return JsonResponse({'status': 'fail', 'error': "unknown command"})          
    playerstatus.save()

    return JsonResponse({'status': 'success'})


@api_view(["POST"])
def bodyarmor_admin_tools(request, armor_id, command):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return JsonResponse({"status": "not authorized"})
    try:
        armor = BodyArmor.objects.get(armor_uuid = armor_id)
    except:
        return JsonResponse({"status", "body armor id not found"})
    if command == "mark_returned":
        armor.returned = True
        armor.save()
        return JsonResponse({"status": "success"})
    elif command == "loan":
        target_player_uuid = request.data.get("target_uuid")
        try:
            player = Person.objects.get(player_uuid=target_player_uuid)
        except:
            return JsonResponse({"status": "player not found"})
        armor.loaned_to = player
        armor.loaned_at = timezone.localtime()
        armor.save()
        return JsonResponse({'status': 'success', "playername": f"{player.first_name} {player.last_name}", "time": str(armor.loaned_at)})

        


@api_view(["GET"])
def bodyarmor_get_loan_targets(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return JsonResponse({"status": "not authorized"})

    game = get_active_game()
    r = request.query_params
    try:
        order_column = int(r.get("order[0][column]"))
        assert order_column == 1
        order_column_name = r.get(f"columns[{order_column}][name]")
        assert order_column_name in ("name",)
        order_direction = r.get("order[0][dir]")
        assert order_direction in ("asc","desc")
        limit = int(request.query_params["length"])
        start = int(request.query_params["start"])
        search = r["search[value]"] 
    except AssertionError:
        raise
    players = Person.full_name_objects.filter(playerstatus__game=game).filter(playerstatus__status__in=['h','v','e'])
    if search != "":
        players = players.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(clan__name__icontains=search))
    result = []
    filtered_length = len(players)
    if start < filtered_length:
        for person in players[start:]:
            if limit == 0:
                break

            result.append({
                "name": f"""<a class="dt_name_link" href="/player/{person.player_uuid}/">{person.first_name} {person.last_name}</a>""",
                "pic": f"""<a class="dt_profile_link" href="/player/{person.player_uuid}/"><img src='{person.picture_url}' class='dt_profile' /></a>""",
                "loan": f"""<input type="button" value="Loan" class="dt_loan_button" id="{person.player_uuid}" onclick="loan_to(this)" />""",
                "DT_RowData": {"person_url": f"/player/{person.player_uuid}/", "clan_url": f"/clan/{person.clan.name}/" if person.clan is not None else ""}
            })
            limit -= 1
    data = {
        "draw": int(r['draw']),
        "recordsTotal": Person.full_name_objects.filter(playerstatus__game=game).filter(playerstatus__status__in=['h','v','e','z','o','x','a','m']).count(),
        "recordsFiltered": filtered_length,
        "data": result
    }
    return JsonResponse(data)


def clan_view(request, clan_name):
    clan = Clan.objects.get(name=clan_name)
    is_leader = (request.user.is_authenticated and clan.leader == request.user)
    if is_leader or (request.user.is_authenticated and request.user.admin_this_game):
        history = ClanHistoryItem.objects.filter(clan=clan).order_by('-timestamp')
    else:
        history = []
    can_join = request.user.is_authenticated and Clan.objects.filter(leader=request.user).count() == 0 and request.user.has_ever_played and clan.leader is not None
    context = {
        'clan': clan,
        'roster': Person.objects.filter(clan=clan),
        'is_leader': is_leader,
        'user': request.user,
        'history': history,
        'can_join': can_join,
        'show_history': is_leader or (request.user.is_authenticated and request.user.admin_this_game)
    }
    return render(request, "clan.html", context)

@api_view(["POST"])
def clan_api(request, clan_name, command, person_id):
    if not request.user.is_authenticated:
        return JsonResponse({"status":"you must be logged in to use this"})
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
    

def players(request):
    context = {}
    return render(request, "players.html", context)


@api_view(["GET"])
def players_api(request, game=None):
    if game is None:
        game = get_active_game()
    r = request.query_params
    try:
        order_column = int(r.get("order[0][column]"))
        assert order_column in [1,2,3,4]
        order_column_name = r.get(f"columns[{order_column}][name]")
        assert order_column_name in ("name","status","tags","clan")
        order_direction = r.get("order[0][dir]")
        assert order_direction in ("asc","desc")
        limit = int(request.query_params["length"])
        start = int(request.query_params["start"])
        search = r["search[value]"] 
        #print(start)
        #print(limit)
    except AssertionError:
        raise
    query = Person.full_name_objects.filter(playerstatus__game=game, playerstatus__status__in=['h','v','e','z','o','x','a','m'])
    if search != "":
        query = query.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(clan__name__icontains=search))
    if order_column_name == 'tags':
        query = query.annotate(n_tags=Count('taggers', filter=Q(taggers__game=game))).order_by(f"""{'-' if order_direction == 'asc' else ''}n_tags""")
    elif order_column_name == 'status':
        query = sorted([person for person in query], key=lambda person: person.current_status.listing_priority, reverse=(order_direction=='desc'))
    else:
        query = query.order_by(f"""{'-' if order_direction == 'desc' else ''}{ {"name":"full_name", "clan": "clan__name"}[order_column_name]}""")

    result = []
    filtered_length = len(query)
    if start < filtered_length:
        for person in query[start:]:
            if limit == 0:
                break
            try:
                person_status = PlayerStatus.objects.get(player=person, game=game)
            except:
                continue
            result.append({
                "name": f"""<a class="dt_name_link" href="/player/{person.player_uuid}/">{person.first_name} {person.last_name}</a>""",
                "pic": f"""<a class="dt_profile_link" href="/player/{person.player_uuid}/"><img src='{person.picture_url}' class='dt_profile' /></a>""",
                "status": {"h": "Human", "a": "Admin", "z": "Zombie", "m": "Mod", "v": "Human", "o": "Zombie", "n": "NonPlayer", "x": "Zombie", "e": "Human (Extracted)"}[person_status.status],
                "clan": None if person.clan is None else (f"""<a href="/clan/{person.clan.name}/" class="dt_clan_link">person.clan.name</a>""" if (person.clan is None or person.clan.picture is None) else f"""<a href="/clan/{person.clan.name}/" class="dt_clan_link"><img src='{person.clan.picture.url}' class='dt_clanpic' alt='{person.clan}' /><span class="dt_clanname">{person.clan}</span></a>"""),
                "clan_pic": None if (person.clan is None or person.clan.picture is None) else person.clan.picture.url,
                "tags": Tag.objects.filter(tagger=person,game=game).count(),
                "DT_RowClass": {"h": "dt_human", "v": "dt_human", "e": "dt_human", "a": "dt_admin", "z": "dt_zombie", "o": "dt_zombie", "n": "dt_nonplayer", "x": "dt_zombie", "m": "dt_mod"}[person_status.status],
                "DT_RowData": {"person_url": f"/player/{person.player_uuid}/", "clan_url": f"/clan/{person.clan.name}/" if person.clan is not None else ""}
            })
            limit -= 1
    data = {
        "draw": int(r['draw']),
        "recordsTotal": Person.full_name_objects.filter(playerstatus__game=game).filter(playerstatus__status__in=['h','v','e','z','o','x','a','m']).count(),
        "recordsFiltered": filtered_length,
        "data": result
    }
    return JsonResponse(data)


def player_activation(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect('/')
    context = {}
    return render(request, "player_activation.html", context)

#TODO: Returning raw HTML to embed in the page is a bad idea, find a better solution
@api_view(["GET"])
def player_activation_api(request, game=None):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponse(status=403, content='Only admins can use this API')

    if game is None:
        game = get_active_game()
    r = request.query_params
    try:
        order_column = int(r.get("order[0][column]"))
        assert order_column == 1
        order_column_name = r.get(f"columns[{order_column}][name]")
        assert order_column_name in ("name",)
        order_direction = r.get("order[0][dir]")
        assert order_direction in ("asc","desc")
        limit = int(request.query_params["length"])
        start = int(request.query_params["start"])
        search = r["search[value]"]
    except AssertionError:
        raise
    query = Person.full_name_objects.filter(is_banned=False, is_active=True)
    if search != "":
        query = query.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(clan__name__icontains=search))
    query = query.order_by(f"""{'-' if order_direction == 'desc' else ''}{ {"name":"full_name"}[order_column_name]}""")
    result = []
    filtered_length = len(query)
    if start < filtered_length:
        for person in query[start:]:
            if limit == 0:
                break
            try:
                person_status = PlayerStatus.objects.get_or_create(player=person, game=game)[0]
            except:
                continue
            if person.active_this_game:
                continue
            result.append({
                "name": f"""{person.first_name} {person.last_name}""",
                "pic": f"""<img src='{person.picture_url}' class='dt_profile' />""",
                "email": f"""{person.email}""",
                "DT_RowClass": {"h": "dt_human", "v": "dt_human", "a": "dt_admin", "z": "dt_zombie", "o": "dt_zombie", "n": "dt_nonplayer", "x": "dt_zombie", "m": "dt_mod"}[person_status.status],
                "activation_link": f"""<button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#activationmodal" data-bs-activationname="{person.first_name} {person.last_name}" data-bs-activationid="{person.player_uuid}">Activate</button>"""
            })
            limit -= 1
    data = {
        "draw": int(r['draw']),
        "recordsTotal": Person.full_name_objects.filter(playerstatus__game=game).filter(playerstatus__status='n').count(),
        "recordsFiltered": filtered_length,
        "data": result
    }
    return JsonResponse(data)


@api_view(["POST"])
def player_activation_rest(request):
    game = get_active_game()
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponse(status=403, content='Only admins can use this API')

    try:
        requested_player = Person.objects.get(player_uuid=request.POST["activated_player"])
        image_base64 = request.POST['player_photo'].replace('data:image/jpeg;base64,', '').replace(" ","+")
        print(image_base64)
        im_bytes = base64.b64decode(image_base64)   # im_bytes is a binary image
        im_file = BytesIO(im_bytes)  # convert image to file-like object
        img = Image.open(im_file)   # img is now PIL Image object

        output = BytesIO()
        im = img.convert('RGB')
        im.thumbnail( (400, 400) , Image.ANTIALIAS )
        im.save(output, format="JPEG", quality=95)
        output.seek(0)
        requested_player.picture = InMemoryUploadedFile(output,'ImageField', "%s.jpg" % requested_player.player_uuid, 'image/jpeg', sys.getsizeof(output), None)
        person_status = PlayerStatus.objects.get(player=requested_player, game=game)
        person_status.activation_timestamp = timezone.now()
        person_status.status = 'h'
        requested_player.save()
        person_status.save()
        return JsonResponse({"status":"success"})
    except Exception as e:
        return JsonResponse({"status":"error", "error": str(e)})


def player_oz_activation(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect('/')
    context = {}
    return render(request, "player_oz_activation.html", context)


@api_view(["GET"])
def player_oz_activation_api(request, game=None):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponse(status=403, content='Only admins can use this API')

    if game is None:
        game = get_active_game()
    r = request.query_params
    order_column = int(r.get("order[0][column]"))
    assert order_column == 1
    order_column_name = r.get(f"columns[{order_column}][name]")
    assert order_column_name in ("name",)
    order_direction = r.get("order[0][dir]")
    assert order_direction in ("asc","desc")
    limit = int(request.query_params["length"])
    start = int(request.query_params["start"])
    search = r["search[value]"]

    query = PlayerStatus.objects.filter(Q(game=game) & ~Q(status='n'))
    if search != "":
        query = query.filter(Q(player__first_name__icontains=search) | Q(player__last_name__icontains=search))
    result = []
    filtered_length = len(query)
    result = [
        {
            "name": f"{player_status.player.first_name} {player_status.player.last_name}",
            "pic": f"<img src='{player_status.player.picture_url}' class='dt_profile' />",
            "email": f"{player_status.player.email}",
            "uuid": f"{player_status.player.player_uuid}",
            "DT_RowClass": {"h": "dt_human", "v": "dt_human", "a": "dt_admin", "z": "dt_zombie", "o": "dt_zombie", "n": "dt_nonplayer", "x": "dt_zombie", "m": "dt_mod"}[player_status.status],
            "activation_link": f"""<button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#activationmodal" data-bs-activationname="{player_status.player.first_name} {player_status.player.last_name}" data-bs-activationid="{player_status.player.player_uuid}">Make OZ</button>""",
        } for player_status in query[start:start + limit]
    ]

    data = {
        "draw": int(r['draw']),
        "recordsTotal": Person.full_name_objects.filter(playerstatus__game=game).filter(playerstatus__status='n').count(),
        "recordsFiltered": filtered_length,
        "data": result
    }
    return JsonResponse(data)


@api_view(["POST"])
def player_oz_activation_rest(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponse(status=403, content='Only admins can use this API')

    try:
        requested_player = Person.objects.get(player_uuid=request.POST["activated_player"])
        game = get_active_game()
        if len(OZEntry.objects.filter(player=requested_player, game=game)) > 0:
            return JsonResponse({"status":"error", "error": "This player is already set as an OZ"})

        OZEntry.objects.create(player=requested_player, game=game)

        return JsonResponse({"status":"success"})
    except Exception as e:
        return JsonResponse({"status":"error", "error": str(e)})


@api_view(["POST"])
def player_oz_enable(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponse(status=403, content='Only admins can use this API')

    try:
        game = get_active_game()
        for entry in OZEntry.objects.filter(game=game):
            player_status = entry.player.current_status
            player_status.status = 'o'
            player_status.save()
            entry.delete()
        return JsonResponse({"status":"success"})
    except Exception as e:
        return JsonResponse({"status":"error", "error": str(e)})

def clans(request):
    context = {}
    return render(request, "clans.html", context)

@api_view(["GET"])
def clans_api(request):
    r = request.query_params
    try:
        order_column = int(r.get("order[0][column]"))
        assert order_column in [1,2]
        order_column_name = r.get(f"columns[{order_column}][name]")
        assert order_column_name in ("name","size")
        order_direction = r.get("order[0][dir]")
        assert order_direction in ("asc","desc")
        limit = int(request.query_params["length"])
        start = int(request.query_params["start"])
        search = r["search[value]"]
    except AssertionError:
        raise
    query = Clan.objects.all().annotate(clan_member_count=Count('clan_members'))
    if search != "":
        query = query.filter(name__icontains=search)
    query = query.order_by(f"""{'-' if order_direction == 'desc' else ''}{ {"name":"name", "size": "clan_member_count", }[order_column_name]}""")
    result = []
    for clan in query[start:limit]:
        result.append({
            "name": f"""<a class="dt_name_link" style="color:{clan.get_text_color}" href="/clan/{clan.name}/">{clan.name}</a>""",
            "pic": f"""<a  class="dt_profile_link" style="color:{clan.get_text_color}" href="/clan/{clan.name}/"><img src='{clan.picture.url}' class='dt_profile' /></a>""",
            "DT_RowAttr": {"style": f'background-color:{clan.color}; color:{clan.get_text_color}' },
            "size": f"""<span style="color:{clan.get_text_color}"> {clan.clan_members.count()} </span>"""
        })
    data = {
        "draw": int(r['draw']),
        "recordsTotal": Clan.objects.all().count(),
        "recordsFiltered": len(result),
        "data": result
    }
    return JsonResponse(data)


def rules(request):
    return render(request, "rules.html", {'rules': Rules.load()})


def about(request):
    return render(request, "about.html", {'about': About.load()})


def bodyarmors(request):
    game = get_active_game()
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    body_armors = BodyArmor.objects.filter(game=game)
    context = {"bodyarmors": body_armors.order_by("-expiration_time")}
    return render(request, "bodyarmors.html", context)


def bodyarmor_view(request, armor_id):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    armor = BodyArmor.objects.get(armor_uuid=armor_id)
    context = {
        'armor': armor,
    }
    return render(request, "bodyarmor.html", context)


def av_view(request, av_id):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    av = AntiVirus.objects.get(av_uuid=av_id)
    context = {
        'av': av,
    }
    return render(request, "av_view.html", context)


def create_report(request):
    report_complete = False
    report_id = None
    if request.method == "POST":
        form = ReportForm(request.POST, request.FILES, authenticated=request.user.is_authenticated)
        if form.is_valid():
            report = form.instance
            report.game = get_active_game()
            if request.user.is_authenticated:
                report.reporter = request.user
            report.status = "n"
            report.save()
            report_complete = True
            report_id = report.report_uuid
            form = ReportForm(authenticated=request.user.is_authenticated)
            if report_webhook:
                report_webhook.send("!report " +
                                    json.dumps({
                                        'report_text': report.report_text, 
                                        'reporter_email': report.reporter_email,
                                        'reporter': str(report.reporter),
                                        'timestamp': str(report.timestamp),
                                        # 'picture' = models.ImageField(upload_to='report_images/', null=True, blank=True)
                                    }))
        else:
            messages.error(request, "Unsuccessful report. Invalid information.")
    else:
        form = ReportForm(authenticated=request.user.is_authenticated)
    return render(request=request, template_name="create_report.html", context={"form":form, "reportcomplete":report_complete, "report_id": report_id})


def reports(request):
    game = get_active_game()
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    reports = Report.objects.filter(game=game)
    context = {"reports": reports.order_by("-timestamp")}
    return render(request, "reports.html", context)

def report(request, report_id):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    report = Report.objects.get(report_uuid=report_id)
    if request.method == "POST":
        form = ReportUpdateForm(request.POST, report=report)
        if form.is_valid():
            form_reportees = set(form.cleaned_data['reportees'])
            new_update = form.instance
            new_update.note_creator = request.user
            new_update.report = Report.objects.get(report_uuid=report_id)
            existing_reportees = set(new_update.report.reportees.get_queryset())
            new_reportees = form_reportees - existing_reportees
            deleted_reportees = existing_reportees - form_reportees
            print(new_reportees)
            print(deleted_reportees)
            print(existing_reportees.intersection(form_reportees))
            new_update.report.reportees.set(form_reportees)
            new_update.report.save()
            if len(new_reportees) > 0 or len(deleted_reportees) > 0:
                new_note = ""
                if len(new_reportees) > 0:
                    new_note += f"-{request.user} added {', '.join([str(reportee) for reportee in new_reportees])} as Reportees-\n"
                if len(deleted_reportees) > 0:
                    new_note += f"-{request.user} removed {', '.join([str(reportee) for reportee in deleted_reportees])} as Reportees-"
                reportee_change_update = ReportUpdate.objects.create(note=new_note, note_creator=request.user, report=new_update.report)
                reportee_change_update.save()
            if form.cleaned_data['update_status'] != 'x':
                new_update.report.status = form.cleaned_data['update_status']
                new_update.report.save()
                status_change_update = ReportUpdate.objects.create(note=f"-{request.user} changed the status of this report to {new_update.report.status_text}-", note_creator=request.user, report=new_update.report)
                status_change_update.save()
            new_update.save()
            form = ReportUpdateForm(report=report)
    else:
        form = ReportUpdateForm(report=report)
    report = Report.objects.get(report_uuid=report_id)
    context = {
        'report': report,
        'form': form
    }
    return render(request, "report.html", context)


def rules_update(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    if request.method == "POST":
        form = RulesUpdateForm(request.POST)
        if form.is_valid():
            rules_obj = form.instance
            rules_obj.last_edited_by = request.user
            rules_obj.last_edited_datetime = timezone.localtime()
            rules_obj.save()
            return HttpResponseRedirect("/rules/")
    else:
        form = RulesUpdateForm(instance= Rules.load())
    rules = Rules.load()
    context = {
        'rules': rules,
        'form': form
    }
    return render(request, "rules_update.html", context)


def about_update(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    if request.method == "POST":
        form = AboutUpdateForm(request.POST)
        if form.is_valid():
            about_obj = form.instance
            about_obj.last_edited_by = request.user
            about_obj.last_edited_datetime = timezone.localtime()
            about_obj.save()
            return HttpResponseRedirect("/about/")
    else:
        form = AboutUpdateForm(instance=About.load())
    about = About.load()
    context = {
        'about': about,
        'form': form
    }
    return render(request, "about_update.html", context)


def print_one(request, player_uuid):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    context = {
        "players": Person.objects.filter(player_uuid=player_uuid),
        "preview": False,
        "print_one": True,
        "url": f"{request.scheme}://{get_current_site(request)}"
    }
    return render(request, "print_cards.html", context)


def print_ids(request, preview=False):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    to_print = PlayerStatus.objects.filter(printed=False, game=get_active_game()).filter(~Q(status='n')).order_by('player__first_name', 'player__last_name')
    context = {
        "players": [status.player for status in to_print],
        "preview": preview,
        "print_one": False,
        "url": f"{request.scheme}://{get_current_site(request)}"
    }
    return render(request, "print_cards.html", context)


#def print_ids_datetime(request, unix_timestamp, preview=False):
#    if not request.user.is_authenticated or not request.user.admin_this_game:
#        return HttpResponseRedirect("/")
#    to_print = PlayerStatus.objects.filter(game=get_active_game()).filter(~Q(status='n'))
#    context = {
#        "players": [status.player for status in to_print],
#        "preview": preview,
#        "print_one": False,
#        "url": f"{request.scheme}://{get_current_site(request)}"
#    }
#    return render(request, "print_cards.html", context)
#

def print_preview(request):
    return print_ids(request, True)


def mark_printed(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    PlayerStatus.objects.filter(printed=False, game=get_active_game()).filter(~Q(status='n')).update(printed=True)
    return HttpResponseRedirect("/")

def view_failed_av_list(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    offenders = Person.objects.annotate(failcount=Count("failed_av_attempts")).filter(failcount__gt=0).order_by("-failcount")
    context = {
        "offenders": offenders
    }
    return render(request, "failed_av_list.html", context)

## REST API endpoints

class ApiDiscordId(APIView):
    """
    Returns the player UUID associated with the given discord ID.

    @param id The discord id to be checked
    @return {
      discord-id: The input id
      player-id: The UUID of the player
      player-name: The full name of the player
    }
    """
    permission_classes = [HasAPIKey]

    def get(self, request):
        r = request.query_params

        if 'id' not in r:
            return HttpResponse(status=400, content='Missing field: "id"')
        discord_id = r.get('id')

        try:
            player = Person.objects.get(discord_id=discord_id)
        except Person.DoesNotExist:
            return HttpResponse(status=404, content='No player with the given discord id')

        data = {
            'discord-id': discord_id,
            'player-id': player.player_uuid,
            'player-name': str(player)
        }
        return JsonResponse(data)


class ApiLinkDiscordId(APIView):
    permission_classes = [HasAPIKey]

    def get(self, request):
        r = request.query_params

        if 'discord_id' not in r:
            return HttpResponse(status=400, content='Missing field: "discord_id"')
        if 'link_code' not in r:
            return HttpResponse(status=400, content='Missing field: "link_code"')
        discord_id = r.get('discord_id')
        link_code = r.get('link_code')

        try:
            code = DiscordLinkCode.objects.get(code=link_code)
        except DiscordLinkCode.DoesNotExist:
            return HttpResponse(status=404, content='Bad link code: does not exist')

        code.account.discord_id = discord_id
        code.account.save()
        code.delete()

        return HttpResponse('Successfully linked account')

    
class ApiMissions(APIView):
    permission_classes = [HasAPIKey]

    def get(self, request):
        r = request.query_params

        if 'team' not in r:
            return HttpResponse(status=400, content='Missing field: "team"')
        team = r.get('team')

        valid_teams = ['Human', 'Zombie', 'Staff']
        if team not in valid_teams:
            return HttpResponse(status=400, content='Invalid team, must be one of: '+str(valid_teams))

        missions = Mission.objects.filter(team__in=[team[0].lower(),'a'], game=get_active_game())

        data = {
            'missions': [
                {
                    'story-form': m.story_form,
                    'story-form-live-time': m.story_form_go_live_time,
                    'mission-text': m.mission_text,
                    'mission-text-live-time': m.go_live_time,
                }
                for m in missions]
        }
        return JsonResponse(data)

class ApiPlayerId(APIView):
    permission_classes = [HasAPIKey]

    def get(self, request):
        r = request.query_params

        if 'uuid' not in r:
            return HttpResponse(status=400, content='Missing field: "uuid"')
        player_id = r.get('uuid')

        try:
            player = Person.objects.get(player_uuid=player_id)
        except Person.DoesNotExist:
            return HttpResponse(status=404, content='No player with the given user id')

        data = {
            'uuid': player.player_uuid,
            'clan': player.clan,
            'email': player.email,
            'name': str(player),
            'status': player.current_status.status,
            'tags': player.current_status.num_tags,
        }
        return JsonResponse(data)

class ApiClans(APIView):
    def get(self, request):
        t = list(Clan.objects.values_list('name', flat=True))

        data = {
            'clans': t
        }
        return JsonResponse(data)


class ApiPlayers(APIView):
    '''
    Returns all player information
    '''
    def get(self, request):
        players = [
            {
                'name': str(p),
                'id': p.player_uuid,
                'status': p.current_status.get_status_display(),
                'tags': p.current_status.num_tags,
            } for p in Person.objects.all()
        ]
        
        data = {
            'players': players
        }
        return JsonResponse(data)


class ApiTag(APIView):
    permission_classes = [HasAPIKey]

    def post(self, request):
        r = request.query_params

        if 'tagger' not in r:
            return HttpResponse(status=400, content='Missing field: "tagger"')
        if 'taggee' not in r:
            return HttpResponse(status=400, content='Missing field: "taggee"')

        try:
            tagger = Person.objects.get(player_uuid=r['tagger'])
        except Person.DoesNotExist:
            return HttpResponse(status=404, content='No player with the given tagger id')

        try:
            taggee = PlayerStatus.objects.get(tag1_uuid=r['taggee'])
            if taggee.status == 'h':
                taggee.status = 'z'
            else:
                return HttpResponse(status=400, content='Invalid status, ensure the taggee ID is correct')
        except PlayerStatus.DoesNotExist:
            try:
                taggee = PlayerStatus.objects.get(tag2_uuid=r['taggee'])
                if taggee.status == 'v':
                    taggee.status = 'x'
                else:
                    return HttpResponse(status=400, content='Invalid status, ensure the taggee ID is correct')
            except PlayerStatus.DoesNotExist:
                return HttpResponse(status=404, content='No player with the given taggee id')

        
        tag = Tag.objects.create(tagger=tagger, taggee=taggee.player, game=get_active_game())
        taggee.save()
        tag.save()

        return HttpResponse(status=200)


class ApiReports(APIView):
    permission_classes = [HasAPIKey]

    def get(self, request):
        data = {
            'reports': [
                {
                    "report-text": report.report_text,
                    "reporter-email": report.reporter_email,
                    "reporter": str(report.reporter) if report.reporter else None, 
                    "timestamp": report.timestamp,
                    "status": report.status,
                }
                for report in Report.objects.all()],
        }
        return JsonResponse(data)


class ApiCreateAv(APIView):
    permission_classes = [HasAPIKey]

    def post(self, request):
        r = request.query_params

        if 'exp-time' not in r:
            return HttpResponse(status=400, content='Missing field: "exp-time"')

        try:
            if 'av-code' in r:
                av = AntiVirus.objects.create(av_code=r['av-code'], game=get_active_game(), expiration_time = r['exp-time'])
            else:
                av = AntiVirus.objects.create(game=get_active_game(), expiration_time = r['exp-time'])
        except exceptions.ValidationError:
            return HttpResponse(status=400, content='Invalid time format. It must be in YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ] format.')
        except IntegrityError:
            return HttpResponse(status=400, content='Cannot create duplicate AV code.')

        av.save()
        
        return HttpResponse('Successfully created AV: "{}"'.format(av.av_code))

class ApiCreateBodyArmor(APIView):
    permission_classes = [HasAPIKey]

    def post(self, request):
        r = request.query_params

        if 'exp-time' not in r:
            return HttpResponse(status=400, content='Missing field: "exp-time"')

        try:
            if 'armor-code' in r:
                armor = BodyArmor.objects.create(armor_code=r['armor-code'], game=get_active_game(), expiration_time = r['exp-time'])
            else:
                armor = BodyArmor.objects.create(game=get_active_game(), expiration_time = r['exp-time'])
        except exceptions.ValidationError:
            return HttpResponse(status=400, content='Invalid time format. It must be in YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ] format.')
        except IntegrityError:
            return HttpResponse(status=400, content='Cannot create duplicate BodyArmor code.')

        armor.save()

        return HttpResponse('Successfully created Body Armor: "{}"'.format(armor.armor_code))


def create_clan_view(request):
    if  not request.user.is_authenticated or \
        not request.user.active_this_game or \
        request.user.is_a_clan_leader:
        return HttpResponseRedirect("/")
    
    if request.method == "GET":     
        form = ClanCreateForm()
    else:
        form = ClanCreateForm(request.POST, request.FILES)

        if form.is_valid():
            newclan = form.save()
            newclan.leader = request.user
            newclan.save()
            request.user.clan = newclan
            request.user.save()
            new_history_item = ClanHistoryItem.objects.create(clan=newclan, actor=request.user, history_item_type='c')
            new_history_item.save()
            return HttpResponseRedirect(f"/clan/{newclan.name}/")
    return render(request, "create_clan.html", {'form':form,'newclan':True})

def manage_announcements(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    announcements = Announcement.objects.all().order_by('-post_time')
    return render(request, "manage_announcements.html", {'announcements':announcements})

def edit_announcement(request, announcement_id):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect("/")
    if request.method == "GET":
        if announcement_id == "new":
            form = AnnouncementForm()
        else:
            form = AnnouncementForm(instance=Announcement.objects.get(id=announcement_id))
    else:
        if announcement_id == "new":
            form = AnnouncementForm(request.POST)
        else:
            form = AnnouncementForm(request.POST, instance=Announcement.objects.get(id=announcement_id))

        if form.is_valid():
            announcement = form.save()
            return HttpResponseRedirect(f"/announcement/{announcement.id}/")
    return render(request, "edit_announcement.html", {'form':form})


def view_announcement(request, announcement_id):
    try:
        announcement = Announcement.objects.get(id=announcement_id)
        return render(request, "announcement.html", {'announcement':announcement})
    except:
        return HttpResponseRedirect("/")


def modify_clan_view(request, clan_name):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    try:
        clan = Clan.objects.get(name=clan_name)
    except:
        return HttpResponseRedirect("/")
    
    if not request.user == clan.leader:
        return HttpResponseRedirect("/")
    
    if request.method == "GET":     
        form = ClanCreateForm(instance=clan)
    else:
        form = ClanCreateForm(request.POST, request.FILES, instance=clan)

        if form.is_valid():
            old_name = clan.name
            old_photo = clan.picture.url
            form.save()
            new_name = clan.name
            new_photo = clan.picture.url
            if old_name != new_name:
                new_history_item = ClanHistoryItem.objects.create(clan=clan, actor=request.user, history_item_type='n', additional_info=f"from {old_name} to {new_name}")
                new_history_item.save()
            if old_photo != new_photo:
                new_history_item = ClanHistoryItem.objects.create(clan=clan, actor=request.user, history_item_type='p', additional_info=f"from {old_photo} to {new_photo}")
                new_history_item.save()
            return HttpResponseRedirect(f"/clan/{clan.name}/")
    return render(request, "create_clan.html", {'form':form,'newclan':False})


def badge_grant_list(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    if request.user.mod_this_game:
        grantable_badges = BadgeType.objects.filter(mod_grantable=True, active=True)
    elif request.user.admin_this_game:
        grantable_badges = BadgeType.objects.filter(active=True)
    else:
        return HttpResponseRedirect("/")
    return render(request, "badge_grant_list.html", {'badge_choices': grantable_badges})
    

def badge_grant(request, badge_type_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    try:
        badge_type = BadgeType.objects.get(id=badge_type_id, active=True)
    except:
        return HttpResponseRedirect("/")
    if (request.user.admin_this_game) or (request.user.mod_this_game and badge_type.mod_grantable):
        pass
    else:
        return HttpResponseRedirect("/")
    return render(request, "badge_grant.html", {'badge_type': badge_type})


@api_view(["POST"])
def badge_grant_api(request, badge_type_id, player_id):
    if not request.user.is_authenticated:
        return JsonResponse({"status":"not authorized"})
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
