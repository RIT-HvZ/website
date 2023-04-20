from django import template
from hvz.models import PostGameSurveyResponse, PostGameSurvey
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


@register.filter
def strftime(date, fmt="%H:%M (%m/%d)"):
    return date.strftime(fmt)

