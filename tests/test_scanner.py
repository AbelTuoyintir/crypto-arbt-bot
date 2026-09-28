import pytest
from src.dex.manager import DEXManager
from src.scanner.market_scanner import MarketScanner
from src.core.engine import ArbitrageEngine
from tests.test_trading import MockTradingDEX

class TrackingScannerDEX(MockTradingDEX):
    def __init__(self, output_multiplier=1.05, gas_cost=0.001):
        super().__init__(output_multiplier=output_multiplier, gas_cost=gas_cost)
        self.quote_calls = 0
        self.gas_calls = 0

    def get_quote(self, amount_in, token_in, token_out):
        self.quote_calls += 1
        return super().get_quote(amount_in, token_in, token_out)

    def estimate_gas(self, token_in, token_out, amount_in):
        self.gas_calls += 1
        return super().estimate_gas(token_in, token_out, amount_in)

SAFE_TOKEN = '0x8888888888888888888888888888888888888888'

def test_market_scanner_no_duplicate_quotes():
    dex = TrackingScannerDEX(output_multiplier=1.05, gas_cost=0.001)
    dex_manager = DEXManager()
    dex_manager.register_adapter("MockDEX", dex)

    engine = ArbitrageEngine(dex_manager=dex_manager)
    scanner = MarketScanner(dex_manager=dex_manager, engine=engine)

    target_tokens = [
        {"address": SAFE_TOKEN, "symbol": "TEST", "liquidity": 50000.0, "buy_tax": 0.0, "sell_tax": 0.0}
    ]

    results = scanner.scan_market(target_tokens=target_tokens, initial_gat=100.0)

    assert len(results) == 1
    assert results[0]["token"] == "TEST"
    assert results[0]["dex"] == "MockDEX"

    # Single-pass scan per token should only make 2 DEX quote calls (Leg 1 & Leg 2)
    # and 2 gas estimation calls during the engine simulation, not 4 quote calls & 3 gas calls.
    assert dex.quote_calls == 2
    assert dex.gas_calls == 2
