from django import template
from hvz.models import PostGameSurveyResponse, PostGameSurvey
from django.utils import timezone
register = template.Library()

@register.simple_tag
def player_has_response(player, response):
    return PostGameSurveyResponse.objects.filter(player=player, response=response).count() > 0

@register.simple_tag
def get_player_response(player, survey):
    responses = PostGameSurveyResponse.objects.filter(player=player, survey=survey)
    if responses.count() > 0:
        return responses[0]
    return None

@register.simple_tag
def can_respond_to_survey(player, survey):
    status = player.current_status
    return (survey.mission.team == 'h' and status.is_human()) or \
           (survey.mission.team == "z" and status.is_zombie()) or \
           status.is_admin()

@register.filter
def strftime(date, fmt="%H:%M (%m/%d)"):
    return date.strftime(fmt)
