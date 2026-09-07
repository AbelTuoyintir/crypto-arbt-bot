import pytest
from src.token.safety_analyzer import TokenSafetyAnalyzer
from src.dex.pancakeswap_adapter import PancakeSwapAdapter

SAFE_TOKEN = '0x0000000000000000000000000000000000000001'
HONEY_TOKEN = '0x0000000000000000000000000000000000000002'
TAX_TOKEN = '0x0000000000000000000000000000000000000003'
FAILSELL_TOKEN = '0x0000000000000000000000000000000000000004'
LOWLIQ_TOKEN = '0x0000000000000000000000000000000000000005'
RESTRICTED_TOKEN = '0x0000000000000000000000000000000000000006'

def test_invalid_address_format():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token('0xINVALID')
    assert res["safe"] is False
    assert res["risk_score"] == 100.0
    assert res["risk_level"] == "BLOCKED"
    assert "Invalid target token address" in res["reasons"][0]

def test_normal_safe_token():
    dex = PancakeSwapAdapter()
    dex.set_mock_pool('0x1111111111111111111111111111111111111111', SAFE_TOKEN, 100000.0, 100000.0)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    res = analyzer.analyze_token(SAFE_TOKEN, {'liquidity': 50000.0, 'buy_tax': 1.0, 'sell_tax': 1.0})
    assert res["safe"] is True
    assert res["risk_score"] <= 20.0
    assert res["sellable"] is True

def test_honeypot_token():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token(HONEY_TOKEN, {'is_honeypot': True})
    assert res["safe"] is False
    assert res["risk_score"] == 100.0
    assert res["risk_level"] == "BLOCKED"
    assert res["sellable"] is False

def test_high_tax_token():
    dex = PancakeSwapAdapter()
    dex.set_mock_pool('0x1111111111111111111111111111111111111111', TAX_TOKEN, 100000.0, 100000.0)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    res = analyzer.analyze_token(TAX_TOKEN, {'liquidity': 50000.0, 'buy_tax': 10.0, 'sell_tax': 15.0})
    assert res["safe"] is False
    assert res["risk_score"] > 40.0

def test_failed_sell_simulation():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token(FAILSELL_TOKEN, {'sell_failed': True})
    assert res["safe"] is False
    assert res["sellable"] is False

def test_low_liquidity():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token(LOWLIQ_TOKEN, {'liquidity': 500.0})
    assert res["safe"] is False

def test_transfer_restricted_token():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token(RESTRICTED_TOKEN, {'transfer_restricted': True})
    assert res["safe"] is False
