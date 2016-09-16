
from django.utils import translation

import pytest

from index_service.serializers import IdentitySerializer, UpdateRequestSerializer, UpdateItemSerializer


def make_update_item(type='email', value='foo@example.com', action='create'):
    return {
        'action': action,
        'field': type,
        'value': value,
    }


def remove_key(some_dict, item_path):
    """Return *some_dict* (dict[-of-dicts]) with dotted *item_path* removed."""
    item_stack = item_path.split('.')
    current_dict = some_dict
    for item in item_stack[:-1]:
        current_dict = current_dict[item]
    del current_dict[item_stack[-1]]
    return some_dict


# of course some tests for this helper
def test_remove_key_first_level():
    d = make_update_item('1234', '56789')
    d = remove_key(d, 'action')
    assert 'action' not in d


def test_remove_key_nested():
    d = {
        'identity': {
            'public_key': 1234
        }
    }
    d = remove_key(d, 'identity.public_key')
    assert 'public_key' not in d['identity']


def test_remove_key_keyerror():
    d = make_update_item()
    with pytest.raises(KeyError):
        remove_key(d, 'ädentity')
    with pytest.raises(KeyError):
        remove_key(d, 'identity..')


@pytest.mark.parametrize('invalid', [
    {},
    {
        'action': 'create'
    },
    remove_key(make_update_item(), 'value'),
])
def test_invalid_item(invalid):
    serializer = UpdateItemSerializer(data=invalid)
    assert not serializer.is_valid()


def test_simple_item():
    serializer = UpdateItemSerializer(data=make_update_item('email', 'asdf@example.com'))
    assert serializer.is_valid(), serializer.errors
    item = serializer.save()
    assert item.field == 'email'
    assert item.value == 'asdf@example.com'


def test_phone_item():
    serializer = UpdateItemSerializer(data=make_update_item('phone', '1234'))
    assert serializer.is_valid(), serializer.errors
    item = serializer.save()
    assert item.field == 'phone'
    assert item.value == '+491234'


def test_phone_item_international():
    serializer = UpdateItemSerializer(data=make_update_item('phone', '+631234'))
    assert serializer.is_valid(), serializer.errors
    item = serializer.save()
    assert item.field == 'phone'
    assert item.value == '+631234'


@pytest.mark.parametrize('locale, input, output', (
    ('en-us', '555-1234', '+15551234'),
    # Yes, the US actually has "1" as their country calling code.
    ('ky-kg', '555-1234', '+9965551234'),
    # Kyrgyzstan on the other hand has 996. Priorities, nuclear super power etc.
))
def test_phone_item_international_request(locale, input, output):
    with translation.override(locale):
        serializer = UpdateItemSerializer(data=make_update_item('phone', input))
        assert serializer.is_valid(), serializer.errors
        item = serializer.save()
    assert item.field == 'phone'
    assert item.value == output


@pytest.mark.parametrize('invalid', [
    {},
    {
        'items': []
    },
])
def test_invalid_request(invalid):
    serializer = UpdateRequestSerializer(data=invalid)
    assert not serializer.is_valid()


def test_single_item(simple_identity):
    request = {
        'identity': simple_identity,
        'items': [make_update_item('email', 'asdf@example.com')]
    }
    serializer = UpdateRequestSerializer(data=request)
    assert serializer.is_valid(), serializer.errors
    update_request = serializer.save()
    assert len(update_request.items) == 1
    identity = update_request.identity
    assert identity.public_key == simple_identity['public_key']
    assert identity.drop_url == simple_identity['drop_url']
    assert identity.alias == simple_identity['alias']
    item = update_request.items[0]
    assert item.action == 'create'
    assert item.field == 'email'
    assert item.value == 'asdf@example.com'


def test_identical_items(simple_identity):
    request = {
        'identity': simple_identity,
        'items': [
            make_update_item('email', 'asdf@example.com'),
            make_update_item('email', 'asdf@example.com')
        ]
    }
    serializer = UpdateRequestSerializer(data=request)
    assert not serializer.is_valid()
    assert 'Duplicate update items are not allowed.' in serializer.errors['items']


def test_similar_items(simple_identity):
    request = {
        'identity': simple_identity,
        'items': [
            make_update_item('email', 'asdf@example.com'),
            make_update_item('email', 'asdf@example.com', action='delete')
        ]
    }
    serializer = UpdateRequestSerializer(data=request)
    assert serializer.is_valid(), serializer.errors


def test_identity_deserialize_multiple(simple_identity):
    def deserialize_and_save(data):
        idser = IdentitySerializer(data=simple_identity)
        idser.is_valid(True)
        return idser.save()
    identity1 = deserialize_and_save(simple_identity)
    identity2 = deserialize_and_save(simple_identity)
    assert identity1 == identity2
