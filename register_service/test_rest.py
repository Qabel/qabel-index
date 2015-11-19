import json

from register_service.models import Identity


def loads(response):
    return json.loads(response.decode('utf-8'))

def test_get_identity(api_client, identity):
    response = api_client.post('/api/v0/search/', {'alias': 'qabel', 'drop_url': '6000'})
    assert response.status_code == 200
    result = loads(response.content)
    assert len(result) == 1
    assert result[0]['alias'] == "qabel_user"
    assert result[0]['drop_url'] == "http://127.0.0.1:6000/qabel_user"

def test_get_no_identity(api_client, identity):
    response = api_client.post('/api/v0/search/', {'alias': 'no_user'})
    assert response.status_code == 204


def test_create_invalid_identity(api_client, identity):
    response = api_client.post('/api/v0/identity/', {})
    assert response.status_code == 400
    assert Identity.objects.all().count() == 1


def test_create_new_identity(api_client, identity):
    response = api_client.post('/api/v0/identity/',
                               {'alias': 'best_user', 'drop_url': 'http://127.0.0.1:6000/best_user'})
    assert response.status_code == 201
    assert Identity.objects.all().count() == 2


def test_create_duplicate(api_client, identity):
    response = api_client.post('/api/v0/identity/',
                               {'alias': 'qabel_user', 'drop_url': 'http://127.0.0.1:6000/qabel_user'})
    assert response.status_code == 201
    assert Identity.objects.all().count() == 2


def test_update_identity(api_client, identity):
    response = api_client.post('/api/v0/update/',
                              {'alias_to_change': 'qabel_user', 'alias': 'foobar',
                               'drop_url': 'http://127.0.0.1:6000/qabel_user',
                               'email': 'qabel_user@example.com'})
    assert response.status_code == 200
    assert Identity.objects.all().count() == 1
    result = loads(response.content)
    identity = Identity.objects.get(alias='foobar')
    assert result['alias'] == "foobar" == identity.alias
    assert result['email'] == "qabel_user@example.com" == identity.email
