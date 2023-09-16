from django import forms
from django.forms import ValidationError
from django.db.models import Count, Q
from .models import Announcement, Person, Blaster, BodyArmor, AntiVirus, Rules, About, PlayerStatus, Clan, get_active_game, Tag, Mission, CurrentGame, PostGameSurvey, PostGameSurveyOption, Report, ReportUpdate
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from datetime import datetime
from pytz import timezone
from django_registration.forms import RegistrationForm
from django.utils.translation import gettext_lazy as _
from django_registration import validators
from captcha.fields import CaptchaField

class HVZRegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Person
        fields = (
            User.USERNAME_FIELD,
            User.get_email_field_name(),
            "first_name", "last_name", "password1", "password2")

    error_css_class = "error"
    required_css_class = "required"

    #tos = forms.BooleanField(
    #    widget=forms.CheckboxInput,
    #    label=_("I have read and agree to the Terms of Service"),
    #    error_messages={"required": validators.TOS_REQUIRED},
    #)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop(User.USERNAME_FIELD)
        email_field = User.get_email_field_name()
        if hasattr(self, "reserved_names"):
            reserved_names = self.reserved_names
        else:
            reserved_names = validators.DEFAULT_RESERVED_NAMES
        username_validators = [
            validators.ReservedNameValidator(reserved_names),
            validators.validate_confusables,
        ]
        #self.fields[User.USERNAME_FIELD].validators.extend(username_validators)
        self.fields[email_field].validators.extend(username_validators)
        self.fields[email_field].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def clean(self):
        cd = self.cleaned_data
        cd['username'] = cd['email']

        existing_players = Person.objects.filter(email=cd['email'])
        if existing_players.count() > 0:
            raise ValidationError("An account with that email address already exists.")


class TagForm(forms.Form):
    tagger_id = forms.CharField(label='Tagger (Zombie) ID', max_length=36)
    taggee_id = forms.CharField(label='Taggee (Human) ID / Body Armor ID', max_length=36)

    def clean(self):
        cd = self.cleaned_data

        tagger = cd.get("tagger_id")
        taggee = cd.get("taggee_id")
        this_game = get_active_game()
        try:
            tagger_status = PlayerStatus.objects.get(zombie_uuid=tagger, game=this_game)
        except:
            raise ValidationError("No Player with that Zombie ID found")
        if not (tagger_status.is_zombie() or tagger_status.is_staff()):
            raise ValidationError("Tagger is not a Zombie!")

        taggee_statuses = PlayerStatus.objects.filter(game=this_game).filter(Q(tag1_uuid=taggee) | Q(tag2_uuid=taggee))
        armors = BodyArmor.objects.filter(game=this_game).filter(Q(armor_uuid=taggee) | Q(armor_code=taggee))
        if len(armors) > 0 and len(taggee_statuses) > 0:
            raise ValidationError("Oh dear, that code matches a tag AND an armor")
        elif len(taggee_statuses) > 0:
            cd['type'] = "player"
            if len(taggee_statuses) > 1:
                raise ValidationError("Oh dear, that tag matches more than one player")
            taggee_status = taggee_statuses[0]
            if not taggee_status.is_human():
                raise ValidationError("Taggee is not a Human!")
            if taggee_status.status == "e":
                raise ValidationError("Cannot tag an extracted player!")
            if taggee_status.status == "v" and taggee != str(taggee_status.tag2_uuid):
                raise ValidationError("Tag #1 ID given, but player has already used AV!")
            if taggee_status.status == "h" and taggee != str(taggee_status.tag1_uuid):
                raise ValidationError("Tag #2 ID given, but player has not yet used AV!")
            cd["taggee"] = taggee_status
        elif len(armors) > 0:
            cd['type'] = "armor"
            if len(armors) > 1:
                raise ValidationError("Oh dear, that tag matches more than one armor")
            armor = armors[0]
            if datetime.now(tz=timezone('EST')) > armor.expiration_time:
                raise ValidationError("Armor is expired!")
            previous_tags = Tag.objects.filter(armor_taggee = armor, game=this_game)
            if len(previous_tags) > 0:
                raise ValidationError("Armor already used!")
            cd["taggee"] = armor
        else:
            raise ValidationError("No Human or Armor with that ID")
        cd["tagger"] = tagger_status
        # Validation complete
        return cd

class AVCreateForm(forms.ModelForm):
    class Meta:
        model = AntiVirus
        fields='__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['game'] = forms.CharField(widget = forms.HiddenInput(), required = False)

    def clean(self):
        cd = self.cleaned_data
        cd['game'] = get_active_game()
        return cd
    

class BlasterApprovalForm(forms.ModelForm):
    class Meta:
        model = Blaster
        fields=['name','owner','picture','avg_chrono']
    

class AVForm(forms.Form):
    av_code = forms.CharField(label='AV Code', max_length=36)    
    
    def clean(self):
        cd = self.cleaned_data
        av = cd.get("av_code")
        this_game = get_active_game()

        try:
            av = AntiVirus.objects.get(av_code=av, game=this_game)
        except:
            raise ValidationError("No AntiVirus with that ID found")

        if av.used_by is not None:
            raise ValidationError("AntiVirus already used!")

        if datetime.now(tz=timezone('EST')) > av.expiration_time:
            raise ValidationError("Sorry, this AV has expired")
        
        cd["av"] = av
        # Validation complete
        return cd

class BodyArmorCreateForm(forms.ModelForm):
    class Meta:
        model = BodyArmor
        fields=['armor_code','expiration_time']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expiration_time'].label = "Expiration Date/Time (YYYY-mm-dd HH:MM)"

class MissionForm(forms.ModelForm):
    class Meta:
        model = Mission
        fields = "__all__"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['go_live_time'].label = "When can players read the Non-Story form of the mission?"
        self.fields['story_form_go_live_time'].label =  "When can players read the Story form of the mission?"
        self.fields['game'] = forms.CharField(widget = forms.HiddenInput(), required = False)

    def clean(self):
        cd = self.cleaned_data
        cd['game'] = get_active_game()
        return cd

class PostGameSurveyForm(forms.ModelForm):
    class Meta:
        model = PostGameSurvey
        fields = "__all__"

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['game'] = forms.CharField(widget = forms.HiddenInput(), required = False)
        if len(args) > 0:
            for key in args[0].keys():
                if key.startswith("option_text_") and not key.startswith("option_text_id") or \
                      key.startswith("option_name_") and not key.startswith("option_name_id"):
                    self.fields[key] = forms.CharField()
    
        options = PostGameSurveyOption.objects.filter(
            survey=self.instance
        )
        for option in options:
            option_name_field = f'option_name_id_{option.id}'
            option_text_field = f"option_text_id_{option.id}"
            if len(args) > 0 and option_name_field not in args[0].keys():
                continue
            self.fields[option_name_field] = forms.CharField(required=False, label="")
            self.fields[option_text_field] = forms.CharField(required=False, label="", widget=forms.TextInput(attrs={'size':80}))
            try:
                self.initial[option_name_field] = option.option_name
            except IndexError:
                self.initial[option_name_field] = ""
            try:
                self.initial[option_text_field] = option.option_text
            except IndexError:
                self.initial[option_text_field] = ""

    def clean(self):
        options = []
        #print(self.cleaned_data.keys())
        option_text_field_names = [key for key in self.cleaned_data.keys() if "option_text" in key]
        for option_text_field_name in option_text_field_names:
            option_name_field_name = option_text_field_name.replace('option_text','option_name')
            if option_name_field_name not in self.cleaned_data.keys():
                self.add_error(option_text_field_name, "no matching field name")
            option = {
                "name": self.cleaned_data[option_name_field_name],
                "text": self.cleaned_data[option_text_field_name]
            }
            if "_id_" in option_text_field_name:
                option['id'] = int(option_text_field_name.split('_')[-1])
            else:
                option['id'] = None
            options.append(option)
            
        self.cleaned_data['game'] = get_active_game()
        self.cleaned_data["options"] = options

                         
    def save(self):
        survey = self.instance
        survey.save()
        existing_options = set([option.id for option in PostGameSurveyOption.objects.filter(survey=survey)])
        for option in self.cleaned_data["options"]:
            if option.get("id") is not None:
                # Existing option
                existing_options.remove(option.get('id'))
                existing_option = PostGameSurveyOption.objects.get(id=option.get('id'))
                existing_option.option_name = option.get('name')
                existing_option.option_text = option.get('text')
                print(f"Update: Option {option.get('id')}")
                existing_option.save()
            else:
                new_option = PostGameSurveyOption.objects.create(option_name=option.get('name'), option_text=option.get('text'), survey=survey)
                print(f"New: Option {new_option.id}")
                new_option.save()
        for option_to_delete in existing_options:
            print(f"Delete: Option {option_to_delete}")
            PostGameSurveyOption.objects.get(id=option_to_delete).delete()

    def get_options(self):
        for field_name in self.fields:
            if field_name.startswith("option_name"):
                opposite_field = field_name.replace('name','text')
                yield (self[field_name], self[opposite_field])


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["report_text", "reporter_email", "picture"]
    
    def __init__(self, *args, **kwargs):
        authenticated = kwargs.pop("authenticated", None)
        super().__init__(*args, **kwargs)
        self.fields['picture'].required = False
        self.fields['report_text'].widget.attrs['cols'] = 80
        if authenticated:
            self.fields.pop("reporter_email")
        else:
            self.fields["reporter_email"].label = "Your email address (optional)"
            self.fields['captcha'] = CaptchaField()
            self.fields['captcha'].label = "Captcha (enter the answer to the math problem, not the text of it)"


class ReportUpdateForm(forms.ModelForm):
    update_status = forms.ChoiceField(choices=(('x','No change'),('n','New'),('i','Investigating'),('d','Dismissed'),('c','Closed')))
    
    class Meta:
        model = ReportUpdate
        fields = ['note']

    def __init__(self, *args, **kwargs):
        report = kwargs.pop("report", None)
        super().__init__(*args, **kwargs)
        self.fields['note'].widget.attrs['cols'] = 80
        if report:
            self.fields['reportees'] = forms.ModelMultipleChoiceField(queryset=Person.objects.filter(playerstatus__game=get_active_game()) \
                                                        .filter(playerstatus__status__in=['h','v','e','z','o','x']) \
                                                        .annotate(num_status=Count('playerstatus')) \
                                                        .filter(num_status=1)   )
            self.fields['reportees'].initial = report.reportees.all()
            self.fields['reportees'].required = False

class RulesUpdateForm(forms.ModelForm):
    class Meta:
        model = Rules
        fields = ['rules_text']

class AboutUpdateForm(forms.ModelForm):
    class Meta:
        model = About
        fields = ['about_text']

class ClanCreateForm(forms.ModelForm):
    class Meta:
        model = Clan
        fields = ["name", "picture", "color"]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['color'].widget = forms.TextInput(attrs={'data-coloris':''})

        
    def clean(self):
        cd = self.cleaned_data
        existing_clans = Clan.objects.filter(name__iexact=cd['name'])
        if existing_clans.count() > 0 and (self.instance is None or self.instance != existing_clans[0]):
            raise ValidationError("A clan with that name already exists.")


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["short_form", "long_form", "active"]


class NameChangeForm(forms.Form):
    first_name = forms.CharField(label='First Name', max_length=50)
    last_name = forms.CharField(label='Last Name', max_length=50)