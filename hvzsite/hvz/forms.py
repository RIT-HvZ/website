from django import forms
from django.forms import ValidationError
from .models import AntiVirus, PlayerStatus, get_latest_game
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Person


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
        
        if not tagger_status.is_zombie():
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

class AVForm(forms.Form):
    player_id = forms.CharField(label='Player (Zombie) ID', max_length=36)
    av_id = forms.CharField(label='AV ID', max_length=36)

    def clean(self):
        cd = self.cleaned_data

        player = cd.get("player_id")
        av = cd.get("av_id")
        this_game = get_latest_game()
        try:
            player_status = PlayerStatus.objects.get(zombie_uuid=player, game=this_game)
        except:
            raise ValidationError("No Player with that Zombie ID found")
        try:
            av = AntiVirus.objects.get(av_id=av, game=this_game)
        except:
            raise ValidationError("No AntiVirus with that ID found")
        
        if not player_status.is_zombie():
            raise ValidationError("Player is not a Zombie!")
        if av.used_by is not None:
            raise ValidationError("AntiVirus already used!")
        if len(AntiVirus.objects.filter(game=this_game, used_by=player_status.player)) > 0:
            raise ValidationError("Player has already used an AV this game!")
        
        cd["player"] = player_status
        cd["av"] = av
        # Validation complete
        return cd