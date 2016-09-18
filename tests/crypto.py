
from django.core.checks import Error

import pytest

from index_service.crypto import check_server_private_key


@pytest.mark.parametrize('private_key', (
    '123', b'1234', bytes(31), bytes(31).hex()
))
def test_check_server_private_key_invalid(settings, private_key):
    settings.SERVER_PRIVATE_KEY = private_key
    errors = check_server_private_key(None)
    assert errors
    assert isinstance(errors[0], Error)


@pytest.mark.parametrize('private_key', (
    None, bytes(32), bytes(32).hex()
))
def test_check_server_private_key(settings, private_key):
    settings.SERVER_PRIVATE_KEY = private_key
    errors = check_server_private_key(None)
    assert not errors
