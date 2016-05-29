
import pytest

from register_service.serializers import UpdateRequestSerializer, UpdateItemSerializer


pytestmark = pytest.mark.django_db


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
    assert update_request.identity == simple_identity
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
