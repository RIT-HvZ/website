from datetime import timedelta

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone

from .decorators import authentication_required
from .forms import ClanCreateForm
from .models import Clan, ClanHistoryItem, DiscordLinkCode
from .models import get_active_game
from .views import for_all_methods, player_view


@for_all_methods(authentication_required)
class UserHTMLViews(object):
    def me(request):
        return player_view(request, request.user.player_uuid, is_me=True)

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
        
        return player_view(request, request.user.player_uuid, is_me=True, discord_code=code.code)


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
