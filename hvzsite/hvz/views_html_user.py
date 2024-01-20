from datetime import timedelta

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone

from .decorators import authentication_required
from .forms import ClanCreateForm, NameChangeForm
from .models import Clan, ClanHistoryItem, DiscordLinkCode, NameChangeRequest
from .models import get_active_game
from .views import for_all_methods, player_view

@for_all_methods(authentication_required)
class UserHTMLViews(object):
    def me(request):
        return player_view(request, request.user.player_uuid)

    def discord_link(request):
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
        
        return player_view(request, request.user.player_uuid, discord_code=code.code)


    def modify_clan_view(request, clan_name):
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


    def name_change(request):
        existing_requests = NameChangeRequest.objects.filter(player=request.user, request_status='n')
        if existing_requests.count() > 0:
            existing_request = existing_requests[0]
        else:
            existing_request = None

        if request.method == "GET":
            form = NameChangeForm()
        else:
            form = NameChangeForm(request.POST)

            if form.is_valid():
                if existing_request:
                    existing_request.requested_first_name = form.cleaned_data['first_name']
                    existing_request.requested_last_name = form.cleaned_data['last_name']
                    existing_request.save()
                else:
                    new_request = NameChangeRequest.objects.create(previous_first_name=request.user.first_name, previous_last_name=request.user.last_name, requested_first_name=form.cleaned_data['first_name'], requested_last_name=form.cleaned_data['last_name'], player=request.user)
                    new_request.save()
                    existing_request = new_request
                newform = NameChangeForm()
                return render(request, "name_change.html", {'form':newform, 'requestcomplete': True, 'existing_request': existing_request})
        return render(request, "name_change.html", {'form':form, 'requestcomplete': False, 'existing_request': existing_request})


    def cancel_name_change(request):
        existing_requests = NameChangeRequest.objects.filter(player=request.user, request_status='n')
        if existing_requests.count() > 0:
            existing_request = existing_requests[0]
            existing_request.request_status = 'c'
            existing_request.request_close_timestamp = timezone.now()
            existing_request.save()
        return UserHTMLViews.name_change(request)
