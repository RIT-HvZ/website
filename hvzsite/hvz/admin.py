from django.contrib import admin

# Register your models here.

from django.contrib.auth.admin import UserAdmin
from .models import *

admin.site.register(Game)
admin.site.register(Mission)
admin.site.register(Person)
admin.site.register(PlayerStatus)
admin.site.register(BadgeType)
admin.site.register(BadgeInstance)
admin.site.register(Tag)
admin.site.register(Blaster)
admin.site.register(Team)
admin.site.register(AntiVirus)
admin.site.register(PostGameSurvey)
admin.site.register(PostGameSurveyOption)
admin.site.register(PostGameSurveyResponse)
admin.site.register(Report)
admin.site.register(ReportUpdate)
admin.site.register(BodyArmor)
admin.site.register(Rules)
admin.site.register(DiscordLinkCode)
admin.site.register(CurrentGame)
