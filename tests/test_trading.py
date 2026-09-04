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
        self.get_quote_calls = 0

    def get_quote(self, amount_in, token_in, token_out):
        self.get_quote_calls += 1
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

def test_quote_call_reduction_and_fallback():
    dex = MockTradingDEX(output_multiplier=1.05, gas_cost=0.001)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    sim = TradeSimulator(dex_adapter=dex, safety_analyzer=analyzer)

    # 1. Verify get_quote is called exactly 2 times (during safety analysis only, reused in simulation)
    res = sim.simulate_arbitrage_cycle(target_token='0xOPTIMIZED', initial_gat=100.0, token_info={'liquidity': 50000.0, 'buy_tax': 0.0, 'sell_tax': 0.0})
    assert res["valid"] is True
    assert dex.get_quote_calls == 2

    # 2. Verify fallback works when safety_res does not have matching quotes (e.g., test_amount_gat mismatch)
    dex.get_quote_calls = 0
    class MockSafetyAnalyzer(TokenSafetyAnalyzer):
        def analyze_token(self, token_address, token_info=None, test_amount_gat=100.0):
            res = super().analyze_token(token_address, token_info, test_amount_gat)
            res["test_amount_gat"] = 999.0  # Force mismatch
            return res

    sim_mismatch = TradeSimulator(dex_adapter=dex, safety_analyzer=MockSafetyAnalyzer(dex_adapter=dex))
    res_fallback = sim_mismatch.simulate_arbitrage_cycle(target_token='0xFALLBACK', initial_gat=100.0, token_info={'liquidity': 50000.0, 'buy_tax': 0.0, 'sell_tax': 0.0})
    assert res_fallback["valid"] is True
    # 2 calls in analyze_token + 2 fallback calls in simulate_arbitrage_cycle = 4 calls total
    assert dex.get_quote_calls == 4
