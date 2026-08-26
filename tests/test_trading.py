import pytest
from src.dex.base_adapter import BaseDEXAdapter
from src.dex.manager import DEXManager
from src.core.trade_simulator import TradeSimulator
from src.token.safety_analyzer import TokenSafetyAnalyzer

class MockTradingDEX(BaseDEXAdapter):
    def __init__(self, output_multiplier=1.05, gas_cost=0.001):
        super().__init__('MockTradingDEX', '', '')
        self.output_multiplier = output_multiplier
        self.gas_cost = gas_cost

    def get_quote(self, amount_in, token_in, token_out):
        return amount_in * self.output_multiplier

    def estimate_output(self, amount_in, token_in, token_out, fee_bips=25):
        return self.get_quote(amount_in, token_in, token_out)

    def estimate_gas(self, token_in, token_out, amount_in):
        return self.gas_cost

    def simulate_swap(self, token_in, token_out, amount_in, min_amount_out):
        return {"success": True, "amount_out": min_amount_out, "gas_cost": self.gas_cost}

    def execute_swap(self, token_in, token_out, amount_in, min_amount_out):
        return {"success": True, "tx_hash": "0xtest_tx_hash"}

    def get_liquidity(self, token_a, token_b):
        return 100000.0

    def get_pool_price(self, token_in, token_out):
        return self.output_multiplier

def test_successful_simulation():
    dex = MockTradingDEX(output_multiplier=1.05, gas_cost=0.001)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)
    res = sim.simulate_arbitrage_cycle(target_token='0xGOOD', initial_gat=100.0, token_info={'liquidity': 50000.0, 'buy_tax': 0.0, 'sell_tax': 0.0})
    assert res["valid"] is True
    assert res["profit_analysis"]["net_profit"] > 0

def test_failed_simulation_unprofitable():
    dex = MockTradingDEX(output_multiplier=0.98, gas_cost=0.001)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)
    res = sim.simulate_arbitrage_cycle(target_token='0xBAD', initial_gat=100.0, token_info={'liquidity': 50000.0})
    assert res["valid"] is False

def test_slippage_failure():
    dex = MockTradingDEX(output_multiplier=1.01, gas_cost=0.001)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)
    res = sim.simulate_arbitrage_cycle(target_token='0xSLIP', initial_gat=100.0, token_info={'liquidity': 50000.0, 'buy_tax': 1.0, 'sell_tax': 1.0})
    assert res["valid"] is False

def test_quote_reuse_optimization(mocker=None):
    """Verify that simulate_arbitrage_cycle reuses quotes from safety analysis without duplicate get_quote calls."""
    dex = MockTradingDEX(output_multiplier=1.05, gas_cost=0.001)
    quote_calls = []
    original_get_quote = dex.get_quote

    def spy_get_quote(amount_in, token_in, token_out):
        quote_calls.append((amount_in, token_in, token_out))
        return original_get_quote(amount_in, token_in, token_out)

    dex.get_quote = spy_get_quote

    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)
    res = sim.simulate_arbitrage_cycle(
        target_token='0xGOOD',
        initial_gat=100.0,
        token_info={'liquidity': 50000.0, 'buy_tax': 0.0, 'sell_tax': 0.0}
    )

    assert res["valid"] is True
    # In safety analysis: 1 quote for GAT -> TOKEN, 1 quote for TOKEN -> GAT = 2 total quote calls.
    # Without optimization, simulate_arbitrage_cycle would call get_quote 2 additional times (4 total).
    assert len(quote_calls) == 2

def test_quote_fallback_when_amount_mismatches():
    """Verify that simulate_arbitrage_cycle falls back to fresh get_quote if initial_gat differs from test_amount_gat."""
    dex = MockTradingDEX(output_multiplier=1.05, gas_cost=0.001)
    quote_calls = []
    original_get_quote = dex.get_quote

    def spy_get_quote(amount_in, token_in, token_out):
        quote_calls.append((amount_in, token_in, token_out))
        return original_get_quote(amount_in, token_in, token_out)

    dex.get_quote = spy_get_quote

    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    # Mock analyze_token return value to simulate safety check with test_amount_gat = 50.0
    original_analyze = analyzer.analyze_token
    def mock_analyze(token_address, token_info=None, test_amount_gat=100.0):
        res = original_analyze(token_address, token_info=token_info, test_amount_gat=50.0)
        return res

    analyzer.analyze_token = mock_analyze

    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)
    res = sim.simulate_arbitrage_cycle(
        target_token='0xGOOD',
        initial_gat=100.0,
        token_info={'liquidity': 50000.0, 'buy_tax': 0.0, 'sell_tax': 0.0}
    )

    assert res["valid"] is True
    # 2 calls in analyze_token (with 50.0) + 2 fresh calls in simulate_arbitrage_cycle (with 100.0) = 4 total calls
    assert len(quote_calls) == 4
