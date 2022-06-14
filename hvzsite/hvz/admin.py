from django.contrib import admin

# Register your models here.

from django.contrib.auth.admin import UserAdmin
from .models import BadgeInstance, BadgeType, Blaster, Person, Tag, Team

admin.site.register(Person)
admin.site.register(BadgeType)
admin.site.register(BadgeInstance)
admin.site.register(Tag)
admin.site.register(Blaster)
admin.site.register(Team)