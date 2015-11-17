from rest_framework import serializers

from register_service.models import Identity


class IdentitySerializer(serializers.ModelSerializer):

    class Meta:
        model = Identity
        fields = ('alias', 'public_key', 'drop_url', 'email', 'mobile')
        read_only = ('created_at', 'updated_at')