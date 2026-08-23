import pytest
from src.token.safety_analyzer import TokenSafetyAnalyzer
from src.dex.pancakeswap_adapter import PancakeSwapAdapter

def test_normal_safe_token():
    dex = PancakeSwapAdapter()
    dex.set_mock_pool('0x1111111111111111111111111111111111111111', '0xSAFE', 100000.0, 100000.0)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    res = analyzer.analyze_token('0xSAFE', {'liquidity': 50000.0, 'buy_tax': 1.0, 'sell_tax': 1.0})
    assert res["safe"] is True
    assert res["risk_score"] <= 20.0
    assert res["sellable"] is True

def test_honeypot_token():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token('0xHONEY', {'is_honeypot': True})
    assert res["safe"] is False
    assert res["risk_score"] == 100.0
    assert res["risk_level"] == "BLOCKED"
    assert res["sellable"] is False

def test_high_tax_token():
    dex = PancakeSwapAdapter()
    dex.set_mock_pool('0x1111111111111111111111111111111111111111', '0xTAX', 100000.0, 100000.0)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    res = analyzer.analyze_token('0xTAX', {'liquidity': 50000.0, 'buy_tax': 10.0, 'sell_tax': 15.0})
    assert res["safe"] is False
    assert res["risk_score"] > 40.0

def test_failed_sell_simulation():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token('0xFAILSELL', {'sell_failed': True})
    assert res["safe"] is False
    assert res["sellable"] is False

def test_low_liquidity():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token('0xLOWLIQ', {'liquidity': 500.0})
    assert res["safe"] is False

def test_transfer_restricted_token():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token('0xRESTRICTED', {'transfer_restricted': True})
    assert res["safe"] is False
