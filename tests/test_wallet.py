import pytest
from src.wallet.wallet_manager import WalletManager

# Standard test account private key (well-known test key)
TEST_PRIVATE_KEY = "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a0f361234"

def test_wallet_manager_no_key():
    wm = WalletManager(private_key="")
    assert wm.has_wallet() is False
    assert wm.get_address() == ""
    assert wm.get_masked_address() == "NO_WALLET"
    assert getattr(wm, "private_key", None) is None

def test_wallet_manager_secure_key_storage():
    wm = WalletManager(private_key=TEST_PRIVATE_KEY)
    assert wm.has_wallet() is True
    assert wm.get_address().startswith("0x")
    assert wm.get_masked_address() != "NO_WALLET"
    # Verify private key is NOT exposed as an instance attribute
    assert getattr(wm, "private_key", None) is None
    assert "private_key" not in wm.__dict__

def test_sign_transaction_without_wallet():
    wm = WalletManager(private_key="")
    with pytest.raises(ValueError, match="No private key loaded"):
        wm.sign_transaction({"to": "0x1111111111111111111111111111111111111111", "value": 0})
