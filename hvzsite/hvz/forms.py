from django import forms
from django.forms import ValidationError
from django.db.models import Count, Q
from .models import Person, Blaster, BodyArmor, AntiVirus, PlayerStatus, get_latest_game
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
    taggee_id = forms.CharField(label='Taggee (Human) ID', max_length=36)

    def clean(self):
        cd = self.cleaned_data

        tagger = cd.get("tagger_id")
        taggee = cd.get("taggee_id")
        this_game = get_latest_game()
        try:
            tagger_status = PlayerStatus.objects.get(zombie_uuid=tagger, game=this_game)
        except:
            raise ValidationError("No Player with that Zombie ID found")
        
        taggee_status = None
        try:
            taggee_status = PlayerStatus.objects.get(tag1_uuid=taggee, game=this_game)
            #if taggee_status.status != "h":
            #    raise ValidationError("Taggee Human ID #1 given, but that ID was already tagged!")
        except:
            pass
        try:
            taggee_status = PlayerStatus.objects.get(tag2_uuid=taggee, game=this_game)
            #if taggee_status.status != "v":
            #    raise ValidationError("Taggee Human ID #2 given, but ID #1 wasn't used yet!")
        except:
            pass
        if taggee_status is None:
            raise ValidationError("No player with that Human ID found")
        
        if not (tagger_status.is_zombie() or tagger_status.is_admin()):
            raise ValidationError("Tagger is not a Zombie!")
        if not taggee_status.is_human():
            raise ValidationError("Taggee is not a Human!")
        
        cd["tagger"] = tagger_status
        cd["taggee"] = taggee_status
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
    player_id = forms.CharField(label='Player (Zombie) ID', max_length=36)
    av_code = forms.CharField(label='AV Code', max_length=36)    
    
    def clean(self):
        cd = self.cleaned_data

        player = cd.get("player_id")
        av = cd.get("av_code")
        this_game = get_latest_game()
        try:
            player_status = PlayerStatus.objects.get(zombie_uuid=player, game=this_game)
        except:
            raise ValidationError("No Player with that Zombie ID found")
        try:
            av = AntiVirus.objects.get(av_code=av, game=this_game)
        except:
            raise ValidationError("No AntiVirus with that ID found")
        
        if not player_status.is_zombie():
            raise ValidationError("Player is not a Zombie!")
        if av.used_by is not None:
            raise ValidationError("AntiVirus already used!")
        if len(AntiVirus.objects.filter(game=this_game, used_by=player_status.player)) > 0:
            raise ValidationError("Player has already used an AV this game!")

        if datetime.now(tz=timezone('EST')) > av.expiration_time:
            raise ValidationError("Sorry, this AV has expired")
        
        cd["player"] = player_status
        cd["av"] = av
        # Validation complete
        return cd

class BodyArmorCreateForm(forms.ModelForm):
    class Meta:
        model = BodyArmor
        fields='__all__'
