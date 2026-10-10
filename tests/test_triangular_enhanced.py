import pytest
from config.settings import settings
from src.core.risk_manager import RiskManager
from src.core.engine import ArbitrageEngine
from src.dex.manager import DEXManager
from tests.test_triangular import MockTriangularDEX, TOKEN_B, TOKEN_C
from src.dashboard.app import app

def test_risk_manager_win_rate_tracking():
    rm = RiskManager()
    assert rm.get_daily_win_rate() == 100.0

    # Record 1 success, 0 losses
    rm.record_trade_result(10.0, success=True)
    assert rm.get_daily_win_rate() == 100.0

    # Record 1 failure
    rm.record_trade_result(0.0, success=False)
    assert rm.get_daily_win_rate() == 50.0

def test_risk_manager_confidence_filtering():
    rm = RiskManager()
    # When confidence is high (96.0 >= 95.0 required), should approve
    res_high = rm.validate_trade(
        trade_amount_gat=50.0,
        gas_cost_gat=0.001,
        profit_percent=2.0,
        token_risk_score=10.0,
        confidence_score=96.0
    )
    assert res_high["approved"] is True

    # When confidence is low (60.0 < 95.0 required), should reject
    res_low = rm.validate_trade(
        trade_amount_gat=50.0,
        gas_cost_gat=0.001,
        profit_percent=2.0,
        token_risk_score=10.0,
        confidence_score=60.0
    )
    assert res_low["approved"] is False
    assert "Confidence score below target" in res_low["reason"]

def test_engine_triangular_confidence_rejection():
    manager = DEXManager()
    # Multiplier=1.05 gives profitable simulation, but gas_cost=1.0 (3.0 GAT gas total) drops confidence score to 75%
    dex = MockTriangularDEX(multiplier=1.05, gas_cost=1.0)
    manager.register_adapter('MockTriangularDEX', dex)
    engine = ArbitrageEngine(dex_manager=manager)

    res = engine.process_triangular_opportunity(
        dex_name='MockTriangularDEX',
        token_a=TOKEN_B,
        token_b=TOKEN_C,
        initial_gat=100.0,
        token_a_info={'liquidity': 50000.0},
        token_b_info={'liquidity': 50000.0}
    )

    # Should be rejected by RiskManager because confidence score (75%) is below 95% threshold
    assert res["executed"] is False
    assert "Confidence score below target" in res["reason"] or "Risk check failed" in res["reason"]

def test_api_triangular_endpoint():
    client = app.test_client()
    response = client.get("/api/triangular")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "online"
    assert "target_win_rate_percent" in data
    assert data["target_win_rate_percent"] == 95.0
    assert "daily_win_rate" in data
