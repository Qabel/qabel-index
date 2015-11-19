import json

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