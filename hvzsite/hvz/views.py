from webbrowser import get
from django.shortcuts import render
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from rest_framework.response import Response
from django.db.models import Count
from django.contrib.auth.models import Group
from rest_framework import viewsets
from rest_framework import permissions
from .serializers import UserSerializer, GroupSerializer
from .models import Person, BadgeInstance, PlayerStatus, Tag, Blaster, Team, Game, get_latest_game
from rest_framework.decorators import api_view
import json 

# Create your views here.
def index(request):
    context = {}
    return render(request, "index.html", context)

def me(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/")
    return player_view(request, request.user.player_uuid)

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