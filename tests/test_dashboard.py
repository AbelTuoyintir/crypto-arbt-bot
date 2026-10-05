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
    assert response.headers.get('Content-Security-Policy') == "default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline';"

def test_api_metrics_data(client):
    from src.db.models import SessionLocal, Opportunity, Trade
    db = SessionLocal()
    created_trades = []
    created_opp = None
    try:
        # Insert test opportunity and trades
        created_opp = Opportunity(
            base_token="0xbase", target_token="0xtarget", dex="TestDEX",
            initial_gat=100.0, expected_token=50.0, expected_final_gat=110.0,
            estimated_profit=10.0, status="executed"
        )
        db.add(created_opp)
        db.commit()

        t1 = Trade(opportunity_id=created_opp.id, initial_gat=100.0, final_gat=108.0, actual_profit=8.0, status="success")
        t2 = Trade(opportunity_id=created_opp.id, initial_gat=100.0, final_gat=104.0, actual_profit=4.0, status="success")
        t3 = Trade(opportunity_id=created_opp.id, initial_gat=100.0, final_gat=100.0, actual_profit=0.0, status="failed")
        created_trades = [t1, t2, t3]
        db.add_all(created_trades)
        db.commit()

        response = client.get('/api/metrics')
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "online"
        assert data["total_opportunities"] >= 1
        assert data["total_trades"] >= 3
        # total_profit should correctly aggregate success trades (8.0 + 4.0 = 12.0)
        assert data["total_profit"] >= 12.0
    finally:
        for t in created_trades:
            db.delete(t)
        if created_opp:
            db.delete(created_opp)
        db.commit()
        db.close()

def test_api_metrics_security_headers(client):
    response = client.get('/api/metrics')
    assert response.status_code == 200
    assert response.headers.get('X-Frame-Options') == 'DENY'
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-XSS-Protection') == '1; mode=block'
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert response.headers.get('Content-Security-Policy') == "default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline';"
