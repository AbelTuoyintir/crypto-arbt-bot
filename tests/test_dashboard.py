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

def test_dashboard_and_api_metrics_aggregations(client):
    from src.db.models import init_db, SessionLocal, Opportunity, Trade
    init_db()
    db = SessionLocal()
    try:
        # Clear existing records for deterministic metrics testing
        db.query(Trade).delete()
        db.query(Opportunity).delete()
        db.commit()

        # Add mock opportunities
        opp1 = Opportunity(
            base_token="0xBASE",
            target_token="0xTARGET1",
            dex="PancakeSwapV2",
            initial_gat=100.0,
            expected_token=1000.0,
            expected_final_gat=105.0,
            estimated_profit=5.0,
            profit_percentage=5.0,
            status="executed"
        )
        opp2 = Opportunity(
            base_token="0xBASE",
            target_token="0xTARGET2",
            dex="PancakeSwapV2",
            initial_gat=100.0,
            expected_token=0.0,
            expected_final_gat=0.0,
            estimated_profit=-1.0,
            profit_percentage=-1.0,
            status="rejected"
        )
        db.add_all([opp1, opp2])
        db.commit()

        # Add mock trades
        trade1 = Trade(
            opportunity_id=opp1.id,
            entry_transaction_hash="0x1",
            exit_transaction_hash="0x2",
            initial_gat=100.0,
            final_gat=105.0,
            actual_profit=5.0,
            status="success"
        )
        trade2 = Trade(
            opportunity_id=opp2.id,
            entry_transaction_hash="0x3",
            exit_transaction_hash="0x4",
            initial_gat=100.0,
            final_gat=100.0,
            actual_profit=0.0,
            status="failed"
        )
        db.add_all([trade1, trade2])
        db.commit()

        # Verify API metrics output accurately reflects aggregated SQL values
        response = client.get('/api/metrics')
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_opportunities"] == 2
        assert data["total_trades"] == 2
        assert data["total_profit"] == 5.0

        # Verify Dashboard page renders successfully with aggregated values
        dash_resp = client.get('/')
        assert dash_resp.status_code == 200
        assert b"Opportunities Found:" in dash_resp.data
        assert b"5.0000" in dash_resp.data
    finally:
        db.close()

def test_api_metrics_security_headers(client):
    response = client.get('/api/metrics')
    assert response.status_code == 200
    assert response.headers.get('X-Frame-Options') == 'DENY'
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-XSS-Protection') == '1; mode=block'
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert response.headers.get('Content-Security-Policy') == "default-src 'self' 'unsafe-inline';"
