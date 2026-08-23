import pytest
from src.core.profit_calculator import ProfitCalculator

def test_profitable_trade():
    calc = ProfitCalculator(min_profit_percent=1.0)
    res = calc.calculate_round_trip(
        initial_gat=100.0,
        token_received_gross=100.0,
        final_gat_gross=105.0,
        buy_tax_percent=0.0,
        sell_tax_percent=0.0,
        slippage_percent=0.5,
        gas_cost_gat=0.5
    )
    assert res["profitable"] is True
    assert res["net_profit"] > 0
    assert res["profit_percentage"] >= 1.0

def test_unprofitable_trade():
    calc = ProfitCalculator(min_profit_percent=1.0)
    res = calc.calculate_round_trip(
        initial_gat=100.0,
        token_received_gross=100.0,
        final_gat_gross=100.5,
        buy_tax_percent=0.0,
        sell_tax_percent=0.0,
        slippage_percent=0.5,
        gas_cost_gat=0.5
    )
    assert res["profitable"] is False

def test_fees_greater_than_profit():
    calc = ProfitCalculator(min_profit_percent=1.0)
    res = calc.calculate_round_trip(
        initial_gat=100.0,
        token_received_gross=100.0,
        final_gat_gross=102.0,
        buy_tax_percent=2.0,
        sell_tax_percent=2.0,
        slippage_percent=0.5,
        gas_cost_gat=0.5
    )
    assert res["profitable"] is False
    assert res["net_profit"] < 0

def test_gas_greater_than_profit():
    calc = ProfitCalculator(min_profit_percent=1.0)
    res = calc.calculate_round_trip(
        initial_gat=100.0,
        token_received_gross=100.0,
        final_gat_gross=103.0,
        buy_tax_percent=0.0,
        sell_tax_percent=0.0,
        slippage_percent=0.5,
        gas_cost_gat=5.0
    )
    assert res["profitable"] is False
