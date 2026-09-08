import pytest
from src.token.safety_analyzer import TokenSafetyAnalyzer
from src.dex.pancakeswap_adapter import PancakeSwapAdapter

VALID_ADDR_SAFE = '0x2222222222222222222222222222222222222222'
VALID_ADDR_HONEY = '0x3333333333333333333333333333333333333333'
VALID_ADDR_TAX = '0x4444444444444444444444444444444444444444'
VALID_ADDR_FAIL = '0x5555555555555555555555555555555555555555'
VALID_ADDR_LOWLIQ = '0x6666666666666666666666666666666666666666'
VALID_ADDR_RESTRICT = '0x7777777777777777777777777777777777777777'

def test_normal_safe_token():
    dex = PancakeSwapAdapter()
    dex.set_mock_pool('0x1111111111111111111111111111111111111111', VALID_ADDR_SAFE, 100000.0, 100000.0)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    res = analyzer.analyze_token(VALID_ADDR_SAFE, {'liquidity': 50000.0, 'buy_tax': 1.0, 'sell_tax': 1.0})
    assert res["safe"] is True
    assert res["risk_score"] <= 20.0
    assert res["sellable"] is True

def test_honeypot_token():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token(VALID_ADDR_HONEY, {'is_honeypot': True})
    assert res["safe"] is False
    assert res["risk_score"] == 100.0
    assert res["risk_level"] == "BLOCKED"
    assert res["sellable"] is False

def test_high_tax_token():
    dex = PancakeSwapAdapter()
    dex.set_mock_pool('0x1111111111111111111111111111111111111111', VALID_ADDR_TAX, 100000.0, 100000.0)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    res = analyzer.analyze_token(VALID_ADDR_TAX, {'liquidity': 50000.0, 'buy_tax': 10.0, 'sell_tax': 15.0})
    assert res["safe"] is False
    assert res["risk_score"] > 40.0

def test_failed_sell_simulation():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token(VALID_ADDR_FAIL, {'sell_failed': True})
    assert res["safe"] is False
    assert res["sellable"] is False

def test_low_liquidity():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token(VALID_ADDR_LOWLIQ, {'liquidity': 500.0})
    assert res["safe"] is False

def test_transfer_restricted_token():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token(VALID_ADDR_RESTRICT, {'transfer_restricted': True})
    assert res["safe"] is False

def test_invalid_evm_address():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token("invalid_eth_address")
    assert res["safe"] is False
    assert res["risk_score"] == 100.0
    assert res["risk_level"] == "BLOCKED"
    assert "Invalid target token EVM address format" in res["reasons"]
