from importlib.metadata import requires
from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager, BaseUserManager
from django.db.models.functions import Concat
from django.db.models import CharField
from django_resized import ResizedImageField

import datetime
import uuid
import os
import random
import string
from django.utils import timezone
from pytz import timezone as pytz_timezone
from tinymce import models as tinymce_models

def get_team_upload_path(instance, filename):
        return os.path.join("static","team_pictures",str(instance.name), filename)


class Team(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    picture = ResizedImageField(size=[400, None], keep_meta=False, force_format="jpeg", upload_to=get_team_upload_path, null=True)
    def __str__(self) -> str:
        return self.name

def get_person_upload_path(instance, filename):
    return os.path.join("static","profile_pictures",str(instance.player_uuid), filename)

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
    if Game.objects.count() > 0:
        return Game.objects.latest("start_date")
    dummy_game = Game.objects.create(game_name="Dummy game", start_date=datetime.date.today(), end_date=datetime.date.today())
    dummy_game.save()
    return dummy_game
    
class Mission(models.Model):
    mission_name = models.CharField(max_length=100)
    story_form = tinymce_models.HTMLField(verbose_name="Story Form")
    story_form_go_live_time = models.DateTimeField(verbose_name="Date/Time that players can read the Story form of the mission")
    mission_text = tinymce_models.HTMLField(verbose_name="Non-Story Form")
    go_live_time = models.DateTimeField(verbose_name="Date/Time that players can read the Non-Story form of the mission")
    team = models.CharField(max_length=1,choices=[('h','Human'),('z','Zombie'),('s',"Staff")])
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)

    def __str__(self) -> str:
        return f"{self.mission_name} - { {'h':'Human','z':'Zombie','s':'Staff'}[self.team]} - {str(self.game)}"

    @property
    def story_viewable(self):
        return self.story_form_go_live_time < timezone.now()
    
    @property
    def non_story_viewable(self):
        return self.go_live_time < timezone.now()


class Person(AbstractUser):
    player_uuid = models.UUIDField(verbose_name="Player UUID", default=uuid.uuid4, unique=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, blank=True, null=True, related_name="team_members")
    picture = ResizedImageField(size=[400,None], keep_meta=False, force_format="jpeg", upload_to=get_person_upload_path, null=False, default="/static/images/noprofile.png")
    objects = UserManager()
    full_name_objects = PersonFullNameManager()
    discord_id = models.CharField(max_length=100, blank=True, null=True)
    games_played = models.ManyToManyField(Game, blank=True)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    #USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def current_status(self):
        return PlayerStatus.objects.get_or_create(player=self, game=get_latest_game())[0]

    @property
    def num_tags(self):
        return Tag.objects.filter(game=get_latest_game(), tagger=self).count()

    @property
    def active_this_game(self):
        return not self.current_status.is_nonplayer()

    @property
    def admin_this_game(self):
        return self.current_status.is_admin()

def generate_tag_id(length=10):
    import string
    import secrets
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

class PlayerStatus(models.Model):
    player = models.ForeignKey(Person, on_delete=models.CASCADE)
    tag1_uuid =   models.CharField(verbose_name="Tag #1 ID", editable=True, default=generate_tag_id, max_length=36)
    tag2_uuid =   models.CharField(verbose_name="Tag #2 ID", editable=True, default=generate_tag_id, max_length=36)
    zombie_uuid = models.CharField(verbose_name="Zombie ID", editable=True, default=generate_tag_id, max_length=36)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    status = models.CharField(verbose_name="Role", choices=[('h','Human'),('v','Human (used AV)'),('z','Zombie'),('x','Zombie (used AV)'),('m','Mod'),('a','Admin'),("o","Zombie (OZ)"),("n","NonPlayer")], max_length=1, default='n', null=False)

    class Meta:
        unique_together = (('tag1_uuid', 'game'),
                           ('tag2_uuid', 'game'),
                           ('zombie_uuid', 'game'))

    def __str__(self) -> str:
        return f"Status of {self.player} during game \"{self.game}\" ({self.get_status_display()})"

    def is_zombie(self):
        return self.status in ['z','o','x']

    def is_human(self):
        return self.status in ['h','v']

    def is_mod(self):
        return self.status == 'm'

    def is_admin(self):
        return self.status == 'a'

    def is_staff(self):
        return self.status in ['m','a']

    def is_nonplayer(self):
        return self.status == 'n'
    
    @property
    def can_av(self):
        return self.status == "z"

def gen_default_code():
    return ''.join(random.choices(string.ascii_letters, k=10))

class AntiVirus(models.Model):
    av_uuid = models.UUIDField(verbose_name="AV UUID (Unique)", editable=False, default=uuid.uuid4, primary_key=True)
    av_code = models.CharField(verbose_name="AV Code", editable=True, default=gen_default_code, max_length=30)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)#, default=get_latest_game)
    used_by = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)
    time_used = models.DateTimeField(null=True, blank=True)
    expiration_time = models.DateTimeField(null=True, blank=True)

class BadgeType(models.Model):
    badge_name = models.CharField(verbose_name="Badge Name", max_length=30, null=False)
    picture = ResizedImageField(size=[400,None], force_format="PNG", keep_meta=False, upload_to="static/badge_icons/", null=True)
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


def get_blaster_upload_path(instance, filename):
        return os.path.join("static","blaster_pictures",str(instance.owner.player_uuid), filename)

class Blaster(models.Model):
    name = models.CharField(max_length=100, default="No name given")
    owner = models.ForeignKey(Person, on_delete=models.CASCADE, null=False, related_name="owned_blasters")
    game_approved_in = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)
    approved_by = models.ManyToManyField(Person, related_name="approved_blasters", limit_choices_to={'is_staff': True})
    picture = ResizedImageField(size=[400, None], quality=75, keep_meta=False, force_format="jpeg", upload_to=get_blaster_upload_path, null=True)
    avg_chrono = models.FloatField(verbose_name="Average Chronograph velocity", default=0)

    def __str__(self) -> str:
        return f"Blaster \"{self.name}\" owned by {self.owner}. Avg. FPS: {self.avg_chrono if self.avg_chrono != 0 else 'N/A'}. Approved by {', '.join([str(p) for p in self.approved_by.all()])}"

class PostGameSurvey(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)#, default=get_latest_game)
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    go_live_time = models.DateTimeField(verbose_name="Date/Time that players can take the survey")
    lock_time = models.DateTimeField(verbose_name="Date/Time that players can no longer the survey")
    survey_text = tinymce_models.HTMLField()

    @property
    def is_open(self):
        return self.go_live_time < timezone.now() and self.lock_time > timezone.now()
    
    @property
    def is_viewable(self):
        return self.go_live_time < timezone.now()

    def __str__(self) -> str:
        return f"Survey for mission {self.mission}"

class PostGameSurveyOption(models.Model):
    survey = models.ForeignKey(PostGameSurvey, on_delete=models.CASCADE)
    option_name = models.CharField(max_length=50, null=True, blank=True)
    option_text = tinymce_models.HTMLField()

    def __str__(self) -> str:
        return f"Option {self.option_name} for survey {self.survey}"

class PostGameSurveyResponse(models.Model):
    player = models.ForeignKey(Person, on_delete=models.CASCADE)
    survey = models.ForeignKey(PostGameSurvey, on_delete=models.CASCADE)
    response = models.ForeignKey(PostGameSurveyOption, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"Response of {self.player} for survey {self.survey} - {self.response}"

class BodyArmor(models.Model):
    armor_uuid = models.CharField(verbose_name="Armor UUID (Unique)", max_length=36, editable=False, default=uuid.uuid4, primary_key=True)
    armor_code = models.CharField(verbose_name="Armor Code", editable=True, default=gen_default_code, max_length=30)
    expiration_time = models.DateTimeField()
    loaned_to = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)
    loaned_at = models.DateTimeField(null=True, blank=True)
    returned = models.BooleanField(default=False)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)#, default=get_latest_game)

    class Meta:
        unique_together = ('armor_code', 'game',)

    @property
    def used(self):
        return len(Tag.objects.filter(armor_taggee=self)) > 0
    
    @property
    def get_tag(self):
        return Tag.objects.get(armor_taggee=self)
    
    @property
    def get_status(self):
        if self.used:
            return "Tagged"
        if datetime.datetime.now(tz=pytz_timezone('EST')) > self.expiration_time:
            return "Expired"
        return "Active"

    def __str__(self) -> str:
        return f"Body Armor {self.armor_code}. Expires {datetime.datetime.strftime(self.expiration_time, '%Y-%m-%d %H:%M')}. From game {self.game}"

class Tag(models.Model):
    tagger = models.ForeignKey(Person, null=False, on_delete=models.CASCADE, related_name="taggers")
    taggee = models.ForeignKey(Person, null=True, blank=True, on_delete=models.CASCADE, related_name="taggees")
    armor_taggee = models.ForeignKey(BodyArmor, null=True, blank=True, on_delete=models.CASCADE, related_name="armor_taggees")
    timestamp = models.DateTimeField(verbose_name="Tag Timestamp", auto_now=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    def __str__(self) -> str:
        if self.taggee:
            return f"{self.tagger} tagged {self.taggee} at {self.timestamp}"
        elif self.armor_taggee:
            return f"{self.tagger} tagged {self.armor_taggee} at {self.timestamp}"
        else:
            return f"{self.tagger} tagged nothing at {self.timestamp}"