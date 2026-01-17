from starlette.testclient import TestClient
from main import app

def test_get_home():
    client = TestClient(app)
    res = client.get('/')
    assert res.status_code == 200
    assert 'Hello World' in res.text
    assert 'FastHTML Template' in res.text