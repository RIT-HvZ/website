from django.contrib import admin

# Register your models here.

from django.contrib.auth.admin import UserAdmin
from .models import AntiVirus, BadgeInstance, BadgeType, Blaster, Game, Mission, Person, PlayerStatus, Tag, Team

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