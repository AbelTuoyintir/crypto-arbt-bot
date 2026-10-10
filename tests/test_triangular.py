import pytest
from src.core.profit_calculator import ProfitCalculator
from src.core.trade_simulator import TradeSimulator
from src.token.safety_analyzer import TokenSafetyAnalyzer
from src.core.engine import ArbitrageEngine
from src.scanner.market_scanner import MarketScanner
from src.dex.manager import DEXManager
from src.dex.base_adapter import BaseDEXAdapter
import abitragebot

class MockTriangularDEX(BaseDEXAdapter):
    def __init__(self, multiplier=1.05, gas_cost=0.001, fail_leg=None):
        super().__init__('MockTriangularDEX', '', '')
        self.multiplier = multiplier
        self.gas_cost = gas_cost
        self.fail_leg = fail_leg

    def get_quote(self, amount_in, token_in, token_out):
        if self.fail_leg == "leg1" and token_in == TOKEN_A:
            return 0.0
        if self.fail_leg == "leg2" and token_in == TOKEN_B and token_out == TOKEN_C:
            return 0.0
        if self.fail_leg == "leg3" and token_in == TOKEN_C:
            return 0.0
        return amount_in * self.multiplier

    def estimate_output(self, amount_in, token_in, token_out, fee_bips=25):
        return self.get_quote(amount_in, token_in, token_out)

    def estimate_gas(self, token_in, token_out, amount_in):
        return self.gas_cost

    def simulate_swap(self, token_in, token_out, amount_in, min_amount_out):
        return {"success": True, "amount_out": min_amount_out, "gas_cost": self.gas_cost}

    def execute_swap(self, token_in, token_out, amount_in, min_amount_out):
        return {"success": True, "tx_hash": "0xtriangular_test_hash"}

    def get_liquidity(self, token_a, token_b):
        return 100000.0

    def get_pool_price(self, token_in, token_out):
        return self.multiplier

TOKEN_A = '0x1111111111111111111111111111111111111111'
TOKEN_B = '0x2222222222222222222222222222222222222222'
TOKEN_C = '0x3333333333333333333333333333333333333333'

def test_triangular_profit_calculator_profitable():
    calc = ProfitCalculator(min_profit_percent=1.0)
    res = calc.calculate_triangular_round_trip(
        initial_gat=100.0,
        token_a_gross=100.0,
        token_b_gross=100.0,
        final_gat_gross=108.0,
        token_a_buy_tax=0.0,
        token_a_sell_tax=0.0,
        token_b_buy_tax=0.0,
        token_b_sell_tax=0.0,
        slippage_percent=0.5,
        gas_cost_gat=0.5
    )
    assert res["profitable"] is True
    assert res["net_profit"] > 0
    assert res["profit_percentage"] >= 1.0

def test_triangular_profit_calculator_unprofitable():
    calc = ProfitCalculator(min_profit_percent=1.0)
    res = calc.calculate_triangular_round_trip(
        initial_gat=100.0,
        token_a_gross=100.0,
        token_b_gross=100.0,
        final_gat_gross=101.0,
        token_a_buy_tax=2.0,
        token_a_sell_tax=2.0,
        token_b_buy_tax=2.0,
        token_b_sell_tax=2.0,
        slippage_percent=0.5,
        gas_cost_gat=1.0
    )
    assert res["profitable"] is False
    assert res["net_profit"] < 0

def test_triangular_simulator_success():
    dex = MockTriangularDEX(multiplier=1.03, gas_cost=0.001)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)
    res = sim.simulate_triangular_arbitrage_cycle(
        token_a=TOKEN_B,
        token_b=TOKEN_C,
        initial_gat=100.0,
        token_a_info={'liquidity': 50000.0, 'buy_tax': 0.0, 'sell_tax': 0.0},
        token_b_info={'liquidity': 50000.0, 'buy_tax': 0.0, 'sell_tax': 0.0}
    )
    assert res["valid"] is True
    assert res["profit_analysis"]["net_profit"] > 0

def test_triangular_simulator_rejected_safety():
    dex = MockTriangularDEX(multiplier=1.03, gas_cost=0.001)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)
    res = sim.simulate_triangular_arbitrage_cycle(
        token_a=TOKEN_B,
        token_b=TOKEN_C,
        initial_gat=100.0,
        token_a_info={'is_honeypot': True},
        token_b_info={'liquidity': 50000.0}
    )
    assert res["valid"] is False
    assert "Token A safety check failed" in res["rejection_reason"]

def test_triangular_simulator_leg_failure():
    dex = MockTriangularDEX(multiplier=1.03, gas_cost=0.001, fail_leg="leg2")
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)
    res = sim.simulate_triangular_arbitrage_cycle(
        token_a=TOKEN_B,
        token_b=TOKEN_C,
        initial_gat=100.0,
        token_a_info={'liquidity': 50000.0},
        token_b_info={'liquidity': 50000.0}
    )
    assert res["valid"] is False
    assert "Leg 2" in res["rejection_reason"]

def test_triangular_engine_processing():
    manager = DEXManager()
    dex = MockTriangularDEX(multiplier=1.03, gas_cost=0.001)
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

    assert res["executed"] is True
    assert res["profit"] > 0
    assert "confidence_analysis" in res
    assert res["confidence_analysis"]["confidence_score"] > 0

def test_triangular_engine_missing_dex():
    manager = DEXManager()
    engine = ArbitrageEngine(dex_manager=manager)
    res = engine.process_triangular_opportunity(
        dex_name='NonExistentDEX',
        token_a=TOKEN_B,
        token_b=TOKEN_C,
        initial_gat=100.0
    )
    assert res["executed"] is False
    assert "not found" in res["reason"]

def test_calculate_opportunity_confidence():
    manager = DEXManager()
    engine = ArbitrageEngine(dex_manager=manager)

    high_conf = engine.calculate_opportunity_confidence(
        profit_percentage=5.0,
        risk_score=10.0,
        gas_cost_gat=0.1,
        initial_gat=100.0
    )
    assert high_conf["confidence_score"] >= 80.0
    assert high_conf["high_confidence"] is True

    low_conf = engine.calculate_opportunity_confidence(
        profit_percentage=1.1,
        risk_score=50.0,
        gas_cost_gat=3.0,
        initial_gat=100.0
    )
    assert low_conf["confidence_score"] < 70.0
    assert low_conf["high_confidence"] is False

def test_standalone_bot_confidence_score():
    score, multiplier = abitragebot.calculate_confidence_score(
        gross_profit_wei=10**16,  # 0.01 ether
        gas_cost_wei=10**14,      # 0.0001 ether
        amount_in_wei=10**18      # 1 ether
    )
    assert score > 50.0
    assert multiplier > 0.0

    score_unprofitable, mult_unprofitable = abitragebot.calculate_confidence_score(
        gross_profit_wei=10**14,
        gas_cost_wei=10**15,
        amount_in_wei=10**18
    )
    assert score_unprofitable == 0.0
    assert mult_unprofitable == 0.0

def test_triangular_market_scanner():
    manager = DEXManager()
    dex = MockTriangularDEX(multiplier=1.03, gas_cost=0.001)
    manager.register_adapter('MockTriangularDEX', dex)
    scanner = MarketScanner(dex_manager=manager)

    pairs = [
        {
            "token_a": {"address": TOKEN_B, "symbol": "TOKB", "liquidity": 50000.0},
            "token_b": {"address": TOKEN_C, "symbol": "TOKC", "liquidity": 50000.0}
        }
    ]

    results = scanner.scan_triangular_market(token_pairs=pairs, initial_gat=100.0)
    assert len(results) == 1
    assert results[0]["pair"] == "TOKB->TOKC"
    assert results[0]["profit"] > 0

def test_triangular_engine_confidence_filtering():
    manager = DEXManager()
    dex = MockTriangularDEX(multiplier=1.03, gas_cost=0.001)
    manager.register_adapter('MockTriangularDEX', dex)
    engine = ArbitrageEngine(dex_manager=manager)

    # Calling with min_confidence requirement = 101.0, which exceeds max possible confidence (100.0)
    res = engine.process_triangular_opportunity(
        dex_name='MockTriangularDEX',
        token_a=TOKEN_B,
        token_b=TOKEN_C,
        initial_gat=100.0,
        token_a_info={'liquidity': 50000.0},
        token_b_info={'liquidity': 50000.0},
        min_confidence=101.0
    )

    assert res["executed"] is False
    assert "Confidence score" in res["reason"]
