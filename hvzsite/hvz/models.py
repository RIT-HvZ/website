from importlib.metadata import requires
from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager, BaseUserManager
from django.db.models.functions import Concat
from django.db.models import CharField
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.templatetags.static import static

import datetime
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
    name = models.CharField(max_length=100, primary_key=True)
    picture = models.ImageField(upload_to=get_clan_upload_path, null=True)
    def __str__(self) -> str:
        return self.name
    
    def save(self, *args, **kwargs):
        if self.picture:
            self.picture = resize_image(self.picture, 400, 400)
        super().save()
                
def get_person_upload_path(instance, filename):
    return os.path.join("profile_pictures",str(instance.player_uuid), filename)


class PersonFullNameManager(models.Manager):
    def get_queryset(self):
        return super(PersonFullNameManager, self).get_queryset().annotate(full_name=Concat('first_name', 'last_name', output_field=CharField()))


class Game(models.Model):
    game_name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self) -> str:
        return f"{self.game_name}: {datetime.datetime.strftime(self.start_date, '%Y/%m/%d')}-{datetime.datetime.strftime(self.end_date, '%Y/%m/%d')}"


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
    team = models.CharField(max_length=1,choices=[('h','Human'),('z','Zombie'),('s',"Staff")])
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)

    def __str__(self) -> str:
        return f"{self.mission_name} - { {'h':'Human','z':'Zombie','s':'Staff'}[self.team]} - {str(self.game)}"

    @property
    def story_viewable(self):
        return self.story_form_go_live_time < timezone.localtime()
    
    @property
    def non_story_viewable(self):
        return self.go_live_time < timezone.localtime()


class Person(AbstractUser):
    player_uuid = models.UUIDField(verbose_name="Player UUID", default=uuid.uuid4, unique=True)
    clan = models.ForeignKey(Clan, on_delete=models.SET_NULL, blank=True, null=True, related_name="clan_members")
    picture = models.ImageField(upload_to=get_person_upload_path, null=True, blank=True)
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
    
    def save(self, *args, **kwargs):
        if self.picture and (self.picture != self.__original_picture):
            self.picture = resize_image(self.picture, 400, 400, 'PNG')
        super().save()


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
    printed = models.BooleanField(verbose_name="Has Player's ID card been printed?", default=False)
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

    @property
    def num_tags(self):
        return Tag.objects.filter(game=self.game, tagger=self.player).count()


class Rules(SingletonModel):
    rules_text = tinymce_models.HTMLField(verbose_name="Rules Text")
    last_edited_by = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)
    last_edited_datetime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Da Rules. Last edited by {self.last_edited_by} at {self.last_edited_datetime.astimezone(timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M')}"


def gen_default_code(k=10):
    return ''.join(random.choices(string.ascii_letters, k=k))


class AntiVirus(models.Model):
    av_uuid = models.UUIDField(verbose_name="AV UUID (Unique)", editable=False, default=uuid.uuid4, primary_key=True)
    av_code = models.CharField(verbose_name="AV Code", editable=True, default=gen_default_code, max_length=30)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)#, default=get_latest_game)
    used_by = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)
    time_used = models.DateTimeField(null=True, blank=True)
    expiration_time = models.DateTimeField(null=True, blank=True)

    @property
    def get_status(self):
        if self.used_by is not None:
            return "Used"
        if timezone.localtime() > self.expiration_time:
            return "Expired"
        return "Active"


class BadgeType(models.Model):
    badge_name = models.CharField(verbose_name="Badge Name", max_length=30, null=False)
    picture = models.ImageField(upload_to="badge_icons/", null=True)
    badge_type = models.CharField(verbose_name="Badge Type", choices=[('a','Account (persistent)'),('g','Game (resets after each game)')], max_length=1, null=False, default='g')
    def __str__(self) -> str:
        return f"{self.badge_name}"
    
    def save(self, *args, **kwargs):
        if self.picture:
            self.picture = resize_image(self.picture, 400, 400, "PNG")
        super().save()

class BadgeInstance(models.Model):
    badge_type = models.ForeignKey(BadgeType, on_delete=models.CASCADE)
    player = models.ForeignKey(Person, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(verbose_name="Badge Timestamp", auto_now=True)
    game_awarded = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)
    def __str__(self) -> str:
        return f"{self.badge_type.badge_name} earned by {self.player} at {self.timestamp}"


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
    timestamp = models.DateTimeField(verbose_name="Tag Timestamp", auto_now=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    def __str__(self) -> str:
        if self.taggee:
            return f"{self.tagger} tagged {self.taggee} at {self.timestamp}"
        elif self.armor_taggee:
            return f"{self.tagger} tagged {self.armor_taggee} at {self.timestamp}"
        else:
            return f"{self.tagger} tagged nothing at {self.timestamp}"


class Report(models.Model):
    report_text = models.TextField(verbose_name="Report Description")
    reporter_email = models.EmailField(verbose_name="Reporter Email", null=True, blank=True)
    reporter = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="reporters")
    reportees = models.ManyToManyField(Person, related_name="reportees")
    timestamp = models.DateTimeField(auto_now_add=True, editable=True)
    status = models.CharField(max_length=1, null=False, default='n', choices=(('n','New'),('i','Investigating'),('d','Dismissed'),('c','Closed')))
    game = models.ForeignKey(Game, null=False, on_delete=models.CASCADE)
    picture = models.ImageField(upload_to='report_images/', null=True, blank=True)

    __original_picture = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_picture = self.picture

    def save(self, *args, **kwargs):
        if self.picture and (self.picture != self.__original_picture):
            self.picture = resize_image(self.picture, 1000, 1000, "JPEG")
        super().save()

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
