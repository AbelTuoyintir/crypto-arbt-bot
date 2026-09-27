from unittest.mock import MagicMock
import pytest
from src.token.token_utils import TokenUtils

def test_token_utils_invalid_address():
    utils = TokenUtils()
    res = utils.get_token_info("invalid_address")
    assert res["valid"] is False
    assert "Invalid EVM contract address" in res["error"]

def test_token_utils_caching():
    utils = TokenUtils()
    test_addr = "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"

    mock_contract = MagicMock()
    mock_contract.functions.name().call.return_value = "PancakeSwap Token"
    mock_contract.functions.symbol().call.return_value = "CAKE"
    mock_contract.functions.decimals().call.return_value = 18

    utils.w3 = MagicMock()
    utils.w3.eth.contract.return_value = mock_contract

    # First call - should query Web3 contract
    res1 = utils.get_token_info(test_addr)
    assert res1["valid"] is True
    assert res1["name"] == "PancakeSwap Token"
    assert res1["symbol"] == "CAKE"
    assert res1["decimals"] == 18
    assert mock_contract.functions.name().call.call_count == 1

    # Second call - should return cached result without calling contract functions again
    res2 = utils.get_token_info(test_addr)
    assert res2 == res1
    assert mock_contract.functions.name().call.call_count == 1
