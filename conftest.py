import pytest
from rest_framework.test import APIClient

from register_service.models import Identity

ALIAS = 'qabel_user'


@pytest.fixture
def identity(db):
    try:
        identity = Identity.objects.get(alias=ALIAS)
    except Identity.DoesNotExist:
        identity = Identity(alias=ALIAS, drop_url='http://127.0.0.1:6000/qabel_user', public_key='Qabel')
        identity.save()
    return identity

@pytest.fixture
def api_client():
    return APIClient()