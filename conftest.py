import pytest
from register_service.models import Identity
ALIAS = 'qabel_user'


@pytest.fixture
def identity(db):
    try:
        identity = Identity.objects.get(alias=ALIAS)
    except Identity.DoesNotExist:
        identity = Identity(alias=ALIAS, drop_url='http://127.0.0.1:6000/')
        identity.save()
    return identity
