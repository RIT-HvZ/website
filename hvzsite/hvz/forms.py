from django import forms
from django.forms import ValidationError
from django.db.models import Count, Q
from .models import Person, Blaster, BodyArmor, AntiVirus, PlayerStatus, get_latest_game, Tag
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from datetime import datetime
from pytz import timezone
from django_registration.forms import RegistrationForm
from django.utils.translation import gettext_lazy as _
from django_registration import validators

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


# Create your forms here.
class LoginForm(forms.Form):
    email = forms.CharField(label='Email', max_length=100)
    password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = Person

class NewUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True

    class Meta:
        model = Person
        fields = ("email", "first_name", "last_name", "password1", "password2")

    def save(self, commit=True):
        user = super(NewUserForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class TagForm(forms.Form):
    tagger_id = forms.CharField(label='Tagger (Zombie) ID', max_length=36)
    taggee_id = forms.CharField(label='Taggee (Human) ID / Body Armor ID', max_length=36)

    def clean(self):
        cd = self.cleaned_data

        tagger = cd.get("tagger_id")
        taggee = cd.get("taggee_id")
        this_game = get_latest_game()
        try:
            tagger_status = PlayerStatus.objects.get(zombie_uuid=tagger, game=this_game)
        except:
            raise ValidationError("No Player with that Zombie ID found")
        if not (tagger_status.is_zombie() or tagger_status.is_admin()):
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

class BlasterApprovalForm(forms.ModelForm):
    class Meta:
        model = Blaster
        fields=['name','owner','picture','avg_chrono']
    

class AVForm(forms.Form):
    av_code = forms.CharField(label='AV Code', max_length=36)    
    
    def clean(self):
        cd = self.cleaned_data
        av = cd.get("av_code")
        this_game = get_latest_game()

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
        self.fields['expiration_time'].label = "Expiration Date/Time (YYYY/mm/dd HH:MM)"
        self.fields['expiration_time'].input_formats = ["%Y/%m/%d %H:%M"]

