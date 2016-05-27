
import pytest

from register_service.serializers import UpdateRequestSerializer, UpdateItemSerializer


pytestmark = pytest.mark.django_db


def make_update_item(type='email', value='foo@example.com', action='create'):
    return {
        'action': action,
        'identity': {
            'public_key': 'this would be a public key',
            'drop_url': 'http://example.com',
            'alias': 'public alias',
        },
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
    d = make_update_item()
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
    remove_key(make_update_item(), 'identity'),
    remove_key(make_update_item(), 'identity.public_key'),
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
    assert item.identity == {
        'public_key': 'this would be a public key',
        'drop_url': 'http://example.com',
        'alias': 'public alias',
    }


@pytest.mark.parametrize('invalid', [
    {},
    {
        'items': []
    },
])
def test_invalid_request(invalid):
    serializer = UpdateRequestSerializer(data=invalid)
    assert not serializer.is_valid()


def test_single_item():
    request = {
        'items': [make_update_item('email', 'asdf@example.com')]
    }
    serializer = UpdateRequestSerializer(data=request)
    assert serializer.is_valid(), serializer.errors
    update_request = serializer.save()
    assert len(update_request.items) == 1
    item = update_request.items[0]
    assert item.action == 'create'
    assert item.field == 'email'
    assert item.value == 'asdf@example.com'
    assert item.identity == {
        'public_key': 'this would be a public key',
        'drop_url': 'http://example.com',
        'alias': 'public alias',
    }


def test_identical_items():
    request = {
        'items': [
            make_update_item('email', 'asdf@example.com'),
            make_update_item('email', 'asdf@example.com')
        ]
    }
    serializer = UpdateRequestSerializer(data=request)
    assert not serializer.is_valid()


def test_similar_items():
    request = {
        'items': [
            make_update_item('email', 'asdf@example.com'),
            make_update_item('email', 'asdf@example.com', action='delete')
        ]
    }
    serializer = UpdateRequestSerializer(data=request)
    assert serializer.is_valid()
