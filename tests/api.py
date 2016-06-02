
import json
import base64

import pytest

import mail_templated

from register_service.models import Entry
from register_service.logic import UpdateRequest, UpdateItem


class RootTest:
    def test_root(self, api_client):
        response = api_client.get('/api/v0/')
        assert len(response.data) == 3


class KeyTest:
    @pytest.mark.xfail
    def test_get_key(self, api_client):
        response = api_client.get('/api/v0/key/')
        assert response.status_code == 200
        pubkey = base64.b64decode(response.data['pubkey'])
        assert len(pubkey) == 32
        # The public key is ephemeral (generated when the server starts); can't really check much else.


class SearchTest:
    path = '/api/v0/search/'

    def test_get_identity(self, api_client, email_entry):
        response = api_client.get(self.path, {'email': email_entry.value})
        assert response.status_code == 200
        result = response.data
        assert len(result) == 1
        assert result[0]['alias'] == 'qabel_user'
        assert result[0]['drop_url'] == 'http://127.0.0.1:6000/qabel_user'

    def test_get_no_identity(self, api_client):
        response = api_client.get(self.path, {'email': 'no_such_email@example.com'})
        assert response.status_code == 200
        assert len(response.data) == 0

    def test_no_full_match(self, api_client, email_entry):
        response = api_client.get(self.path, {'email': email_entry.value,
                                              'phone': '123456789'})
        assert not response.data

    def test_match_is_exact(self, api_client, email_entry):
        response = api_client.get(self.path, {'email': email_entry.value + "a"})
        assert not response.data
        response = api_client.get(self.path, {'email': "a" + email_entry.value})
        assert not response.data

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
        mocker.patch.object(UpdateRequest, 'start_verification', lambda self, _: self.execute())
        response = api_client.put(self.path, request, content_type='application/json')
        assert response.status_code == 202

    @pytest.fixture
    def delete_prerequisite(self, api_client, mocker, email_entry):
        # Maybe use pytest-bdd here?
        # pls more fixtures
        send_mail = mail_templated.send_mail = mocker.patch('mail_templated.send_mail', autospec=True)
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
        assert response.status_code == 202

        assert send_mail.call_count == 1
        mail_args = send_mail.call_args[1]
        assert mail_args['recipient_list'] == [email_entry.value]
        mail_context = mail_args['context']
        assert mail_context['identity'] == email_entry.identity

        return mail_context

    def test_delete_confirm(self, api_client, delete_prerequisite, email_entry):
        confirm_url = delete_prerequisite['confirm_url']

        # At this point the entry still exists
        assert Entry.objects.filter(value=email_entry.value).count() == 1
        # User clicks the confirm link
        response = api_client.get(confirm_url)
        assert response.status_code == 200
        # Entry should be gone now
        assert Entry.objects.filter(value=email_entry.value).count() == 0

    def test_delete_deny(self, api_client, delete_prerequisite, email_entry):
        deny_url = delete_prerequisite['deny_url']

        assert Entry.objects.filter(value=email_entry.value).count() == 1
        # User clicks the deny link
        response = api_client.get(deny_url)
        assert response.status_code == 200
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
        assert response.status_code == 400
