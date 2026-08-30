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
    assert response.headers.get('Content-Security-Policy') == "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self';"
    assert response.headers.get('X-Permitted-Cross-Domain-Policies') == 'none'
    assert response.headers.get('Cross-Origin-Opener-Policy') == 'same-origin'

def test_api_metrics_security_headers(client):
    response = client.get('/api/metrics')
    assert response.status_code == 200
    assert response.headers.get('X-Frame-Options') == 'DENY'
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-XSS-Protection') == '1; mode=block'
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert response.headers.get('Content-Security-Policy') == "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self';"
    assert response.headers.get('X-Permitted-Cross-Domain-Policies') == 'none'
    assert response.headers.get('Cross-Origin-Opener-Policy') == 'same-origin'
