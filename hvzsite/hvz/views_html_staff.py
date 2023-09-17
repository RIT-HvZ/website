from django.http import HttpResponseRedirect
from django.shortcuts import render

from .decorators import staff_required
from .models import BadgeType
from .views import for_all_methods


@for_all_methods(staff_required)
class StaffHTMLViews(object):
    def badge_grant_list(request):
        if request.user.mod_this_game:
            grantable_badges = BadgeType.objects.filter(mod_grantable=True, active=True)
        elif request.user.admin_this_game:
            grantable_badges = BadgeType.objects.filter(active=True)
        else:
            return HttpResponseRedirect("/")
        return render(request, "badge_grant_list.html", {'badge_choices': grantable_badges})
        

    def badge_grant(request, badge_type_id):
        try:
            badge_type = BadgeType.objects.get(id=badge_type_id, active=True)
        except:
            return HttpResponseRedirect("/")
        if (request.user.admin_this_game) or (request.user.mod_this_game and badge_type.mod_grantable):
            pass
        else:
            return HttpResponseRedirect("/")
        return render(request, "badge_grant.html", {'badge_type': badge_type})
