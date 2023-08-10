from hvz.models import Person

def is_player_banned(request):
    return {'is_banned': (request.user.is_authenticated and request.user.is_banned)}