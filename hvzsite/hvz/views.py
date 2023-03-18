from datetime import datetime
from django.shortcuts import render, redirect
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from rest_framework.response import Response
from django.db.models import Count
from django.utils import timezone
from django.contrib.auth.models import Group
from rest_framework import viewsets
from rest_framework import permissions
from .serializers import UserSerializer, GroupSerializer
from .models import AntiVirus, Mission, Person, BadgeInstance, PlayerStatus, Tag, Blaster, Team, Report, ReportUpdate, Game, Rules, get_active_game, PostGameSurvey, PostGameSurveyResponse, PostGameSurveyOption, BodyArmor
from .forms import TagForm, AVForm, NewUserForm, LoginForm, AVCreateForm, BlasterApprovalForm, ReportUpdateForm, ReportForm, RulesUpdateForm, BodyArmorCreateForm, MissionForm, PostGameSurveyForm
from rest_framework.decorators import api_view
from django.contrib import messages
from django.contrib.auth import login, authenticate
from rest_framework.views import APIView
from rest_framework_api_key.models import APIKey
from rest_framework_api_key.permissions import HasAPIKey
import json 

# Create your views here.
def index(request):
    game = get_active_game()
    humancount = PlayerStatus.objects.filter(game=game).filter(Q(status='h') | Q(status='v')).count()
    zombiecount = PlayerStatus.objects.filter(game=game).filter(Q(status='z') | Q(status='x') | Q(status='o')).count()
    return render(request, "index.html", {'humancount': humancount, 'zombiecount': zombiecount})

def me(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    return player_view(request, request.user.player_uuid, is_me=True)

def infection(request):
    game = get_active_game()
    ozs = PlayerStatus.objects.filter(game=game, status='o')
    tags = Tag.objects.filter(game=game)
    return render(request, "infection.html", {'ozs':ozs, 'tags':tags})

def register(request):
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful." )
            return index(request)
        messages.error(request, "Unsuccessful registration. Invalid information.")
    form = NewUserForm()
    return render (request=request, template_name="register.html", context={"register_form":form})

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
        if (survey.mission.team == 'h' and status.is_human()) or (survey.mission.team == "z" and status.is_zombie()) or status.is_admin():
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
                new_response = PostGameSurveyOption.objects.create(player=request.user, survey=survey, response=response)
                new_response.save()
                print(f"New response: {new_response}")
        else:
            return HttpResponseRedirect("/")
    if request.user.current_status.is_zombie():
        missions = Mission.objects.filter(game=this_game, team='z', story_form_go_live_time__lt=timezone.now())
    elif request.user.current_status.is_human():
        missions = Mission.objects.filter(game=this_game, team='h', story_form_go_live_time__lt=timezone.now())
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
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    player = request.user
    if player.current_status.is_zombie():
        qr = player.current_status.zombie_uuid
    elif player.current_status.status == 'h':
        qr = player.current_status.tag1_uuid
    elif player.current_status.status == 'v':
        qr = player.current_status.tag2_uuid
    else:
        qr = None
    if request.method == "GET":
        data = {}
        player = request.user
        status = player.current_status
        if status.is_zombie():
            data['tagger_id'] = status.zombie_uuid
        elif status.is_human():
            if status.status == 'h':
                data['taggee_id'] = status.tag1_uuid
            elif status.status == 'v':
                data['taggee_id'] = status.tag2_uuid
        prefilled_zombie = request.GET.get('z',None)
        prefilled_human = request.GET.get('h',None)
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
                tag.save()
                if form.cleaned_data['taggee'].status == 'v':
                    form.cleaned_data['taggee'].status = 'x'
                else:
                    form.cleaned_data['taggee'].status = 'z'
                form.cleaned_data['taggee'].save()
            else:
                tag = Tag.objects.create(tagger=form.cleaned_data['tagger'].player, armor_taggee=form.cleaned_data['taggee'], game=get_active_game())
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
    return render(request, "av.html", {'form':form, 'avcomplete': False})

def blasterapproval(request):
    if (not request.user.is_authenticated) or (not request.user.admin_this_game):
        return HttpResponseRedirect("/")
    if request.method == "GET":     
        form = BlasterApprovalForm()
        form.fields['owner'].queryset = Person.objects.filter(playerstatus__game=get_active_game()) \
                                                      .filter(playerstatus__status__in=['h','v','z','o','x']) \
                                                      .annotate(num_status=Count('playerstatus')) \
                                                      .filter(num_status=1)
    else:
        form = BlasterApprovalForm(request.POST, request.FILES)
        if form.is_valid():
            print("AHHH")
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

def player_view(request, player_id, is_me=False, game=None):
    player = Person.objects.get(player_uuid=player_id)
    if game is None:
        game = get_active_game()
    context = {
        'player': player,
        'is_me': is_me,
        'badges': BadgeInstance.objects.filter(player=player), 
        'tags': Tag.objects.filter(tagger=player, game=game),
        'status': PlayerStatus.objects.get_or_create(player=player, game=game)[0],
        'blasters': Blaster.objects.filter(owner=player, game_approved_in=game),
        'domain': request.build_absolute_uri('/tag/')
    }
    return render(request, "player.html", context)

def player_admin_tools(request, player_id, command):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect('/')

    try:
        player = Person.objects.get(player_uuid = player_id)
        playerstatus = PlayerStatus.objects.get(player = player, game = get_active_game())
    except:
        return HttpResponseRedirect('/')

    if command == "make_oz":
        playerstatus.status = 'o'
    if command == "make_nonplayer":
        playerstatus.status = 'n'
    if command == "make_human":
        playerstatus.status = 'h'
    if command == "make_human_av":
        playerstatus.status = 'v'
    if command == "make_zombie":
        playerstatus.status = 'z'
    if command == "make_zombie_av":
        playerstatus.status = 'x'
    if command == "make_mod":
        playerstatus.status = 'm'
    playerstatus.save()

    return player_view(request, player_id, False)

def team_view(request, team_name):
    team = Team.objects.get(name=team_name)
    context = {
        'team': team,
        'roster': Person.objects.filter(team=team)
    }
    return render(request, "team.html", context)


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
        assert order_column_name in ("name","status","tags","team")
        order_direction = r.get("order[0][dir]")
        assert order_direction in ("asc","desc")
        limit = int(request.query_params["length"])
        start = int(request.query_params["start"])
        search = r["search[value]"] 
    except AssertionError:
        raise
    query = Person.full_name_objects.filter(playerstatus__game=game).filter(playerstatus__status__in=['h','v','z','o','x','a','m'])
    if search != "":
        query = query.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(team__name__icontains=search))
    if order_column_name != "tags":
        query = query.order_by(f"""{'-' if order_direction == 'desc' else ''}{ {"name":"full_name", "status": "playerstatus__status", "team": "team__name"}[order_column_name]}""")
    else:
        query = query.annotate(n_tags=Count('taggers', filter=Q(taggers__game=game))).order_by(f"""{'-' if order_direction == 'asc' else ''}n_tags""")
    result = []
    for person in query[start:limit]:
        try:
            person_status = PlayerStatus.objects.get(player=person, game=game)
        except:
            continue
        if person_status.status == "n":
            continue
        result.append({
            "name": f"""<a class="dt_name_link" href="/player/{person.player_uuid}/">{person.first_name} {person.last_name}</a>""",
            "pic": f"""<a class="dt_profile_link" href="/player/{person.player_uuid}/"><img src='{person.picture.url}' class='dt_profile' /></a>""",
            "status": {"h": "Human", "a": "Admin", "z": "Zombie", "m": "Mod", "v": "Human", "o": "Zombie", "n": "NonPlayer", "x": "Zombie"}[person_status.status],
            "team": None if person.team is None else (f"""<a href="/team/{person.team.name}/" class="dt_team_link">person.team.name</a>""" if (person.team is None or person.team.picture is None) else f"""<a href="/team/{person.team.name}/" class="dt_team_link"><img src='{person.team.picture.url}' class='dt_teampic' alt='{person.team}' /><span class="dt_teamname">{person.team}</span></a>"""),
            "team_pic": None if (person.team is None or person.team.picture is None) else person.team.picture.url,
            "tags": Tag.objects.filter(tagger=person,game=game).count(),
            "DT_RowClass": {"h": "dt_human", "v": "dt_human", "a": "dt_admin", "z": "dt_zombie", "o": "dt_zombie", "n": "dt_nonplayer", "x": "dt_zombie"}[person_status.status],
            "DT_RowData": {"person_url": f"/player/{person.player_uuid}/", "team_url": f"/team/{person.team.name}/" if person.team is not None else ""}
        })
    data = {
        "draw": int(r['draw']),
        "recordsTotal": Person.objects.all().count(),
        "recordsFiltered": len(result),
        "data": result
    }
    return JsonResponse(data)


def player_activation(request):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        return HttpResponseRedirect('/')
    context = {}
    return render(request, "player_activation.html", context)

@api_view(["GET"])
def player_activation_api(request, game=None):
    if not request.user.is_authenticated or not request.user.admin_this_game:
        print("Not admin")
        return JsonResponse({})

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
    query = Person.full_name_objects.all()
    if search != "":
        query = query.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(team__name__icontains=search))
    query = query.order_by(f"""{'-' if order_direction == 'desc' else ''}{ {"name":"full_name"}[order_column_name]}""")
    result = []
    for person in query[start:limit]:
        try:
            person_status = PlayerStatus.objects.get_or_create(player=person, game=game)[0]
        except:
            continue
        if person.active_this_game:
            continue
        result.append({
            "name": f"""{person.first_name} {person.last_name}""",
            "pic": f"""<img src='{person.picture.url}' class='dt_profile' />""",
            "email": f"""{person.email}""",
            "DT_RowClass": {"h": "dt_human", "v": "dt_human", "a": "dt_admin", "z": "dt_zombie", "o": "dt_zombie", "n": "dt_nonplayer"}[person_status.status],
            "activation_link": f"""<button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#activationmodal" data-bs-activationname="{person.first_name} {person.last_name}" data-bs-activationid="{person.player_uuid}">Activate</button>"""
        })
    data = {
        "draw": int(r['draw']),
        "recordsTotal": Person.objects.all().count(),
        "recordsFiltered": len(result),
        "data": result
    }
    return JsonResponse(data)


@api_view(["POST"])
def player_activation_rest(request):
    game = get_active_game()
    if not request.user.is_authenticated or not request.user.admin_this_game:
        print("Not admin")
        return JsonResponse({"status":"error","error":"Not Authorized"})
    print(request.POST["activated_player"])
    import time
    time.sleep(1)
    try:
        requested_player = Person.objects.get(player_uuid=request.POST["activated_player"])
        person_status = PlayerStatus.objects.get(player=requested_player, game=game)
        person_status.status = 'h'
        person_status.save()
        return JsonResponse({"status":"success"})
    except Exception as e:
        return JsonResponse({"status":"error", "error": str(e)})


def teams(request):
    context = {}
    return render(request, "teams.html", context)


@api_view(["GET"])
def teams_api(request):
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
    query = Team.objects.all()
    if search != "":
        query = query.filter(name__icontains=search)
    query = query.order_by(f"""{'-' if order_direction == 'desc' else ''}{ {"name":"name", "size": "persons_count", }[order_column_name]}""")
    result = []
    for team in query[start:limit]:
        result.append({
            "name": f"""<a class="dt_name_link" href="/team/{team.name}/">{team.name}</a>""",
            "pic": f"""<a class="dt_profile_link" href="/team/{team.name}/"><img src='{team.picture.url}' class='dt_profile' /></a>""",
            "size": team.team_members.count()
        })
    data = {
        "draw": int(r['draw']),
        "recordsTotal": Team.objects.all().count(),
        "recordsFiltered": len(result),
        "data": result
    }
    return JsonResponse(data)

def rules(request):
    return render(request, "rules.html", {'rules': Rules.load()})

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

def create_report(request):
    report_complete = False
    report_id = None
    if request.method == "POST":
        form = ReportForm(request.POST, request.FILES, authenticated=request.user.is_authenticated)
        print(form.fields)
        if form.is_valid():
            report = form.instance
            report.game = get_active_game()
            if request.user.is_authenticated:
                report.reporter = request.user
            report.status = "n"
            report.save()
            report_complete = True
            report_id = report.id
            form = ReportForm(authenticated=request.user.is_authenticated)
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
    if request.method == "POST":
        form = ReportUpdateForm(request.POST)
        if form.is_valid():
            new_update = form.instance
            new_update.note_creator = request.user
            new_update.report = Report.objects.get(id=report_id)
            if form.cleaned_data['update_status'] != 'x':
                new_update.report.status = form.cleaned_data['update_status']
                new_update.report.save()
                status_change_update = ReportUpdate.objects.create(note=f"-{request.user} changed the status of this report to {new_update.report.status_text}-", note_creator=request.user, report=new_update.report)
                status_change_update.save()
            new_update.save()
            form = ReportUpdateForm()
    else:
        form = ReportUpdateForm()
    report = Report.objects.get(id=report_id)
    context = {
        'report': report,
        'form': form
    }
    return render(request, "report.html", context)


def rules_udpate(request):
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


## REST API endpoints

class ApiDiscordId(APIView):
    permission_classes = [HasAPIKey]

    def get(self, request):
        r = request.query_params

        if 'id' not in r:
            return HttpResponse(status=400, reason='Bad request, missing field: "id"')
        discord_id = r.get('id')

        try:
            player = Person.objects.get(discord_id=discord_id)
        except Person.DoesNotExist:
            return HttpResponse(status=404, reason='No player with the given discord id')

        data = {
            'discord-id': discord_id,
            'player-id': player.player_uuid,
            'player-name': str(player)
        }
        return JsonResponse(data)

class ApiPlayerId(APIView):
    permission_classes = [HasAPIKey]

    def get(self, request):
        r = request.query_params

        if 'uuid' not in r:
            return HttpResponse(status=400, reason='Bad request, missing field: "uuid"')
        player_id = r.get('uuid')

        try:
            player = Person.objects.get(player_uuid=player_id)
        except Person.DoesNotExist:
            return HttpResponse(status=404, reason='No player with the given user id')

        data = {
            'uuid': player.player_uuid,
            'team': player.team,
            'email': player.email,
            'name': str(player),
            'status': player.current_status.status,
        }
        return JsonResponse(data)

class ApiTeams(APIView):
    def get(self, request):
        t = list(Team.objects.values_list('name', flat=True))

        data = {
            'teams': t
        }
        return JsonResponse(data)