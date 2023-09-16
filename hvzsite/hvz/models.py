from importlib.metadata import requires
from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager, BaseUserManager
from django.db.models.functions import Concat
from django.db.models import CharField, Q
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.templatetags.static import static
from django.core.validators import RegexValidator
from django.db.models.functions import Upper

alphanumeric = RegexValidator(r'^[0-9a-zA-Z ]*$', 'Only alphanumeric characters are allowed.')
hex_rgb = RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Only hex color codes e.g. #52fa3d are allowed.')

import datetime
import html
import uuid
import os
import random
import string
from django.utils import timezone
from pytz import timezone as pytz_timezone
from tinymce import models as tinymce_models
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


def generate_id(length=10):
    import secrets
    # Don't use i, o or l as they can be confused for other symbols
    alphabet = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ123456789'
    return ''.join(secrets.choice(alphabet) for i in range(length))

def generate_tag_id(length=10):
    while True:
        new_id = generate_id(length)
        game = get_active_game()
        existing_ids = PlayerStatus.objects.filter(Q(game=game) & (Q(tag1_uuid=new_id) | Q(tag2_uuid=new_id) | Q(zombie_uuid=new_id)))
        if existing_ids.count() > 0:
            continue
        return new_id

def generate_report_id(length=10):
    while True:
        new_id = generate_id(length)
        existing_reports = Report.objects.filter(report_uuid=new_id)
        if existing_reports.count() > 0:
            continue
        return new_id

def get_relative_time(delta):
    if delta.days > 30:
        return f'{delta.days//30} months ago'
    if delta.days > 7:
        return f'{delta.days//7} weeks ago'
    if delta.days > 0:
        return f'{delta.days} days ago'
    if delta.seconds > 3600:
        return f'{delta.seconds // 3600} hours ago'
    if delta.seconds > 60:
        return f'{delta.seconds // 60} mins ago'
    return 'just a moment ago!'

def resize_image(photo, width, height, format="JPEG"):
    im = Image.open(photo)
    output = BytesIO()
    im = im.convert('RGB')
    #Resize/modify the image
    im.thumbnail( (width,height) , Image.ANTIALIAS )
    #after modifications, save it to the output
    im.save(output, format=format, quality=95)
    output.seek(0)
    #change the imagefield value to be the newley modifed image value
    return InMemoryUploadedFile(output,'ImageField', "%s.jpg" % photo.name.split('.')[0], 'image/jpeg', sys.getsizeof(output), None)


def get_clan_upload_path(instance, filename):
    return os.path.join("clan_pictures",str(instance.name), filename)

# Only needed for database migration nonsense, not actually used
get_team_upload_path = get_clan_upload_path

class Clan(models.Model):
    name = models.CharField(max_length=100, verbose_name="Clan Name", unique=True, validators=[alphanumeric])
    clan_uuid = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4, editable=False)
    picture = models.ImageField(upload_to=get_clan_upload_path, null=True)
    leader = models.ForeignKey('Person', on_delete=models.SET_NULL, null=True, related_name="clan_leader")
    disband_timestamp = models.DateTimeField(null=True, blank=True)
    color = models.CharField(max_length=7, verbose_name="Clan Color", validators=[hex_rgb], default="#222222")

    class Meta:
        constraints = [
            models.UniqueConstraint(Upper('name'), name='unique_upper_name_clan')
        ]
        
    __original_picture = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_picture = self.picture

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if self.picture and (self.picture != self.__original_picture):
            self.picture = resize_image(self.picture, 400, 400, 'PNG')
        super().save()

    @property
    def get_text_color(self):
        r = int(self.color[1:3], 16)
        g = int(self.color[3:5], 16)
        b = int(self.color[5:7], 16)
        total_brightness = r+g+b
        if total_brightness > 200:
            return "#222222"
        else:
            return "#dddddd"
        
    @property
    def use_dark_text_color(self):
        r = int(self.color[1:3], 16)
        g = int(self.color[3:5], 16)
        b = int(self.color[5:7], 16)
        total_brightness = r+g+b
        if total_brightness > 200:
            return "true"
        else:
            return "false"
        
    @property
    def get_member_count(self):
        return Person.objects.filter(clan=self).count()

def get_person_upload_path(instance, filename):
    return os.path.join("profile_pictures",str(instance.player_uuid), filename)


class PersonFullNameManager(models.Manager):
    def get_queryset(self):
        return super(PersonFullNameManager, self).get_queryset().annotate(full_name=Concat('first_name', 'last_name', output_field=CharField()))


class Game(models.Model):
    game_name = models.CharField(max_length=50)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.game_name}: {datetime.datetime.strftime(self.start_date, '%Y/%m/%d')}-{datetime.datetime.strftime(self.end_date, '%Y/%m/%d')}"

    @property
    def is_after_start(self):
        return timezone.now() > self.start_date

    @property
    def is_after_end(self):
        return timezone.now() > self.end_date

    @property
    def start_date_javascript(self):
        return self.start_date.strftime("%b %d, %Y %H:%M:%S %Z")

    @property
    def end_date_javascript(self):
        return self.end_date.strftime("%b %d, %Y %H:%M:%S %Z")


class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class CurrentGame(SingletonModel):
    current_game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)


def get_active_game():
    game = CurrentGame.load()
    if game.current_game is None:
        if Game.objects.all().count() > 0:
            game.current_game = Game.objects.latest("start_date")
            game.save()
    return game.current_game

def reset_active_game():
    game = CurrentGame.load()
    game.current_game = None
    game.save()

class Mission(models.Model):
    mission_name = models.CharField(max_length=100)
    story_form = tinymce_models.HTMLField(verbose_name="Story Form")
    story_form_go_live_time = models.DateTimeField(verbose_name="Date/Time that players can read the Story form of the mission")
    mission_text = tinymce_models.HTMLField(verbose_name="Non-Story Form")
    go_live_time = models.DateTimeField(verbose_name="Date/Time that players can read the Non-Story form of the mission")
    team = models.CharField(max_length=1,choices=[('h','Human'),('z','Zombie'),('s',"Staff"),('a',"All")])
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)

    def __str__(self) -> str:
        return f"{self.mission_name} - { {'h':'Human','z':'Zombie','s':'Staff','a':'All'}[self.team]} - {str(self.game)}"

    @property
    def story_viewable(self):
        return self.story_form_go_live_time < timezone.localtime()

    @property
    def non_story_viewable(self):
        return self.go_live_time < timezone.localtime()

class CaseInsensitiveUserManager(UserManager):
    def get_by_natural_key(self, username):
        case_insensitive_username_field = '{}__iexact'.format(self.model.USERNAME_FIELD)
        return self.get(**{case_insensitive_username_field: username})
    
class Person(AbstractUser):
    player_uuid = models.UUIDField(verbose_name="Player UUID", default=uuid.uuid4, unique=True)
    clan = models.ForeignKey(Clan, on_delete=models.SET_NULL, blank=True, null=True, related_name="clan_members")
    picture = models.ImageField(upload_to=get_person_upload_path, null=True, blank=True)
    objects = CaseInsensitiveUserManager()
    full_name_objects = PersonFullNameManager()
    discord_id = models.CharField(max_length=100, blank=True, null=True)
    games_played = models.ManyToManyField(Game, blank=True)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    is_banned = models.BooleanField(verbose_name="Player is banned.", default=False)
    ban_timestamp = models.DateTimeField(null=True, blank=True, auto_now_add=False)
    #USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']

    __original_picture = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_picture = self.picture

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def current_status(self):
        return PlayerStatus.objects.get_or_create(player=self, game=get_active_game())[0]

    @property
    def active_this_game(self):
        return not self.current_status.is_nonplayer()

    @property
    def admin_this_game(self):
        return self.current_status.is_admin()

    @property
    def mod_this_game(self):
        return self.current_status.is_mod()

    @property
    def picture_url(self):
        if self.picture:
            return self.picture.url
        else:
            return static('/images/noprofile.png')

    @property
    def is_a_clan_leader(self):
        return Clan.objects.filter(leader=self).count() > 0

    @property
    def has_ever_played(self):
        return PlayerStatus.objects.filter(player=self, status__in=['h','v','e','z','o','m','a']).count() > 0

    @property
    def id_card_values(self):
        s = self.current_status
        return f"{s.tag1_uuid}|{s.tag2_uuid}|{s.zombie_uuid}"
    
    def save(self, *args, **kwargs):
        self.first_name = html.escape(self.first_name)
        self.last_name = html.escape(self.last_name)
        if self.picture and (self.picture != self.__original_picture):
            self.picture = resize_image(self.picture, 400, 400, 'PNG')
        super().save()

class OZEntry(models.Model):
    player = models.ForeignKey(Person, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'Player "{self.player}" for game "{self.game}"'

class PlayerStatus(models.Model):
    player = models.ForeignKey(Person, on_delete=models.CASCADE)
    tag1_uuid =   models.CharField(verbose_name="Tag #1 ID", editable=True, default=generate_tag_id, max_length=36)
    tag2_uuid =   models.CharField(verbose_name="Tag #2 ID", editable=True, default=generate_tag_id, max_length=36)
    zombie_uuid = models.CharField(verbose_name="Zombie ID", editable=True, default=generate_tag_id, max_length=36)
    printed = models.BooleanField(verbose_name="Has Player's ID card been printed?", default=False)
    activation_timestamp = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    status = models.CharField(verbose_name="Role", choices=[('h','Human'),('v','Human (used AV)'),('e', 'Human (Extracted)'),('z','Zombie'),('x','Zombie (used AV)'),('m','Mod'),('a','Admin'),("o","Zombie (OZ)"),("n","NonPlayer")], max_length=1, default='n', null=False)
    av_banned = models.BooleanField(verbose_name="Is player banned from AV'ing this game", default=False)
    waiver_signed = models.BooleanField(verbose_name="Has Player returned a signed waiver for this game?", editable=True, default=False)
    
    class Meta:
        unique_together = (('tag1_uuid', 'game'),
                           ('tag2_uuid', 'game'),
                           ('zombie_uuid', 'game'))

    def __str__(self) -> str:
        return f"Status of {self.player} during game \"{self.game}\" ({self.get_status_display()})"

    def is_zombie(self):
        return self.status in ['z','o','x']

    def is_human(self):
        return self.status in ['h','v','e']

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
        return (self.status == "z") and (self.av_banned == False)

    @property
    def num_tags(self):
        return Tag.objects.filter(game=self.game, tagger=self.player).count()

    @property
    def listing_priority(self):
        if self.is_admin():
            return 0
        if self.is_mod():
            return 5
        if self.is_human():
            return 10
        if self.is_zombie():
            return 20
        return 100
    
    @property
    def num_failed_av_attempts(self):
        return FailedAVAttempt.objects.filter(player=self.player, game=self.game).count()

    @property
    def logical_timestamp(self):
        if self.activation_timestamp is None:
            return '---'
        return self.activation_timestamp.strftime('%Y-%m-%d %H:%M')


class Rules(SingletonModel):
    rules_text = tinymce_models.HTMLField(verbose_name="Rules Text")
    last_edited_by = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)
    last_edited_datetime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Da Rules. Last edited by {self.last_edited_by} at {self.last_edited_datetime.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M')}"

class About(SingletonModel):
    about_text = tinymce_models.HTMLField(verbose_name="About Us")
    last_edited_by = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)
    last_edited_datetime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"About Us. Last edited by {self.last_edited_by} at {self.last_edited_datetime.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M')}"

def gen_default_code(k=10):
    return ''.join(random.choices(string.ascii_letters, k=k))

class AntiVirus(models.Model):
    av_uuid = models.UUIDField(verbose_name="AV UUID (Unique)", editable=False, default=uuid.uuid4, primary_key=True)
    av_code = models.CharField(verbose_name="AV Code", editable=True, default=gen_default_code, max_length=30)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)#, default=get_latest_game)
    used_by = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)
    time_used = models.DateTimeField(null=True, blank=True)
    expiration_time = models.DateTimeField()

    @property
    def get_status(self):
        if self.used_by is not None:
            return "Used"
        if timezone.localtime() > self.expiration_time:
            return "Expired"
        return "Active"

    @property
    def datatype(self):
        return "AntiVirus"

    @property
    def display_timestamp(self):
        day = self.time_used.astimezone(timezone.get_current_timezone()).strftime("%A")
        hour = str(int(self.time_used.astimezone(timezone.get_current_timezone()).strftime("%I")))
        remainder = self.time_used.astimezone(timezone.get_current_timezone()).strftime("%M %p").lower()
        return f"{day} at {hour}:{remainder}"

    @property
    def relative_time_str(self):
        delta = (timezone.localtime() - self.time_used)
        return get_relative_time(delta)
    
class FailedAVAttempt(models.Model):
    player = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="failed_av_attempts")
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    code_used = models.CharField(max_length=1000)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp}: {self.player} attempted AV code {self.code_used}"
    
    @property 
    def display_timestamp(self):
        return f"{self.timestamp.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M:%S')}"
    
    @property
    def web_str(self):
        return f"<span class='avtimestamp'>{self.display_timestamp}:</span> {html.escape(self.code_used)}"
    

class BadgeType(models.Model):
    badge_name = models.CharField(verbose_name="Badge Name", max_length=30, null=False)
    picture = models.ImageField(upload_to="badge_icons/", null=True)
    badge_type = models.CharField(verbose_name="Badge Type", choices=[('a','Account (persistent)'),('g','Game (resets after each game)')], max_length=1, null=False, default='g')
    badge_description = models.CharField(verbose_name="Badge Description", max_length=256, null=False)
    mod_grantable = models.BooleanField(verbose_name="Can Moderators (not just admins) grant this badge", default=False)
    active = models.BooleanField(verbose_name="Is this badge still able to be earned / granted?", default=True)
    def __str__(self) -> str:
        return f"{self.badge_name}"

    def save(self, *args, **kwargs):
        if self.picture:
            self.picture = resize_image(self.picture, 400, 400, "PNG")
        super().save()

class BadgeInstance(models.Model):
    badge_type = models.ForeignKey(BadgeType, on_delete=models.CASCADE)
    player = models.ForeignKey(Person, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(verbose_name="Badge Timestamp", auto_now_add=True)
    game_awarded = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)
    def __str__(self) -> str:
        return f"{self.badge_type.badge_name} earned by {self.player} at {self.timestamp.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M:%S')}"


def get_blaster_upload_path(instance, filename):
        return os.path.join("blaster_pictures",str(instance.owner.player_uuid), filename)


class Blaster(models.Model):
    name = models.CharField(max_length=100, default="No name given")
    owner = models.ForeignKey(Person, on_delete=models.CASCADE, null=False, related_name="owned_blasters")
    game_approved_in = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)
    approved_by = models.ManyToManyField(Person, related_name="approved_blasters", limit_choices_to={'is_staff': True})
    picture = models.ImageField(upload_to=get_blaster_upload_path, null=True)
    avg_chrono = models.FloatField(verbose_name="Average Chronograph velocity", default=0)

    def __str__(self) -> str:
        return f"Blaster \"{self.name}\" owned by {self.owner}. Avg. FPS: {self.avg_chrono if self.avg_chrono != 0 else 'N/A'}. Approved by {', '.join([str(p) for p in self.approved_by.all()])}"

    def save(self, *args, **kwargs):
        if self.picture:
            self.picture = resize_image(self.picture, 400, 400)
        super().save()

class PostGameSurvey(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)#, default=get_latest_game)
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    go_live_time = models.DateTimeField(verbose_name="Date/Time that players can take the survey")
    lock_time = models.DateTimeField(verbose_name="Date/Time that players can no longer the survey")
    survey_text = tinymce_models.HTMLField()

    @property
    def is_open(self):
        return self.go_live_time < timezone.localtime() and self.lock_time > timezone.localtime()

    @property
    def is_viewable(self):
        print(f"---{self.mission}---")
        print(self.go_live_time)
        print(timezone.localtime())
        return self.go_live_time < timezone.localtime()

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
        if timezone.localtime() > self.expiration_time:
            return "Expired"
        return "Active"

    def __str__(self) -> str:
        return f"Body Armor {self.armor_code}. Expires {self.expiration_time.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M')}. From game {self.game}"


class Tag(models.Model):
    tagger = models.ForeignKey(Person, null=False, on_delete=models.CASCADE, related_name="taggers")
    taggee = models.ForeignKey(Person, null=True, blank=True, on_delete=models.CASCADE, related_name="taggees")
    armor_taggee = models.ForeignKey(BodyArmor, null=True, blank=True, on_delete=models.CASCADE, related_name="armor_taggees")
    timestamp = models.DateTimeField(verbose_name="Tag Timestamp", auto_now_add=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    def __str__(self) -> str:
        if self.taggee:
            return f"{self.tagger} tagged {self.taggee} at {self.timestamp}"
        elif self.armor_taggee:
            return f"{self.tagger} tagged {self.armor_taggee} at {self.timestamp}"
        else:
            return f"{self.tagger} tagged nothing at {self.timestamp}"

    @property
    def datatype(self):
        return "Tag"

    @property
    def display_timestamp(self):
        day = self.timestamp.astimezone(timezone.get_current_timezone()).strftime("%A")
        hour = str(int(self.timestamp.astimezone(timezone.get_current_timezone()).strftime("%I")))
        remainder = self.timestamp.astimezone(timezone.get_current_timezone()).strftime("%M %p").lower()
        return f"{day} at {hour}:{remainder}"

    @property
    def relative_time_str(self):
        delta = (timezone.localtime() - self.timestamp)
        return get_relative_time(delta)

    def handle_streak_badges(self):
        '''
        Handles giving streak badges to the tagging player if appropriate
        '''
        prev_tags = Tag.objects.filter(tagger=self.tagger, game=self.game).order_by('-timestamp')
        if prev_tags[0] == self:
            prev_tags = prev_tags[1:]

        # Loop through prev tags, check for timestamps within 1 hour to continue streak
        curr_timestamp = self.timestamp
        streak = 1
        for tag in prev_tags:
            if (curr_timestamp - tag.timestamp).seconds / 3600 < 1:
                # Less than 1 hour, streak continues
                curr_timestamp = tag.timestamp
                streak += 1
            else:
                break

        if streak > 1:
            if streak == 2:
                badge_type = BadgeType.objects.get(badge_name='Tag Streak: Twin-Tag')
            elif streak == 3:
                badge_type = BadgeType.objects.get(badge_name='Tag Streak: Triple-Tag')
            elif streak == 4:
                badge_type = BadgeType.objects.get(badge_name='Tag Streak: Quad-Tag')
            elif streak == 5:
                badge_type = BadgeType.objects.get(badge_name='Tag Streak: Pentag')
            elif streak == 6:
                badge_type = BadgeType.objects.get(badge_name='Tag Streak: Overkill')
            elif streak == 7:
                badge_type = BadgeType.objects.get(badge_name='Tag Streak: Lucky 7')
            elif streak == 8:
                badge_type = BadgeType.objects.get(badge_name='Tag Streak: Tagalicious')
            elif streak == 9:
                badge_type = BadgeType.objects.get(badge_name='Tag Streak: Unstoppable')
            else:
                badge_type = BadgeType.objects.get(badge_name='Tag Streak: Apocalypse')
            # Give the player the badge
            badge = BadgeInstance.objects.create(badge_type=badge_type, player=self.tagger, game_awarded=self.game)
            badge.save()


class Report(models.Model):
    report_text = models.TextField(verbose_name="Report Description")
    reporter_email = models.EmailField(verbose_name="Reporter Email", null=True, blank=True)
    reporter = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="reporters")
    reportees = models.ManyToManyField(Person, related_name="reportees")
    timestamp = models.DateTimeField(auto_now_add=True, editable=True)
    status = models.CharField(max_length=1, null=False, default='n', choices=(('n','New'),('i','Investigating'),('d','Dismissed'),('c','Closed')))
    game = models.ForeignKey(Game, null=False, on_delete=models.CASCADE)
    picture = models.ImageField(upload_to='report_images/', null=True, blank=True)
    report_uuid = models.CharField(max_length=10, unique=True, editable=False, null=False, default=generate_report_id)

    __original_picture = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_picture = self.picture

    def save(self, *args, **kwargs):
        if self.picture and (self.picture != self.__original_picture):
            self.picture = resize_image(self.picture, 1000, 1000, "JPEG")
        super().save()

    def __str__(self):
        return f"Report ID {self.report_uuid} filed by {self.get_reporter} at {self.timestamp.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M')}"
    @property
    def get_reporter(self):
        if self.reporter:
            return self.reporter
        elif self.reporter_email:
            return self.reporter_email
        else:
            return "Anonymous"

    @property
    def has_picture(self):
        return self.picture is not None

    @property
    def status_text(self):
        options = {'n':'New', 'i':'Investigating','d':'Dismissed','c':'Closed', '':'Unknown'}
        return options[self.status]

    @property
    def is_mod_report(self):
        return self.reporter is not None and self.reporter.mod_this_game

    @property
    def last_updated(self):
        updates = ReportUpdate.objects.filter(report=self).order_by('-timestamp')
        if len(updates) == 0:
            return None
        return updates[0].timestamp

    @property
    def get_reportee(self):
        return self.reportee if self.reportee else "N/A"

    def __str__(self):
        return f"Report #{self.id}, made by {self.get_reporter} on {self.timestamp.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M')}. Status: {self.status_text}"


@receiver(post_save, sender=Report)
def update_file_path(instance, created, **kwargs):
    if created and instance.picture:
        initial_path = instance.picture.path
        new_path = settings.MEDIA_ROOT + f'/report_images/{instance.id}.jpeg'
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        os.rename(initial_path, new_path)
        instance.picture = new_path
        instance.save()


class ReportUpdate(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    note_creator = models.ForeignKey(Person, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField()

    @property
    def get_timestamp(self):
        return self.timestamp.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M')

    def __str__(self):
        return f"Update on Report #{self.report.id} by {self.note_creator} at {self.timestamp.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M')}"


class DiscordLinkCode(models.Model):
    account = models.ForeignKey(Person, on_delete=models.CASCADE)
    code = models.CharField(verbose_name="Discord Link Code", editable=False, default=gen_default_code, max_length=30)
    expiration_time = models.DateTimeField()


class ClanInvitation(models.Model):
    inviter = models.ForeignKey(Person, related_name='inviters', on_delete=models.CASCADE)
    invitee = models.ForeignKey(Person, related_name='invitees', on_delete=models.CASCADE)
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE)
    status = models.CharField(max_length=1, choices=(('n','new'),('a','accepted'),('r','rejected'),('e','expired')), default='n')
    invitation_timestamp = models.DateTimeField(auto_now_add=True)
    response_timestamp = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Invitation for {self.invitee} to join clan {self.clan.name}"
    
class ClanJoinRequest(models.Model):
    requestor = models.ForeignKey(Person, related_name='requestors', on_delete=models.CASCADE)
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE)
    status = models.CharField(max_length=1, choices=(('n','new'),('a','accepted'),('r','rejected'),('e','expired')), default='n')
    request_timestamp = models.DateTimeField(auto_now_add=True)
    response_timestamp = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Request for {self.requestor} to join clan {self.clan.name}"
    
class ClanHistoryItem(models.Model):
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE)
    actor = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name='actors')
    other = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name='others')
    additional_info = models.CharField(max_length=300, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, editable=False)
    history_item_type = models.CharField(max_length=1, choices=(
        ('c','creation'),
        ('d','disband'),
        ('n','name_change'),
        ('p','photo_change'),
        ('i','player_added_by_invite'),
        ('r','player_added_by_request'),
        ('x','promote'),
        ('k','kick'),
        ('l','leave'),
        ('a','leader_banned'),
        ('b','promoted_by_system'),
        ('e','disbanded_by_system')
    ))

    @property
    def timestamp_display(self):
        return self.timestamp.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M:%S')

    def __str__(self) -> str:
        try:
            if self.history_item_type == "c":
                return f"{self.actor} ({self.actor.player_uuid}) created clan {self.clan} at {self.timestamp_display}"
            elif self.history_item_type == "d":
                return f"{self.actor} ({self.actor.player_uuid}) disbanded clan {self.clan} at {self.timestamp_display}"
            elif self.history_item_type == "n":
                return f"{self.actor} ({self.actor.player_uuid}) changed clan name {self.additional_info} at {self.timestamp_display}" # additional_info should be "from X to Y" format
            elif self.history_item_type == "p":
                return f"{self.actor} ({self.actor.player_uuid}) updated clan photo {self.additional_info} at {self.timestamp_display}" # additional_info should be "from X.jpg to Y.jpg" format
            elif self.history_item_type == "i":
                return f"{self.actor} ({self.actor.player_uuid}) accepted invitation to clan {self.clan} at {self.timestamp_display}"
            elif self.history_item_type == "r":
                return f"{self.actor} ({self.actor.player_uuid}) accepted {self.other} ({self.other.player_uuid})'s request to join clan {self.clan} at {self.timestamp_display}"
            elif self.history_item_type == "x":
                return f"{self.actor} ({self.actor.player_uuid}) promoted {self.other} ({self.other.player_uuid}) to leader of clan {self.clan} at {self.timestamp_display}"
            elif self.history_item_type == "k":
                return f"{self.actor} ({self.actor.player_uuid}) kicked {self.other} ({self.other.player_uuid}) from clan {self.clan} at {self.timestamp_display}"
            elif self.history_item_type == "l":
                return f"{self.actor} ({self.actor.player_uuid}) left clan {self.clan} at {self.timestamp_display}"
            elif self.history_item_type == "a":
                return f"Leader {self.actor} ({self.actor.player_uuid}) was banned at {self.timestamp_display}"
            elif self.history_item_type == "b":
                return f"{self.actor} ({self.actor.player_uuid}) was promoted to leader by the system at {self.timestamp_display}"
            elif self.history_item_type == "e":
                return f"Clan was disbanded by the system at {self.timestamp_display}"
            return "I don't know."
        except:
            return "I don't know."
        
    @property
    def web_str(self):
        try:
            if self.history_item_type == "c":
                return f"<a class='clan_link' href='/player/{self.actor.player_uuid}/'>{self.actor}</a> created clan at {self.timestamp_display}"
            elif self.history_item_type == "d":
                return f"<a class='clan_link' href='/player/{self.actor.player_uuid}/'>{self.actor}</a> disbanded clan at {self.timestamp_display}"
            elif self.history_item_type == "n":
                return f"<a class='clan_link' href='/player/{self.actor.player_uuid}/'>{self.actor}</a> changed clan name {self.additional_info} at {self.timestamp_display}" # additional_info should be "from X to Y" format
            elif self.history_item_type == "p":
                return f"<a class='clan_link' href='/player/{self.actor.player_uuid}/'>{self.actor}</a> updated clan photo {self.additional_info} at {self.timestamp_display}" # additional_info should be "from X.jpg to Y.jpg" format
            elif self.history_item_type == "i":
                return f"<a class='clan_link' href='/player/{self.actor.player_uuid}/'>{self.actor}</a> accepted invitation at {self.timestamp_display}"
            elif self.history_item_type == "r":
                return f"<a class='clan_link' href='/player/{self.actor.player_uuid}/'>{self.actor}</a> accepted <a class='clan_link' href='/player/{self.other.player_uuid}/'>{self.other}</a>'s request to join at {self.timestamp_display}"
            elif self.history_item_type == "x":
                return f"<a class='clan_link' href='/player/{self.actor.player_uuid}/'>{self.actor}</a> promoted <a class='clan_link' href='/player/{self.other.player_uuid}/'>{self.other}</a> to leader of clan at {self.timestamp_display}"
            elif self.history_item_type == "k":
                return f"<a class='clan_link' href='/player/{self.actor.player_uuid}/'>{self.actor}</a> kicked <a class='clan_link' href='/player/{self.other.player_uuid}/'>{self.other}</a> at {self.timestamp_display}"
            elif self.history_item_type == "l":
                return f"<a class='clan_link' href='/player/{self.actor.player_uuid}/'>{self.actor}</a> left at {self.timestamp_display}"
            elif self.history_item_type == "a":
                return f"Clan Leader <a class='clan_link' href='/player/{self.actor.player_uuid}/'>{self.actor}</a> was banned at {self.timestamp_display}"
            elif self.history_item_type == "b":
                return f"<a class='clan_link' href='/player/{self.actor.player_uuid}/'>{self.actor}</a> was promoted to leader by the system at {self.timestamp_display}"
            elif self.history_item_type == "e":
                return f"Clan was disbanded by the system at {self.timestamp_display}"
            return "I don't know."
        except:
            return "I don't know."

class Announcement(models.Model):
    post_time = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    long_form = tinymce_models.HTMLField(verbose_name="Full Announcement post")
    short_form = models.TextField(verbose_name="Announcement header short-form",max_length=300)

    def __str__(self) -> str:
        return f"Announcement on {self.post_time}: {self.short_form}"

    @property
    def timestamp_display(self):
        return self.post_time.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M:%S')

    @property
    def relative_time_str(self):
        delta = (timezone.localtime() - self.post_time)
        return get_relative_time(delta)
