from django.contrib import admin

from .models import *


# Register your models here.

class PersonAdmin(admin.ModelAdmin):
    search_fields = ["first_name","last_name","email","player_uuid"]

class PlayerStatusAdmin(admin.ModelAdmin):
    search_fields = ["player__first_name","player__last_name","player__email","player__player_uuid"]

admin.site.register(Game)
admin.site.register(Mission)
admin.site.register(Person, PersonAdmin)
admin.site.register(PlayerStatus, PlayerStatusAdmin)
admin.site.register(BadgeType)
admin.site.register(BadgeInstance)
admin.site.register(Tag)
admin.site.register(Blaster)
admin.site.register(Clan)
admin.site.register(ClanInvitation)
admin.site.register(ClanJoinRequest)
admin.site.register(ClanHistoryItem)
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
admin.site.register(OZEntry)
admin.site.register(NameChangeRequest)
admin.site.register(CustomRedirect)
admin.site.register(Scoreboard)
