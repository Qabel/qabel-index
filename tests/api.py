
import datetime
import json

import pytest

from django.core import mail
from django.core.cache import cache
from django.forms.models import model_to_dict
from django.utils import timezone

from rest_framework import status

from index_service.crypto import decode_key
from index_service.models import Entry, Identity, PendingUpdateRequest
from index_service.logic import UpdateRequest
from index_service.utils import AccountingAuthorization, authorization_cache_key
from index_service.views import StatusView


class RootTest:
    def test_root(self, api_client):
        response = api_client.get('/api/v0/')
        assert len(response.data) == 3


class KeyTest:
    path = '/api/v0/key/'

    def test_get_key(self, api_client):
        response = api_client.get(self.path)
        assert response.status_code == status.HTTP_200_OK
        decode_key(response.data['public_key'])
        # The public key is ephemeral (generated when the server starts); can't really check much else.


class SearchTest:
    path = '/api/v0/search/'

    @pytest.fixture(params=('get', 'post'))
    def search_client(self, request, api_client):
        def client(query):
            if request.param == 'get':
                return api_client.get(self.path, query)
            else:
                transformed_query = []
                for field, value in query.items():
                    if isinstance(value, (list, tuple)):
                        for v in value:
                            transformed_query.append({'field': field, 'value': v})
                    else:
                        transformed_query.append({'field': field, 'value': value})
                q = json.dumps({'query': transformed_query})
                return api_client.post(self.path, q, content_type='application/json')
        return client

    def test_get_identity(self, search_client, email_entry):
        response = search_client({'email': email_entry.value})
        assert response.status_code == status.HTTP_200_OK, response.json()
        identities = response.data['identities']
        assert len(identities) == 1
        identity = identities[0]
        assert identity['alias'] == 'qabel_user'
        assert identity['drop_url'] == 'http://127.0.0.1:6000/qabel_user'
        matches = identity['matches']
        assert len(matches) == 1
        assert {'field': 'email', 'value': email_entry.value} in matches

    def test_get_no_identity(self, search_client):
        response = search_client({'email': 'no_such_email@example.com'})
        assert response.status_code == status.HTTP_200_OK, response.json()
        assert len(response.data['identities']) == 0

    def test_multiple_fields_are_ORed(self, search_client, email_entry):
        response = search_client({'email': email_entry.value, 'phone': '123456789'})
        assert response.status_code == status.HTTP_200_OK, response.json()
        identities = response.data['identities']
        assert len(identities) == 1
        identity = identities[0]
        assert identity['alias'] == 'qabel_user'
        assert identity['drop_url'] == 'http://127.0.0.1:6000/qabel_user'
        matches = identity['matches']
        assert len(matches) == 1
        assert {'field': 'email', 'value': email_entry.value} in matches

    def test_match_is_exact(self, search_client, email_entry):
        response = search_client({'email': email_entry.value + "a"})
        assert response.status_code == status.HTTP_200_OK, response.json()
        assert not response.data['identities']
        response = search_client({'email': "a" + email_entry.value})
        assert response.status_code == status.HTTP_200_OK, response.json()
        assert not response.data['identities']

    def test_cross_identity(self, search_client, email_entry, identity):
        pk2 = identity.public_key.replace('8520', '1234')
        identity2 = Identity(alias='1234', drop_url='http://127.0.0.1:6000/qabel_1234', public_key=pk2)
        identity2.save()
        phone1, phone2 = '+491234', '+491235'
        email = 'bar@example.net'
        Entry(identity=identity2, field='phone', value=phone1).save()
        Entry(identity=identity2, field='email', value=email).save()

        response = search_client({
            'email': (email_entry.value, email),
            'phone': phone1,
        })
        assert response.status_code == status.HTTP_200_OK, response.json()
        identities = response.data['identities']
        assert len(identities) == 2

    def test_unknown_field(self, search_client):
        response = search_client({'no such field': '...'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.json()

    def test_missing_query(self, api_client):
        response = api_client.post(self.path, '{}', content_type='application/json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.json()

    def test_empty_query(self, search_client):
        response = search_client({})
        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.json()
        # "No or unknown field spec'd" or "No fields spec'd"
        assert 'fields specified' in response.json()['error']


class UpdateTest:
    path = '/api/v0/update/'

    def _update_request_with_no_verification(self, api_client, mocker, simple_identity, items, **kwargs):
        request = json.dumps({
            'identity': simple_identity,
            'items': items
        })
        # Short-cut verification to execution
        mocker.patch.object(UpdateRequest, 'start_verification', lambda self, *_: self.execute())
        response = api_client.put(self.path, request, content_type='application/json', **kwargs)
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.json()

    def _search(self, api_client, what):
        response = api_client.get(SearchTest.path, what)
        assert response.status_code == status.HTTP_200_OK, response.json()
        result = response.data['identities']
        assert len(result) == 1
        identity = result[0]
        assert identity['alias'] == 'public alias'
        assert identity['drop_url'] == 'http://example.com'
        return identity

    def test_create(self, api_client, mocker, simple_identity):
        email = 'onlypeople_who_knew_this_address_already_can_find_the_entry@example.com'
        self._update_request_with_no_verification(api_client, mocker, simple_identity, [{
            'action': 'create',
            'field': 'email',
            'value': email,
        }])
        self._search(api_client, {'email': email})

    def test_change_alias(self, api_client, mocker, simple_identity):
        email = 'onlypeople_who_knew_this_address_already_can_find_the_entry@example.com'
        self._update_request_with_no_verification(api_client, mocker, simple_identity, [{
            'action': 'create',
            'field': 'email',
            'value': email,
        }])
        identity = self._search(api_client, {'email': email})
        simple_identity['alias'] = 'foo the bar'
        # ^- this is the mutation applied to the JSON we sent previously; v- this is the encrypted blob resulting from that.
        encrypted_json = bytes.fromhex('D2CB2DA705433593A4E18930C5999BC9254999284458150358723B8CB2C32B0B523180A878EF4E'
                                       'F8D14A8D7DB0473EEF929D27A90D647372387CAA41D8114875B5AE3A950FC1291B7D85FF6C03F4'
                                       'EDB4DBAD4636C027D696A837F501633D741590EC25BD3FEAEF9AAA570B68F69DDC5C61889265BE'
                                       '912E33E8C94FCFB119411D65B14A0D53AEDDCC87F097E0233A0FAFAEC03B587D774BF6DF37EFE2'
                                       '54A47100DA5C556C24577ABDF3D6420D0D3484BF23194BD38C8D5ED1B8071A206BC55365E26225'
                                       '7E2DEDA4C78AC247D8E56C5BE822A5A8CC4B405B711793A41983B6DFAB32E1CB37EFD57D0448DF'
                                       '5438D280B27C2924515AB8DE9287966A65DE82CB')
        response = api_client.put(self.path, encrypted_json, content_type='application/vnd.qabel.noisebox+json')
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.json()
        response = api_client.get(SearchTest.path, {'email': email})
        assert response.status_code == status.HTTP_200_OK, response.json()
        result = response.data['identities']
        assert len(result) == 1
        identity = result[0]
        assert identity['alias'] == 'foo the bar'
        # Conversely, this is invalid:
        with pytest.raises(AssertionError):
            self._update_request_with_no_verification(api_client, mocker, simple_identity, [])

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

    def _test_create_phone(self, api_client, mocker, simple_identity, phone_number, accept_language, search_number):
        kwargs = {}
        if accept_language:
            kwargs['HTTP_ACCEPT_LANGUAGE'] = accept_language
        self._update_request_with_no_verification(api_client, mocker, simple_identity, [{
            'action': 'create',
            'field': 'phone',
            'value': phone_number,
        }], **kwargs)
        self._search(api_client, {'phone': search_number})

    @pytest.fixture
    def delete_request(self, email_entry):
        return {
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
        }

    @pytest.fixture
    def delete_prerequisite(self, api_client, email_entry, delete_request):
        # Maybe use pytest-bdd here?
        # pls more fixtures
        request = json.dumps(delete_request)
        response = api_client.put(self.path, request, content_type='application/json')
        assert response.status_code == status.HTTP_202_ACCEPTED

        assert len(mail.outbox) == 1
        message = mail.outbox.pop()
        assert message.to == [email_entry.value]
        message_context = message.context
        assert message_context['identity']._asdict() == model_to_dict(email_entry.identity, exclude=['id'])

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
        # User clicks the confirm link (again, or changes language or whatever)
        response = api_client.get(confirm_url)
        assert response.status_code == status.HTTP_200_OK

    def test_delete_deny(self, api_client, delete_prerequisite, email_entry):
        deny_url = delete_prerequisite['deny_url']

        assert Entry.objects.filter(value=email_entry.value).count() == 1
        # User clicks the deny link
        response = api_client.get(deny_url)
        assert response.status_code == status.HTTP_200_OK
        # Entry should still exist
        assert Entry.objects.filter(value=email_entry.value).count() == 1
        # User clicks the deny link (again, or changes language or whatever)
        response = api_client.get(deny_url)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('invalid_request', [
        {'items': "a string?"},
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

    def test_encrypted(self, api_client, settings, simple_identity):
        encrypted_json = bytes.fromhex('61A732C1BBFA0C679BD0662F0F1F2C68CFBF5959EE95C4AD5DDEDEAD40EBD104073A0B660095ED'
                                       '6B2E59200AB6CCEC21385DB3D9A0518097797B3ABC3AAE4EA495CC5EC6B450B398999A660AE7EA'
                                       '0AEFD1DF179EC64D1A874E1E43C3F56EB4E8358F770C81E626926C81450B0BACC6C947A146AE90'
                                       'DB522E8ED53D720887488D212660F599BCAFC7FA4C79266377D04AE8464A3264D053F427711AFC'
                                       'A5696744607D6A43F9C1D6F408731AE2EA81D87BE859CEE34D88C5E54CB52488EB317FA4EE879F'
                                       'A7DCCB3F9CD9360C53D3F8199C57E091A4FF4E0037601B920DB07FA352FBDF30B813F6DBF8E065'
                                       'DB14E109F5A78E574B430C1FE17B7E2F47B454A01C281E4105B00A9FBF46256A92827301BF856E'
                                       '27E65CA1748FA87AF33B27A96B7964BF64126D48CCC6A362F5AA0006D44E058AE3B2EA9522FC68'
                                       '23AD3C01517DA91F9C99FD839AAC003302E786EC8C30')
        settings.FACET_SHALLOW_VERIFICATION = True
        response = api_client.put(self.path, encrypted_json, content_type='application/vnd.qabel.noisebox+json')
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.json()
        # Find this identity
        response = api_client.get(SearchTest.path, {'email': 'foo@example.net'})
        assert response.status_code == status.HTTP_200_OK
        result = response.data['identities']
        assert len(result) == 1
        assert result[0]['alias'] == 'public alias'
        assert result[0]['public_key'] == '8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a'

    def test_encrypted_failure(self, api_client, settings):
        encrypted_json = bytes.fromhex('cc0330af7d17d21a58f3c277897b1290405960')
        response = api_client.put(self.path, encrypted_json, content_type='application/vnd.qabel.noisebox+json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_prometheus_metrics(api_client):
    response = api_client.get('/metrics')
    assert response.status_code == 200
    assert b'django_http_requests_latency_seconds' in response.content


class AuthorizationTest:
    APIS = (
        KeyTest.path,
        SearchTest.path,
        UpdateTest.path,
    )

    @pytest.fixture(autouse=True)
    def require_authorization(self, settings):
        settings.REQUIRE_AUTHORIZATION = True

    @pytest.mark.parametrize('api', APIS)
    def test_no_header(self, api_client, api):
        response = api_client.get(api)
        assert response.status_code == 403
        assert response.json()['error'] == 'No authorization supplied.'

    @pytest.mark.parametrize('api', APIS)
    def test_with_invalid_header(self, api_client, api):
        response = api_client.get(api, HTTP_AUTHORIZATION='Token 567')
        assert response.status_code == 403
        assert response.json()['error'] == 'Accounting server unreachable.'

    @pytest.mark.parametrize('api', APIS)
    def test_valid(self, mocker, api_client, api):
        mocker.patch.object(AccountingAuthorization, 'check', lambda self, authorization: (authorization.startswith('Token'), 'All is well'))
        response = api_client.get(api, HTTP_AUTHORIZATION='Token 567')
        assert response.status_code != 403  # It'll usually be no valid request, but it should be authorized.
        assert cache.get(authorization_cache_key('Token 567'))


@pytest.fixture
def date_is_posix_ts0(monkeypatch):
    monkeypatch.setattr(timezone, 'now', lambda: datetime.datetime.fromtimestamp(0, datetime.timezone.utc))


class StatusTest:
    delete_request = UpdateTest.delete_request
    path = '/api/v0/status/'

    def test_encrypted(self, date_is_posix_ts0, api_client, email_entry, simple_identity):
        # {"api": "status", "timestamp": 0}
        encrypted_json = bytes.fromhex('A547C155C16B70947038CE99FE88B5BC9E9886008089FCA82A4C21011B819901895B5DB30482B5'
                                       'C98B3E95EFCF2BB404765D1559F7463E9F6F97001E28927B7F796E2F36B4C468D3557F3DE97CA8'
                                       '86141D2D3F0CC52D4F7F23565758516623B410E8E9820283969D2AF5B99CAF13EBDC09C2761CDD'
                                       '9DF86369A52C81D584C3314C2B25DE80')
        response = api_client.post(self.path, encrypted_json, content_type='application/vnd.qabel.noisebox+json')
        assert response.status_code == status.HTTP_200_OK, response.json()
        data = response.json()
        assert data['identity'] == {
            'alias': 'qabel_user',
            'drop_url': 'http://127.0.0.1:6000/qabel_user',
            'public_key': '8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a',
        }
        assert len(data['entries']) == 1
        entry = data['entries'].pop()
        assert entry == {
            'status': 'confirmed',
            'field': 'email',
            'value': 'foo@example.com',
        }

    def test_replay_attack(self, api_client):
        # {"api": "status", "timestamp": 0}
        encrypted_json = bytes.fromhex('A547C155C16B70947038CE99FE88B5BC9E9886008089FCA82A4C21011B819901895B5DB30482B5'
                                       'C98B3E95EFCF2BB404765D1559F7463E9F6F97001E28927B7F796E2F36B4C468D3557F3DE97CA8'
                                       '86141D2D3F0CC52D4F7F23565758516623B410E8E9820283969D2AF5B99CAF13EBDC09C2761CDD'
                                       '9DF86369A52C81D584C3314C2B25DE80')
        response = api_client.post(self.path, encrypted_json, content_type='application/vnd.qabel.noisebox+json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'timestamp' in response.json()['error']

    def test_find_identity_from_public_data(self, identity):
        id = StatusView.find_identity(identity.public_key)
        assert id == {
            'drop_url': identity.drop_url,
            'public_key': identity.public_key,
            'alias': identity.alias,
        }

    def test_find_identity_from_update_request(self, delete_request, email_entry, identity):
        pur = PendingUpdateRequest()
        pur.request = delete_request
        pur.save()
        identity.delete()
        id = StatusView.find_identity(identity.public_key)
        assert id == {
            'drop_url': identity.drop_url,
            'public_key': identity.public_key,
            'alias': identity.alias,
        }

    def test_find_identity_none(self, delete_request, email_entry, identity):
        identity.delete()
        id = StatusView.find_identity(identity.public_key)
        assert id is None


class DeleteIdentityTest:
    path = '/api/v0/delete-identity/'

    def test_encrypted(self, date_is_posix_ts0, api_client, email_entry, identity):
        # {"api": "delete-identity", "timestamp": 0}
        encrypted_json = bytes.fromhex(
            'E27C89EE1459E53A4E86BC33D01CCDF4E5043DA2DFBF4F346FDC2A5A66D0624B275C03000E140913FDFB2B6A8D13259A7CF5FEB0F'
            '438940C4E77C5F23B865BDD03CFFF218B445B6EE6C993131E471B901D488ED31724C9906014799B5FB9439F6FA38F8FFB4905B92C'
            '9D979498CB98D063A7D71A2D737EF2C06C219589636DED51E6CB19759ADEBE04D41FE75E91')
        response = api_client.post(self.path, encrypted_json, content_type='application/vnd.qabel.noisebox+json')
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.json()

        with pytest.raises(Entry.DoesNotExist):
            email_entry.refresh_from_db()
        with pytest.raises(Identity.DoesNotExist):
            identity.refresh_from_db()

    def test_replay_attack(self, api_client, identity):
        # {"api": "delete-identity", "timestamp": 0}
        encrypted_json = bytes.fromhex(
            'E27C89EE1459E53A4E86BC33D01CCDF4E5043DA2DFBF4F346FDC2A5A66D0624B275C03000E140913FDFB2B6A8D13259A7CF5FEB0F'
            '438940C4E77C5F23B865BDD03CFFF218B445B6EE6C993131E471B901D488ED31724C9906014799B5FB9439F6FA38F8FFB4905B92C'
            '9D979498CB98D063A7D71A2D737EF2C06C219589636DED51E6CB19759ADEBE04D41FE75E91')
        response = api_client.post(self.path, encrypted_json, content_type='application/vnd.qabel.noisebox+json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'timestamp' in response.json()['error']
        identity.refresh_from_db()
