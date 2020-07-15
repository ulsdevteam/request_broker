from rest_framework import serializers

from .models import MachineUser


class MachineUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MachineUser
        fields = ['system_name', 'host_location', 'api_key', 'is_active']

    def create(self, validated_data):
        return MachineUser.objects.create(**validated_data)
