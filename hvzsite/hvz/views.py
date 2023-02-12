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
from .models import AntiVirus, Mission, Person, BadgeInstance, PlayerStatus, Tag, Blaster, Team, Game, get_latest_game
from .forms import TagForm, AVForm, NewUserForm, LoginForm, AVCreateForm
from rest_framework.decorators import api_view
from django.contrib import messages
from django.contrib.auth import login, authenticate
import json 

# Create your views here.
def index(request):
    context = {}
    return render(request, "index.html", context)

def me(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    return player_view(request, request.user.player_uuid)

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data['email'], password=form.cleaned_data['password'])
            if user is not None:
                login(request, user)
                messages.success(request, "Login successful.")
                return index(request)
            else:
                messages.error(request, "Unsuccessful login.")
        else:
            messages.error(request, "Unsuccessful login.")
    form = LoginForm()
    context = {"login_form": form}
    return render(request, "login.html", context)

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
    if request.user.current_status.is_zombie():
        missions = Mission.objects.filter(game=get_latest_game(), team='z', go_live_time__lt=timezone.now())
    elif request.user.current_status.is_human():
        missions = Mission.objects.filter(game=get_latest_game(), team='h', go_live_time__lt=timezone.now())
    elif request.user.current_status.is_staff():
        missions = Mission.objects.filter(game=get_latest_game(), go_live_time__lt=timezone.now())
    missions.order_by("go_live_time")
    return render(request, "missions.html", {'missions':missions})

def tag(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    if request.method == "GET":     
        form = TagForm()
    else:
        form = TagForm(request.POST)
        if form.is_valid():
            tag = Tag.objects.create(tagger=form.cleaned_data['tagger'].player, taggee=form.cleaned_data['taggee'].player, game=get_latest_game())
            tag.save()
            form.cleaned_data['taggee'].status = 'z'
            form.cleaned_data['taggee'].save()
            form = TagForm()
            return render(request, "tag.html", {'form':form, 'tagcomplete': True, 'tag': tag})
    return render(request, "tag.html", {'form':form, 'tagcomplete': False})

def av(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    if request.method == "GET":     
        form = AVForm()
    else:
        form = AVForm(request.POST)
        if form.is_valid():
            form.cleaned_data['player'].status = 'v'
            form.cleaned_data['player'].save()
            form.cleaned_data['av'].used_by = form.cleaned_data['player'].player
            form.cleaned_data['av'].time_used = datetime.now()
            form.cleaned_data['av'].save()
            newform = AVForm()
            return render(request, "av.html", {'form':newform, 'tagcomplete': True, 'av': form.cleaned_data['av']})
    return render(request, "av.html", {'form':form, 'tagcomplete': False})

def blasterapproval(request):
    pass
#    if (not request.user.is_authenticated) or (not request.user.current_status.is_admin()):
#        return HttpResponseRedirect("/")
#    if request.method == "GET":     
#        form = AVForm()
#    else:
#        form = AVForm(request.POST)
#        if form.is_valid():
#            form.cleaned_data['player'].status = 'v'
#            form.cleaned_data['player'].save()
#            form.cleaned_data['av'].used_by = form.cleaned_data['player'].player
#            form.cleaned_data['av'].time_used = datetime.now()
#            form.cleaned_data['av'].save()
#            newform = AVForm()
#            return render(request, "av.html", {'form':newform, 'tagcomplete': True, 'av': form.cleaned_data['av']})
#    return render(request, "av.html", {'form':form, 'tagcomplete': False})

def admin_create_av(request):
    # if not request.user.is_authenticated:
    #     return HttpResponseRedirect("/")

    # if not request.user.admin_this_game():
    #     return HttpResponseRedirect("/")
    
    if request.method == "GET":     
        form = AVCreateForm()
    else:
        form = AVCreateForm(request.POST)

        if form.is_valid():
            av = form.save()
            newform = AVCreateForm()
            return render(request, "create_av.html", {'form':newform, 'createcomplete': True})
    return render(request, "create_av.html", {'form':form, 'createcomplete': False})


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

def player_view(request, player_id, game=None):
    player = Person.objects.get(player_uuid=player_id)
    if game is None:
        game = get_latest_game()
    context = {
        'player': player,
        'badges': BadgeInstance.objects.filter(player=player), 
        'tags': Tag.objects.filter(tagger=player, game=game),
        'status': PlayerStatus.objects.get_or_create(player=player, game=game)[0],
        'blasters': Blaster.objects.filter(owner=player, game_approved_in=game)
    }
    return render(request, "player.html", context)

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
        game = get_latest_game()
    r = request.query_params
    print(json.dumps(r, indent=4))
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
    query = Person.full_name_objects.all()
    if search != "":
        query = query.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(team__name__icontains=search))
    if order_column_name != "tags":
        query = query.order_by(f"""{'-' if order_direction == 'desc' else ''}{ {"name":"full_name", "status": "status", "team": "team__name"}[order_column_name]}""")
    else:
        query = query.annotate(num_tags=Count('taggers', filter=Q(game=game))).order_by(f"""{'-' if order_direction == 'asc' else ''}num_tags""")
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
            "status": {"h": "Human", "a": "Admin", "z": "Zombie", "m": "Mod", "v": "Human", "o": "Zombie", "n": "NonPlayer"}[person_status.status],
            "team": None if person.team is None else (f"""<a href="/team/{person.team.name}/" class="dt_team_link">person.team.name</a>""" if (person.team is None or person.team.picture is None) else f"""<a href="/team/{person.team.name}/" class="dt_team_link"><img src='{person.team.picture.url}' class='dt_teampic' alt='{person.team}' /><span class="dt_teamname">{person.team}</span></a>"""),
            "team_pic": None if (person.team is None or person.team.picture is None) else person.team.picture.url,
            "tags": Tag.objects.filter(tagger=person,game=game).count(),
            "DT_RowClass": {"h": "dt_human", "v": "dt_human", "a": "dt_admin", "z": "dt_zombie", "o": "dt_zombie", "n": "dt_nonplayer"}[person_status.status],
            "DT_RowData": {"person_url": f"/player/{person.player_uuid}/", "team_url": f"/team/{person.team.name}/" if person.team is not None else ""}
        })
    data = {
        "draw": int(r['draw']),
        "recordsTotal": Person.objects.all().count(),
        "recordsFiltered": len(result),
        "data": result
    }
    return JsonResponse(data)

def teams(request):
    context = {}
    return render(request, "teams.html", context)


@api_view(["GET"])
def teams_api(request):
    r = request.query_params
    print(json.dumps(r, indent=4))
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