import pytest
from src.token.safety_analyzer import TokenSafetyAnalyzer
from src.dex.pancakeswap_adapter import PancakeSwapAdapter

def test_normal_safe_token():
    dex = PancakeSwapAdapter()
    safe_addr = '0x1234567890123456789012345678901234567890'
    dex.set_mock_pool('0x1111111111111111111111111111111111111111', safe_addr, 100000.0, 100000.0)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    res = analyzer.analyze_token(safe_addr, {'liquidity': 50000.0, 'buy_tax': 1.0, 'sell_tax': 1.0})
    assert res["safe"] is True
    assert res["risk_score"] <= 20.0
    assert res["sellable"] is True

def test_invalid_address_format():
    analyzer = TokenSafetyAnalyzer()
    res = analyzer.analyze_token('invalid_address_123')
    assert res["safe"] is False
    assert res["risk_score"] == 100.0
    assert res["risk_level"] == "BLOCKED"
    assert "Invalid EVM token address format" in res["reasons"][0]

def test_honeypot_token():
    analyzer = TokenSafetyAnalyzer()
    honey_addr = '0x2222222222222222222222222222222222222222'
    res = analyzer.analyze_token(honey_addr, {'is_honeypot': True})
    assert res["safe"] is False
    assert res["risk_score"] == 100.0
    assert res["risk_level"] == "BLOCKED"
    assert res["sellable"] is False

def test_high_tax_token():
    dex = PancakeSwapAdapter()
    tax_addr = '0x3333333333333333333333333333333333333333'
    dex.set_mock_pool('0x1111111111111111111111111111111111111111', tax_addr, 100000.0, 100000.0)
    analyzer = TokenSafetyAnalyzer(dex_adapter=dex)
    res = analyzer.analyze_token(tax_addr, {'liquidity': 50000.0, 'buy_tax': 10.0, 'sell_tax': 15.0})
    assert res["safe"] is False
    assert res["risk_score"] > 40.0

def test_failed_sell_simulation():
    analyzer = TokenSafetyAnalyzer()
    fail_addr = '0x4444444444444444444444444444444444444444'
    res = analyzer.analyze_token(fail_addr, {'sell_failed': True})
    assert res["safe"] is False
    assert res["sellable"] is False

def test_low_liquidity():
    analyzer = TokenSafetyAnalyzer()
    low_addr = '0x5555555555555555555555555555555555555555'
    res = analyzer.analyze_token(low_addr, {'liquidity': 500.0})
    assert res["safe"] is False

def test_transfer_restricted_token():
    analyzer = TokenSafetyAnalyzer()
    restr_addr = '0x6666666666666666666666666666666666666666'
    res = analyzer.analyze_token(restr_addr, {'transfer_restricted': True})
    assert res["safe"] is False
