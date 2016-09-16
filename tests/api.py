
import json

import pytest

from django.core import mail

from rest_framework import status

from index_service.crypto import decode_key
from index_service.models import Entry
from index_service.logic import UpdateRequest


class RootTest:
    def test_root(self, api_client):
        response = api_client.get('/api/v0/')
        assert len(response.data) == 3


class KeyTest:
    def test_get_key(self, api_client):
        response = api_client.get('/api/v0/key/')
        assert response.status_code == status.HTTP_200_OK
        decode_key(response.data['public_key'])
        # The public key is ephemeral (generated when the server starts); can't really check much else.


class SearchTest:
    path = '/api/v0/search/'

    def test_get_identity(self, api_client, email_entry):
        response = api_client.get(self.path, {'email': email_entry.value})
        assert response.status_code == status.HTTP_200_OK
        result = response.data['identities']
        assert len(result) == 1
        assert result[0]['alias'] == 'qabel_user'
        assert result[0]['drop_url'] == 'http://127.0.0.1:6000/qabel_user'

    def test_get_no_identity(self, api_client):
        response = api_client.get(self.path, {'email': 'no_such_email@example.com'})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['identities']) == 0

    def test_no_full_match(self, api_client, email_entry):
        response = api_client.get(self.path, {'email': email_entry.value,
                                              'phone': '123456789'})
        assert not response.data['identities']

    def test_match_is_exact(self, api_client, email_entry):
        response = api_client.get(self.path, {'email': email_entry.value + "a"})
        assert not response.data['identities']
        response = api_client.get(self.path, {'email': "a" + email_entry.value})
        assert not response.data['identities']

    # XXX phone number tests
    # XXX check that phone numbers are normalized (always have a cc/country code e.g. +49...)


class UpdateTest:
    path = '/api/v0/update/'

    def test_create(self, api_client, mocker, simple_identity):
        request = json.dumps({
            'identity': simple_identity,
            'items': [
                {
                    'action': 'create',
                    'field': 'email',
                    'value': 'onlypeople_who_knew_this_address_already_can_find_the_entry@example.com',
                }
            ]
        })
        # Short-cut verification to execution
        mocker.patch.object(UpdateRequest, 'start_verification', lambda self, *_: self.execute())
        response = api_client.put(self.path, request, content_type='application/json')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.parametrize('accept_language', (
        'de-de',  # an enabled language, also the default
        'ko-kr',  # best korea
        None,  # no header set
    ))
    @pytest.mark.parametrize('phone_number, search_number', (
        ('+661234', '+661234'),
        ('1234', '+491234'),
    ))
    def test_create_phone_normalization(self, api_client, mocker, simple_identity, phone_number, accept_language, search_number):
        self._test_create_phone(api_client, mocker, simple_identity, phone_number, accept_language, search_number)

    @pytest.mark.parametrize('phone_number, accept_language, search_number', (
        ('555', 'en-us', '+1555'),
    ))
    def test_create_phone(self, api_client, mocker, simple_identity, phone_number, accept_language, search_number):
        self._test_create_phone(api_client, mocker, simple_identity, phone_number, accept_language, search_number)

    def _test_create_phone(self, api_client, mocker, simple_identity, phone_number, accept_language, search_number):
        request = json.dumps({
            'identity': simple_identity,
            'items': [
                {
                    'action': 'create',
                    'field': 'phone',
                    'value': phone_number,
                }
            ]
        })
        # Short-cut verification to execution
        mocker.patch.object(UpdateRequest, 'start_verification', lambda self, *_: self.execute())
        kwargs = {}
        if accept_language:
            kwargs['HTTP_ACCEPT_LANGUAGE'] = accept_language
        response = api_client.put(self.path, request, content_type='application/json', **kwargs)
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.json()
        response = api_client.get(SearchTest.path, {'phone': search_number})
        assert response.status_code == status.HTTP_200_OK, response.json()
        result = response.data['identities']
        assert len(result) == 1
        assert result[0]['alias'] == 'public alias'
        assert result[0]['drop_url'] == 'http://example.com'

    @pytest.fixture
    def delete_prerequisite(self, api_client, email_entry):
        # Maybe use pytest-bdd here?
        # pls more fixtures
        request = json.dumps({
            'identity': {
                'public_key': email_entry.identity.public_key,
                'drop_url': email_entry.identity.drop_url,
                'alias': email_entry.identity.alias,
            },
            'items': [
                {
                    'action': 'delete',
                    'field': 'email',
                    'value': email_entry.value,
                }
            ]
        })
        response = api_client.put(self.path, request, content_type='application/json')
        assert response.status_code == status.HTTP_202_ACCEPTED

        assert len(mail.outbox) == 1
        message = mail.outbox.pop()
        assert message.to == [email_entry.value]
        message_context = message.context
        assert message_context['identity'] == email_entry.identity

        return message_context

    def test_delete_confirm(self, api_client, delete_prerequisite, email_entry):
        confirm_url = delete_prerequisite['confirm_url']

        # At this point the entry still exists
        assert Entry.objects.filter(value=email_entry.value).count() == 1
        # User clicks the confirm link
        response = api_client.get(confirm_url)
        assert response.status_code == status.HTTP_200_OK
        # Entry should be gone now
        assert Entry.objects.filter(value=email_entry.value).count() == 0

    def test_delete_deny(self, api_client, delete_prerequisite, email_entry):
        deny_url = delete_prerequisite['deny_url']

        assert Entry.objects.filter(value=email_entry.value).count() == 1
        # User clicks the deny link
        response = api_client.get(deny_url)
        assert response.status_code == status.HTTP_200_OK
        # Entry should still exist
        assert Entry.objects.filter(value=email_entry.value).count() == 1

    @pytest.mark.parametrize('invalid_request', [
        {},
        {'items': "a string?"},
        {'items': []},
        {
            'items': [
                {
                    'action': 'well that ain’t valid'
                }
            ]
        },
    ])
    def test_invalid(self, api_client, invalid_request, simple_identity):
        invalid_request['identity'] = simple_identity
        request = json.dumps(invalid_request)
        response = api_client.put(self.path, request, content_type='application/json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_encrypted(self, api_client, settings):
        encrypted_json = bytes.fromhex('cc0330af7d17d21a58f3c277897b12904059606a323807c3a52d07c50b1814114a1472efb3f3ff9'
                                       '73fbf5480f6e2d09278cd3db3c926c1e1bccb387d140da50404b7fd187eb9fdc79c281a0880ca5f'
                                       'ef8679b65e0bda2f6e249d076318063c58913dae8225cd162edda5d76b2040a96064bcce2c32ae4'
                                       'c0627578ab8e7ae8f99a435e1e3a28fd712e04da3cc7f8a7b302e11dd0127dc1291b551ae95c0a1'
                                       '813759c0a78e10d6705f2f68b79ddc8f5c387f8b78c869a3c97274e2221b1551be6c3e9ed08bd24'
                                       'd6232553bc746cb7e8e58432bd5429e8d203c1ac96c6a18097e3a5d2eb5d30d7c5387fc93e54be8'
                                       'facaf3c01b70059b0a411d3b8a78ac4e34be9711df8771cecc365a27a0915dc5ac05951dede527e'
                                       'd8e701af52886ae237bf0a0b109337b1bcc172550ddfb200aeb2bd8493a84ea6a1dca891d720030'
                                       '3ffc880c07d1cf9dac6d1296191fca487f73f9d1e62071c383a003ce39fbd4f7ea5ce82d8a89007'
                                       '3220d440adef42c75be61d52853355f725e41fcf6d45e8918a68ca87addc3b0fd5efa868c7c8bee'
                                       '15242e37b830340598f6f92e9d42d387ca3be199b14da56004ae78a8242352413c733f55744199e'
                                       '640317298a38bbb59bc622baab0ba0ecebc2a92a1d7b12f86263b5e9ed93af36af685cf18dd551a'
                                       '5e084ada8a0148612e86e68636a30a23dbc4fc807a4bd279a0aa7f37d6a0437116c76589e9')
        settings.FACET_SHALLOW_VERIFICATION = True
        response = api_client.put(self.path, encrypted_json, content_type='application/vnd.qabel.noisebox+json')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Find this identity
        response = api_client.get(SearchTest.path, {'email': 'test-b24aadf6-7fd9-43b0-86e7-eef9a6d24c65@example.net'})
        assert response.status_code == status.HTTP_200_OK
        result = response.data['identities']
        assert len(result) == 1
        assert result[0]['alias'] == 'Major Anya'
        assert result[0]['public_key'] == '434c0dc39e1dab114b965154c196155bec20071ab75936441565e07f6f9a3022'

    def test_encrypted_failure(self, api_client, settings):
        encrypted_json = bytes.fromhex('cc0330af7d17d21a58f3c277897b1290405960')
        response = api_client.put(self.path, encrypted_json, content_type='application/vnd.qabel.noisebox+json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
