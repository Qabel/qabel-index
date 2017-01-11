from pathlib import Path

import pytest
from pytest_postgresql.factories import init_postgresql_database, get_config

from django.conf import settings
from django.core import mail
from rest_framework.test import APIClient

from index_service.models import Identity, Entry
from index_service.crypto import encode_key

ALIAS = 'qabel_user'
PRIVATE_KEY = b'\x77\x07\x6d\x0a\x73\x18\xa5\x7d\x3c\x16\xc1\x72\x51\xb2\x66\x45\xdf\x4c\x2f\x87\xeb\xc0\x99\x2a\xb1\x77\xfb\xa5\x1d\xb9\x2c\x2a'
PUBLIC_KEY = b'\x85\x20\xf0\x09\x89\x30\xa7\x54\x74\x8b\x7d\xdc\xb4\x3e\xf7\x5a\x0d\xbf\x3a\x0d\x26\x38\x1a\xf4\xeb\xa4\xa9\x8e\xaa\x9b\x4e\x6a'


@pytest.fixture()
def tests_output_path():
    output_path = Path(__file__).absolute().parent / 'test-output'
    output_path.mkdir(exist_ok=True)
    return output_path


@pytest.fixture()
def write_mail(tests_output_path):
    def mail_writer(where, outbox_index=0):
        with (tests_output_path / ('email-' + where)).with_suffix('.eml').open('wb') as file:
            file.write(mail.outbox[outbox_index].message().as_bytes())
    return mail_writer


@pytest.fixture
def public_key():
    return PUBLIC_KEY


@pytest.fixture
def private_key():
    return PRIVATE_KEY


@pytest.fixture
def identity(db):
    identity = Identity(alias=ALIAS, drop_url='http://localhost/1234567890123456789012345678901234567890123', public_key=encode_key(PUBLIC_KEY))
    identity.save()
    return identity


@pytest.fixture
def email_entry(identity):
    entry = Entry(field='email', value='foo@example.com', identity=identity)
    entry.save()
    return entry


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def simple_identity():
    return {
        'public_key': encode_key(PUBLIC_KEY),
        'drop_url': 'http://localhost/1234567890123456789012345678901234567890123',
        'alias': 'public alias',
    }


@pytest.fixture(scope='session', autouse=True)
def apply_database_plumbing(request, postgresql_proc):
    """Bolt pytest-dbfixtures onto Django to work around its lack of no-setup testing facilities."""
    config = get_config(request)
    config['db'] = 'tests'
    settings.DATABASES['default'].update({
        'NAME': config['db'],
        'USER': config['user'],
        'HOST': postgresql_proc.host,
        'PORT': postgresql_proc.port,
    })
    init_postgresql_database(config['user'], postgresql_proc.host, postgresql_proc.port, config['db'])


@pytest.fixture(autouse=True)
def implicit_db_use(db):
    pass
