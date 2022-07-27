from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager, BaseUserManager
from django.db.models.functions import Concat
from django.db.models import CharField

import datetime
import uuid
import os

def get_team_upload_path(instance, filename):
        return os.path.join("static","team_pictures",str(instance.name), filename)

class Team(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    picture = models.ImageField(upload_to=get_team_upload_path, null=True)
    def __str__(self) -> str:
        return self.name

def get_person_upload_path(instance, filename):
    return os.path.join("static","profile_pictures",str(instance.zombie_uuid), filename)

class PersonFullNameManager(models.Manager):
    def get_queryset(self):
        return super(PersonFullNameManager, self).get_queryset().annotate(full_name=Concat('first_name', 'last_name', output_field=CharField()))

class Game(models.Model):
    game_name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self) -> str:
        return f"{self.game_name}: {datetime.datetime.strftime(self.start_date, '%Y/%m/%d')}-{datetime.datetime.strftime(self.end_date, '%Y/%m/%d')}"

def get_latest_game():
    return Game.objects.latest("start_date")

class Mission(models.Model):
    team = models.CharField(max_length=1,choices=[('h','Human'),('z','Zombie'),('s',"Staff")])
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)
    go_live_time = models.DateTimeField(verbose_name="Date/Time that players can read the mission")

class Person(AbstractUser):
    player_uuid = models.UUIDField(verbose_name="Player UUID", default=uuid.uuid4, unique=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name="team_members")
    picture = models.ImageField(upload_to=get_person_upload_path, null=False, default="/static/images/noprofile.png")
    objects = UserManager()
    full_name_objects = PersonFullNameManager()
    discord_id = models.CharField(max_length=100, null=True)
    games_played = models.ManyToManyField(Game)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class PlayerStatus(models.Model):
    player = models.ForeignKey(Person, on_delete=models.CASCADE)
    tag1_uuid = models.UUIDField(verbose_name="Tag #1 ID",   editable=True, default=uuid.uuid4)
    tag2_uuid = models.UUIDField(verbose_name="Tag #2 ID",   editable=True, default=uuid.uuid4)
    zombie_uuid = models.UUIDField(verbose_name="Zombie ID", editable=True, default=uuid.uuid4)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    status = models.CharField(verbose_name="Role", choices=[('h','Human'),('v','Human (used AV)'),('z','Zombie'),('m','Mod'),('a','Admin'),("o","Zombie (OZ)"),("n","NonPlayer")], max_length=1, default='h', null=False)

class BadgeType(models.Model):
    badge_name = models.CharField(verbose_name="Badge Name", max_length=30, null=False)
    picture = models.ImageField(upload_to="static/badge_icons/", null=True)
    badge_type = models.CharField(verbose_name="Badge Type", choices=[('a','Account (persistent)'),('g','Game (resets after each game)')], max_length=1, null=False, default='g')
    def __str__(self) -> str:
        return f"{self.badge_name}"

class BadgeInstance(models.Model):
    badge_type = models.ForeignKey(BadgeType, on_delete=models.CASCADE)
    player = models.ForeignKey(Person, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(verbose_name="Badge Timestamp", auto_now=True)
    game_awarded = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)
    def __str__(self) -> str:
        return f"{self.badge_type.badge_name} earned by {self.player} at {self.timestamp}"

class Tag(models.Model):
    tagger = models.ForeignKey(Person, null=False, on_delete=models.CASCADE, related_name="taggers")
    taggee = models.ForeignKey(Person, null=False, on_delete=models.CASCADE, related_name="taggees")
    timestamp = models.DateTimeField(verbose_name="Tag Timestamp", auto_now=True)
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)
    def __str__(self) -> str:
        return f"{self.tagger} tagged {self.taggee} at {self.timestamp}"

def get_blaster_upload_path(instance, filename):
        return os.path.join("static","blaster_pictures",str(instance.owner.zombie_uuid), filename)

class Blaster(models.Model):
    name = models.CharField(max_length=100, default="No name given")
    owner = models.ForeignKey(Person, on_delete=models.CASCADE, null=False, related_name="owned_blasters")
    game_approved_in = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)
    approved_by = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, related_name="approved_blasters", limit_choices_to={'is_staff': True})
    picture = models.ImageField(upload_to=get_blaster_upload_path, null=True)

    def __str__(self) -> str:
        return f"Blaster \"{self.name}\" owned by {self.owner}, approved by {self.approved_by}"

        
