import pytest
from src.core.risk_manager import RiskManager
from config.settings import settings

def test_risk_controls_valid_trade():
    rm = RiskManager()
    res = rm.validate_trade(
        trade_amount_gat=50.0,
        gas_cost_gat=0.001,
        profit_percent=2.0,
        token_risk_score=10.0
    )
    assert res["approved"] is True

def test_non_positive_trade_amount():
    rm = RiskManager()
    res_zero = rm.validate_trade(
        trade_amount_gat=0.0,
        gas_cost_gat=0.001,
        profit_percent=2.0,
        token_risk_score=10.0
    )
    assert res_zero["approved"] is False
    assert "Invalid trade amount" in res_zero["reason"]

    res_negative = rm.validate_trade(
        trade_amount_gat=-10.0,
        gas_cost_gat=0.001,
        profit_percent=2.0,
        token_risk_score=10.0
    )
    assert res_negative["approved"] is False
    assert "Invalid trade amount" in res_negative["reason"]

def test_max_trade_exceeded():
    rm = RiskManager()
    res = rm.validate_trade(
        trade_amount_gat=settings.MAX_TRADE_SIZE + 10.0,
        gas_cost_gat=0.001,
        profit_percent=2.0,
        token_risk_score=10.0
    )
    assert res["approved"] is False
    assert "Trade size exceeds max limit" in res["reason"]

def test_daily_loss_exceeded():
    rm = RiskManager()
    rm.record_trade_result(- (settings.MAX_DAILY_LOSS + 5.0))
    res = rm.validate_trade(
        trade_amount_gat=10.0,
        gas_cost_gat=0.001,
        profit_percent=2.0,
        token_risk_score=10.0
    )
    assert res["approved"] is False
    assert rm.kill_switch_active is True

def test_max_gas_exceeded():
    rm = RiskManager()
    res = rm.validate_trade(
        trade_amount_gat=10.0,
        gas_cost_gat=settings.MAX_GAS_COST + 0.1,
        profit_percent=2.0,
        token_risk_score=10.0
    )
    assert res["approved"] is False
    assert "Gas cost exceeds max allowed" in res["reason"]

def test_minimum_profit_not_reached():
    rm = RiskManager()
    res = rm.validate_trade(
        trade_amount_gat=10.0,
        gas_cost_gat=0.001,
        profit_percent=settings.MIN_PROFIT_PERCENT - 0.5,
        token_risk_score=10.0
    )
    assert res["approved"] is False
    assert "Profit percentage below min threshold" in res["reason"]

def test_kill_switch():
    rm = RiskManager()
    rm.trigger_kill_switch("Manual test trigger")
    res = rm.validate_trade(
        trade_amount_gat=10.0,
        gas_cost_gat=0.001,
        profit_percent=5.0,
        token_risk_score=10.0
    )
    assert res["approved"] is False
    assert "Kill Switch is ACTIVE" in res["reason"]
