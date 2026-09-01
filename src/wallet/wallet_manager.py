import logging
from web3 import Web3
from eth_account import Account
from config.settings import settings

logger = logging.getLogger("WalletManager")

class WalletManager:
    def __init__(self, rpc_url: str = None, private_key: str = None):
        self.rpc_url = rpc_url or settings.RPC_URL
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        pk = private_key or settings.PRIVATE_KEY
        self.account = None

        if pk:
            try:
                self.account = Account.from_key(pk)
                logger.info(f"Loaded wallet account: {self.get_masked_address()}")
            except Exception:
                logger.error("Failed to load account from private key")

    def has_wallet(self) -> bool:
        return self.account is not None

    def get_address(self) -> str:
        if self.account:
            return self.account.address
        return ""

    def get_masked_address(self) -> str:
        addr = self.get_address()
        if addr and len(addr) >= 10:
            return f"{addr[:6]}...{addr[-4:]}"
        return "NO_WALLET"

    def get_native_balance(self) -> float:
        if not self.account:
            return 0.0
        try:
            balance_wei = self.w3.eth.get_balance(self.account.address)
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logger.error(f"Error fetching native balance: {e}")
            return 0.0

    def get_token_balance(self, token_address: str) -> float:
        if not self.account or not Web3.is_address(token_address):
            return 0.0
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }
        ]
        try:
            checksum_token = Web3.to_checksum_address(token_address)
            checksum_user = Web3.to_checksum_address(self.account.address)
            contract = self.w3.eth.contract(address=checksum_token, abi=erc20_abi)
            balance_raw = contract.functions.balanceOf(checksum_user).call()
            try:
                decimals = contract.functions.decimals().call()
            except Exception:
                decimals = 18
            return balance_raw / (10 ** decimals)
        except Exception as e:
            logger.error(f"Error fetching token balance for {token_address}: {e}")
            return 0.0

    def sign_transaction(self, tx_dict: dict):
        if not self.account:
            raise ValueError("No private key loaded to sign transaction")
        return self.account.sign_transaction(tx_dict)
