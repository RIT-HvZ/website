from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone


from .decorators import active_player_required
from .forms import AVForm, ClanCreateForm, Mission, TagForm
from .models import ClanHistoryItem, FailedAVAttempt, PlayerStatus, PostGameSurveyOption, PostGameSurveyResponse, Tag
from .models import get_active_game
from .views import for_all_methods


@for_all_methods(active_player_required)
class ActivePlayerHTMLViews(object):
    def tag(request):
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


    def create_clan_view(request):
        if request.user.is_a_clan_leader:
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


    def av(request):
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
                form.cleaned_data['av'].time_used = timezone.now()
                form.cleaned_data['av'].save()
                newform = AVForm()
                return render(request, "av.html", {'form':newform, 'avcomplete': True, 'av': form.cleaned_data['av']})
            else:
                new_failed_av = FailedAVAttempt.objects.create(player=request.user, game=get_active_game(), code_used=form.cleaned_data['av_code'])
                new_failed_av.save()
        return render(request, "av.html", {'form':form, 'avcomplete': False})


    def missions_view(request):
        if not request.user.admin_this_game and not request.user.current_status.waiver_signed:
            return render(request, "sign_waiver.html")
        this_game = get_active_game()
        if request.method == "POST":
            survey_option = request.POST.get("survey_option")
            if not survey_option or not str(survey_option).isnumeric():
                return HttpResponseRedirect('/')
            response = PostGameSurveyOption.objects.get(id=survey_option)
            survey = response.survey
            if not survey.is_open:
                return HttpResponseRedirect("/")
            status = request.user.current_status
            # See if we have an existing Response for this survey
            existing_responses = PostGameSurveyResponse.objects.filter(survey=survey, player=request.user)
            if (survey.mission.team == 'h' and status.is_human()) or (survey.mission.team == "z" and status.is_zombie()) or status.is_admin() or survey.mission.team == "a":
                # All authorization steps complete
                if existing_responses.count() > 0:
                    # A response for this survey for this user already exists. Update it.
                    existing_response = existing_responses[0]
                    existing_response.response = response
                    existing_response.save()
                else:
                    # No response for this survey for this user exists. Create one.
                    new_response = PostGameSurveyResponse.objects.create(player=request.user, survey=survey, response=response)
                    new_response.save()
            else:
                return HttpResponseRedirect("/")
        if request.user.current_status.is_zombie():
            missions = Mission.objects.filter(game=this_game, team__in=['a','z'], story_form_go_live_time__lt=timezone.now())
        elif request.user.current_status.is_human():
            missions = Mission.objects.filter(game=this_game, team__in=['a','h'], story_form_go_live_time__lt=timezone.now())
        elif request.user.current_status.is_staff():
            missions = Mission.objects.filter(game=this_game, story_form_go_live_time__lt=timezone.now())
        return render(request, "missions.html", {'missions':missions.order_by("-story_form_go_live_time")})

