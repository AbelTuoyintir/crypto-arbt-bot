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

GOOD_TOKEN = '0x8888888888888888888888888888888888888888'
BAD_TOKEN = '0x9999999999999999999999999999999999999999'
SLIP_TOKEN = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'

def test_successful_simulation():
    dex = MockTradingDEX(output_multiplier=1.05, gas_cost=0.001)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)
    res = sim.simulate_arbitrage_cycle(target_token=GOOD_TOKEN, initial_gat=100.0, token_info={'liquidity': 50000.0, 'buy_tax': 0.0, 'sell_tax': 0.0})
    assert res["valid"] is True
    assert res["profit_analysis"]["net_profit"] > 0

def test_failed_simulation_unprofitable():
    dex = MockTradingDEX(output_multiplier=0.98, gas_cost=0.001)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)
    res = sim.simulate_arbitrage_cycle(target_token=BAD_TOKEN, initial_gat=100.0, token_info={'liquidity': 50000.0})
    assert res["valid"] is False

def test_slippage_failure():
    dex = MockTradingDEX(output_multiplier=1.01, gas_cost=0.001)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)
    res = sim.simulate_arbitrage_cycle(target_token=SLIP_TOKEN, initial_gat=100.0, token_info={'liquidity': 50000.0, 'buy_tax': 1.0, 'sell_tax': 1.0})
    assert res["valid"] is False

def test_quote_reuse_and_mismatched_amount_fallback():
    class TrackingDEX(MockTradingDEX):
        def __init__(self):
            super().__init__(output_multiplier=1.05, gas_cost=0.001)
            self.calls = []

        def get_quote(self, amount_in, token_in, token_out):
            self.calls.append((amount_in, token_in, token_out))
            return amount_in * self.output_multiplier

    dex = TrackingDEX()
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)

    match_token = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
    mismatch_token = '0xcccccccccccccccccccccccccccccccccccccccc'

    # Cycle 1: initial_gat=100.0 matches test_amount_gat=100.0 -> quotes reused
    res1 = sim.simulate_arbitrage_cycle(target_token=GOOD_TOKEN, initial_gat=100.0, token_info={'liquidity': 50000.0})
    assert res1["valid"] is True
    # 2 calls made during safety_analyzer, 0 extra calls in simulator
    assert len(dex.calls) == 2

    # Reset tracking
    dex.calls.clear()

    # Cycle 2: simulate_arbitrage_cycle with initial_gat=200.0 -> quotes calculated for 200.0 and reused
    res2 = sim.simulate_arbitrage_cycle(target_token='0x2222222222222222222222222222222222222222', initial_gat=200.0, token_info={'liquidity': 50000.0})
    assert res2["valid"] is True
    # Exactly 2 calls were made during analyze_token for 200.0 GAT
    assert len(dex.calls) == 2
    assert dex.calls[0][0] == 200.0
