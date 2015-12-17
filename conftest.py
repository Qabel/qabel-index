import pytest
from rest_framework.test import APIClient

from register_service.models import Identity

ALIAS = 'qabel_user'
PRIVATE_KEY = b'\x77\x07\x6d\x0a\x73\x18\xa5\x7d\x3c\x16\xc1\x72\x51\xb2\x66\x45\xdf\x4c\x2f\x87\xeb\xc0\x99\x2a\xb1\x77\xfb\xa5\x1d\xb9\x2c\x2a'
PUBLIC_KEY = b'\x85\x20\xf0\x09\x89\x30\xa7\x54\x74\x8b\x7d\xdc\xb4\x3e\xf7\x5a\x0d\xbf\x3a\x0d\x26\x38\x1a\xf4\xeb\xa4\xa9\x8e\xaa\x9b\x4e\x6a'


@pytest.fixture
def public_key():
    return PUBLIC_KEY

@pytest.fixture
def private_key():
    return PRIVATE_KEY

@pytest.fixture
def identity(db):
    try:
        identity = Identity.objects.get(alias=ALIAS)
    except Identity.DoesNotExist:
        identity = Identity(alias=ALIAS, drop_url='http://127.0.0.1:6000/qabel_user')
        identity.pub_key = PUBLIC_KEY
        identity.save()
    return identity

@pytest.fixture
def api_client():
    return APIClient()