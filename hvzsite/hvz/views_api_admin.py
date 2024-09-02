import base64, html, random, sys

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from io import BytesIO
from PIL import Image
from rest_framework.decorators import api_view

from .decorators import admin_required_api
from .models import BodyArmor, Clan, ClanHistoryItem, NameChangeRequest, OZEntry, Person, PlayerStatus, Tag
from .models import get_active_game, generate_tag_id

from .views import for_all_methods
from .views_html_admin import AdminHTMLViews


@for_all_methods(admin_required_api)
class AdminAPIViews(object):
    def admin_tag_api(request, tag_id, command):
        requested_tag = Tag.objects.get(id=tag_id)
        if command == "invalidate":
            if requested_tag.taggee.current_status.status == "z":
                requested_tag.taggee.current_status.status = "h"
            else:
                requested_tag.taggee.current_status.status = "v"
            requested_tag.taggee.current_status.save()
            requested_tag.delete()
            return JsonResponse({"status":"success"})
        return JsonResponse({"status": "unknown command"})
  
    @api_view(["POST"])
    def player_admin_tools(request, player_id, command):
        try:
            player = Person.objects.get(player_uuid = player_id)
            playerstatus = PlayerStatus.objects.get(player = player, game = get_active_game())
        except:
            return JsonResponse({"status": "player not found"})
        if command == "print_id":
            return AdminHTMLViews.print_one(request, player_id)
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
        elif command == "mark_waiver":
            playerstatus.waiver_signed = True
        elif command == "unmark_waiver":
            playerstatus.waiver_signed = False
        elif command == "avunban":
            playerstatus.av_banned = False
        elif command == "regenerate_tag1":
            playerstatus.tag1_uuid = generate_tag_id()
        elif command == "regenerate_tag2":
            playerstatus.tag2_uuid = generate_tag_id()
        elif command == "regenerate_zombie":
            playerstatus.zombie_uuid = generate_tag_id()
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
            return JsonResponse({'status': 'success', "playername": player.readable_name(True), "time": str(armor.loaned_at)})
            

    @api_view(["GET"])
    def bodyarmor_get_loan_targets(request):
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
                    "name": f"""<a class="dt_name_link" href="/player/{person.player_uuid}/">{person.readable_name(True)}</a>""",
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


    #TODO: Returning raw HTML to embed in the page is a bad idea, find a better solution
    @api_view(["GET"])
    def player_activation_api(request, game=None):
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
        records_total = query.count()
        if search != "":
            query = query.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(clan__name__icontains=search))
        query = query.order_by(f"""{'-' if order_direction == 'desc' else ''}{ {"name":"full_name"}[order_column_name]}""")
        result = []
        filtered_length = len(query)
        if start < filtered_length:
            for person in query[start:]:
                if limit == 0:
                    break
                disabled = ''
                if not person.current_status.is_nonplayer():
                    disabled = 'disabled'
                result.append({
                    "name": f"""{html.escape(person.readable_name(True))}""",
                    "pic": f"""<img src='{person.picture_url}' class='dt_profile' />""",
                    "email": f"""{html.escape(person.email)}""",
                    "DT_RowClass": {"h": "dt_human", "v": "dt_human", "a": "dt_admin", "z": "dt_zombie", "o": "dt_zombie", "n": "dt_nonplayer", "x": "dt_zombie", "m": "dt_mod"}[person.current_status.status],
                    "activation_link": f"""<button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#activationmodal" data-bs-activationname="{html.escape(person.first_name)} {html.escape(person.last_name)}" data-bs-activationid="{person.player_uuid}" {disabled}>Register</button>"""
                })
                limit -= 1
        data = {
            "draw": int(r['draw']),
            "recordsTotal": records_total,
            "recordsFiltered": filtered_length,
            "data": result
        }
        return JsonResponse(data)


    @api_view(["POST"])
    def player_activation_rest(request):
        game = get_active_game()
        try:
            requested_player = Person.objects.get(player_uuid=request.POST["activated_player"])
            image_base64 = request.POST['player_photo'].replace('data:image/jpeg;base64,', '').replace(" ","+")
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
            # Going forward, always assume all players have signed a waiver
            person_status.waiver_signed = True #(request.POST["waiver_signed"] == "true")
            requested_player.save()
            person_status.save()
            return JsonResponse({"status":"success"})
        except Exception as e:
            return JsonResponse({"status":"error", "error": str(e)})


    @api_view(["GET"])
    def player_oz_activation_api(request, game=None):
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
                "name": f"{player_status.player.readable_name(True)}",
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


    @api_view(["POST"])
    def name_change_response(request, request_id, command):
        name_change_req = NameChangeRequest.objects.get(id=request_id)
        name_change_req.request_close_timestamp = timezone.now()
        if command == "approve":
            name_change_req.request_status = 'a'
            player = name_change_req.player
            player.first_name = name_change_req.requested_first_name
            player.last_name = name_change_req.requested_last_name
            player.save()
            name_change_req.save()
            return JsonResponse({"status": "success"})
        elif command == "deny":
            name_change_req.request_status = 'r'
            name_change_req.save()
            return JsonResponse({"status": "success"})
        else:
            return JsonResponse({"status": "unknown command"})

    @api_view(["GET"])
    def get_cullable_accounts(request):
        r = request.query_params
        try:
            order_column = int(r.get("order[0][column]"))
            order_column_name = r.get(f"columns[{order_column}][name]")
            print(f"Order column name: {order_column_name}")
            order_direction = r.get("order[0][dir]")
            assert order_direction in ("asc","desc")
            limit = int(request.query_params["length"])
            start = int(request.query_params["start"])
            search = r["search[value]"]
        except AssertionError:
            raise
        query = Person.full_name_objects.exclude(playerstatus__status__in=['h','v','e','z','o','m','a'])
        records_total = query.count()
        if search != "":
            query = query.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(clan__name__icontains=search))
        query = query.order_by(f"""{'-' if order_direction == 'desc' else ''}{ {"name":"full_name","creationdate":"date_joined"}[order_column_name]}""")
        result = []
        filtered_length = len(query)
        if start < filtered_length:
            for person in query[start:]:
                if limit == 0:
                    break
                result.append({
                    "name": f"""{html.escape(person.readable_name(True))}""",
                    "creationdate": f"""{person.date_joined}""",
                    "gamesplayed": f"""{PlayerStatus.objects.filter(player=person, status__in=['h','v','e','z','o','m','a']).count()}""",
                    "email": f"""{html.escape(person.email)}""",
                    "DT_RowClass": "dt_nonplayer",
                    "activation_link": f"""<button type="button" class="btn btn-danger" data-account-uuid="{person.player_uuid}" onclick="handle_delete(this)">Delete Account</button>"""
                })
                limit -= 1
        data = {
            "draw": int(r['draw']),
            "recordsTotal": records_total,
            "recordsFiltered": filtered_length,
            "data": result
        }
        return JsonResponse(data)
    
    @api_view(["POST"])
    def account_culling_rest(request):
        try:
            requested_player = Person.objects.get(player_uuid=request.POST["deleted_player"])
            requested_player.delete()
            return JsonResponse({"status":"success"})
        except Exception as e:
            return JsonResponse({"status":"error", "error": str(e)})
