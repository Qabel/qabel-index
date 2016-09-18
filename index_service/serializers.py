from django.conf import settings

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from index_service.logic import UpdateRequest, UpdateItem
from index_service.models import Identity, Entry
from index_service.crypto import decode_key
from index_service.utils import normalize_phone_number_localised, parse_phone_number, get_current_cc


FIELD_SCRUBBERS = {
    'phone': normalize_phone_number_localised
}


def scrub_field(field, value):
    scrubber = FIELD_SCRUBBERS.get(field)
    if scrubber:
        return scrubber(value)
    else:
        return value


class IdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Identity
        fields = ('alias', 'public_key', 'drop_url')

    def run_validators(self, value):
        for validator in self.validators:
            if isinstance(validator, UniqueTogetherValidator):
                # remove the auto-generated UniqueTogetherValidator so that we get to implement get_or_create
                # semantics
                self.validators.remove(validator)
        super().run_validators(value)

    def update(self, instance, validated_data):
        instance.alias = validated_data.get('alias', instance.alias)
        instance.public_key = validated_data.get('public_key', instance.public_key)
        instance.drop_url = validated_data.get('drop_url', instance.drop_url)
        instance.save()
        return instance

    def create(self, validated_data):
        identity, _ = Identity.objects.get_or_create(defaults=validated_data, **validated_data)
        return identity

    def validate_public_key(self, value):
        try:
            decode_key(value)
        except ValueError:
            raise ValidationError('public key must be 64 hex characters.') from None
        return value


class FieldSerializer(serializers.Serializer):
    field = serializers.ChoiceField(Entry.FIELDS)
    value = serializers.CharField()

    def create(self, validated_data):
        return validated_data


class SearchResultSerializer(IdentitySerializer):
    matches = FieldSerializer(many=True)

    class Meta(IdentitySerializer.Meta):
        fields = IdentitySerializer.Meta.fields + ('matches',)


class SearchSerializer(serializers.Serializer):
    query = FieldSerializer(many=True, required=True)

    def create(self, validated_data):
        return validated_data


class UpdateItemSerializer(serializers.Serializer):
    action = serializers.ChoiceField(('create', 'delete'))
    field = serializers.ChoiceField(Entry.FIELDS)
    value = serializers.CharField()

    def validate(self, data):
        field = data['field']
        try:
            data['value'] = scrub_field(field, data['value'])
        except ValueError as exc:
            raise serializers.ValidationError('Scrubber for %r failed: %s' % (field, exc)) from exc
        if field == 'phone':
            country_code = parse_phone_number(data['value'], get_current_cc()).country_code
            if country_code not in settings.SMS_ALLOWED_COUNTRIES:
                raise serializers.ValidationError('This country code (+%d) is not available at this time.' % country_code)
        return data

    def create(self, validated_data):
        return UpdateItem(action=validated_data['action'],
                          field=validated_data['field'],
                          value=validated_data['value'])


class UpdateRequestSerializer(serializers.Serializer):
    identity = IdentitySerializer(required=True)
    public_key_verified = serializers.BooleanField(default=False)
    items = UpdateItemSerializer(many=True, required=True)

    def create(self, validated_data):
        items = []
        for item in validated_data['items']:
            # XXX easier way?
            subser = UpdateItemSerializer(data=item)
            subser.is_valid(True)
            items.append(subser.save())
        idser = IdentitySerializer(data=validated_data['identity'])
        idser.is_valid(True)
        identity = idser.save()
        request = UpdateRequest(identity, validated_data['public_key_verified'], items)
        return request

    def validate_items(self, value):
        if not value:
            raise ValidationError('At least one update item is required.')
        items = []
        for item in value:
            if item in items:
                raise ValidationError('Duplicate update items are not allowed.')
            items.append(item)
        return value
