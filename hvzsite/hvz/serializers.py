from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import Person


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Person
        fields = ['url', 'first_name', 'last_name', 'zombie_uuid', 'role']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']
