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

def test_api_metrics_error_handling(client, monkeypatch):
    from unittest.mock import MagicMock
    mock_session = MagicMock()
    mock_session.query.side_effect = Exception("Database connection error")
    monkeypatch.setattr('src.dashboard.app.SessionLocal', lambda: mock_session)

    response = client.get('/api/metrics')
    assert response.status_code == 500
    data = response.get_json()
    assert data == {"error": "An internal error occurred"}
    assert "Database connection error" not in response.get_data(as_text=True)

def test_api_metrics_security_headers(client):
    response = client.get('/api/metrics')
    assert response.status_code == 200
    assert response.headers.get('X-Frame-Options') == 'DENY'
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-XSS-Protection') == '1; mode=block'
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert response.headers.get('Content-Security-Policy') == "default-src 'self' 'unsafe-inline';"
