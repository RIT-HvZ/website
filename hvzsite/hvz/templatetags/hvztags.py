from django import template
from hvz.models import PostGameSurveyResponse, PostGameSurvey, Person, PlayerStatus

register = template.Library()

@register.simple_tag
def player_has_response(player, response):
    return PostGameSurveyResponse.objects.filter(player=player, response=response).count() > 0

@register.simple_tag
def can_respond_to_survey(player, survey):
    status = player.current_status
    return (survey.mission.team == 'h' and status.is_human()) or \
           (survey.mission.team == "z" and status.is_zombie()) or \
           status.is_admin()

@register.simple_tag
def get_player_response(player, survey):
    responses = PostGameSurveyResponse.objects.filter(player=player, survey=survey)
    if responses.count() > 0:
        return responses[0]
    return None

@register.simple_tag
def get_player_name(player, requesting_user):
    '''
    Get a readable name for the specified player.
    This is a wrapper to help avoid leaking player PII.

    Params:
      player: The player object to print the name of. This may be a Person, PlayerStatus, or str. If it is a str, it is printed raw (this is for convenience).
      requesting_user: The user that is requesting this player name to be printed

    Returns:
      str: The name of `player`, with the last name possibly obscured
    '''
    if player is None:
        return None

    if isinstance(player, str):
        return player

    if isinstance(player, PlayerStatus):
        player = player.player

    return player.readable_name(authed = requesting_user is not None and \
                                requesting_user.is_authenticated and \
                                requesting_user.active_this_game)

@register.simple_tag
def scoreboard_visible(scoreboard, requesting_user):
    if requesting_user.is_anonymous:
        return False

    return scoreboard.visible_to(requesting_user)

@register.filter
def strftime(date, fmt="%H:%M (%m/%d)"):
    return date.strftime(fmt)
