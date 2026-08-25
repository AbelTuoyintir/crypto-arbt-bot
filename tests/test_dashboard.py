import pytest
from src.dashboard.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_dashboard_security_headers(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.headers.get('X-Frame-Options') == 'DENY'
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-XSS-Protection') == '1; mode=block'
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert response.headers.get('Content-Security-Policy') == "default-src 'self' 'unsafe-inline';"

def test_unhandled_exception_handling(client, monkeypatch):
    def mock_db_raise():
        raise RuntimeError("Secret internal database connection failure details")

    monkeypatch.setattr('src.dashboard.app.SessionLocal', mock_db_raise)

    response = client.get('/api/metrics')
    assert response.status_code == 500
    json_data = response.get_json()
    assert json_data == {"error": "An internal server error occurred"}
    assert b"Secret internal database connection failure details" not in response.data

def test_api_metrics_security_headers(client):
    response = client.get('/api/metrics')
    assert response.status_code == 200
    assert response.headers.get('X-Frame-Options') == 'DENY'
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-XSS-Protection') == '1; mode=block'
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert response.headers.get('Content-Security-Policy') == "default-src 'self' 'unsafe-inline';"
