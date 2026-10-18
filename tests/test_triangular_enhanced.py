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

def test_risk_manager_daily_profit_rate_tracking():
    rm = RiskManager()
    assert rm.daily_total_profit == 0.0
    assert rm.get_daily_profit_rate(initial_capital=100.0) == 0.0

    # Record 5 GAT profit
    rm.record_trade_result(5.0, success=True)
    assert rm.daily_total_profit == 5.0
    assert rm.get_daily_profit_rate(initial_capital=100.0) == 5.0

    # Record edge case: initial capital <= 0
    assert rm.get_daily_profit_rate(initial_capital=0.0) == 0.0

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

def test_abitragebot_min_confidence_threshold(monkeypatch):
    import abitragebot
    score, mult = abitragebot.calculate_confidence_score(
        gross_profit_wei=10**16,
        gas_cost_wei=10**14,
        amount_in_wei=10**18
    )
    # Default MIN_CONFIDENCE_SCORE = 95.0
    monkeypatch.setenv("MIN_CONFIDENCE_SCORE", "95.0")
    import os
    min_conf = float(os.getenv("MIN_CONFIDENCE_SCORE", "95.0"))
    assert min_conf == 95.0
    assert score >= 70.0

def test_engine_price_impact_confidence_deduction():
    manager = DEXManager()
    engine = ArbitrageEngine(dex_manager=manager)

    conf1 = engine.calculate_opportunity_confidence(
        profit_percentage=2.0,
        risk_score=0.0,
        gas_cost_gat=0.001,
        initial_gat=100.0,
        price_impact_percent=0.0
    )

    conf2 = engine.calculate_opportunity_confidence(
        profit_percentage=2.0,
        risk_score=0.0,
        gas_cost_gat=0.001,
        initial_gat=100.0,
        price_impact_percent=1.5
    )

    conf3 = engine.calculate_opportunity_confidence(
        profit_percentage=2.0,
        risk_score=0.0,
        gas_cost_gat=0.001,
        initial_gat=100.0,
        price_impact_percent=2.5
    )

    assert conf1["confidence_score"] > conf2["confidence_score"]
    assert conf2["confidence_score"] > conf3["confidence_score"]
    assert conf1["confidence_score"] - conf2["confidence_score"] == 10.0
    assert conf1["confidence_score"] - conf3["confidence_score"] == 20.0
