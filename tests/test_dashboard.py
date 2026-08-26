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

def test_dashboard_renders_safely_with_special_tokens(client):
    from src.db.models import SessionLocal, Opportunity
    db = SessionLocal()
    opp = Opportunity(
        base_token="0x1111111111111111111111111111111111111111",
        target_token="<script>alert('xss')</script>",
        dex="PancakeSwap",
        initial_gat=100.0,
        expected_token=100.0,
        expected_final_gat=105.0,
        estimated_profit=5.0,
        profit_percentage=5.0,
        risk_score=10.0,
        status="executed"
    )
    db.add(opp)
    try:
        db.commit()

        response = client.get('/')
        assert response.status_code == 200
        # Jinja2 autoescaping must escape HTML tags into entities
        assert "<script>" not in response.get_data(as_text=True)
        assert "&lt;script&gt;" in response.get_data(as_text=True)
    finally:
        try:
            db.delete(opp)
            db.commit()
        except Exception:
            db.rollback()
        db.close()

def test_api_metrics_security_headers(client):
    response = client.get('/api/metrics')
    assert response.status_code == 200
    assert response.headers.get('X-Frame-Options') == 'DENY'
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-XSS-Protection') == '1; mode=block'
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert response.headers.get('Content-Security-Policy') == "default-src 'self' 'unsafe-inline';"
