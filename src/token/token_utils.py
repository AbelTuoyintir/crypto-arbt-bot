import logging
from web3 import Web3
from config.settings import settings

logger = logging.getLogger("TokenUtils")

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
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
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "paused",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

class TokenUtils:
    def __init__(self, rpc_url: str = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url or settings.RPC_URL))

    def get_token_info(self, contract_address: str) -> dict:
        if not Web3.is_address(contract_address):
            return {
                "valid": False,
                "error": "Invalid EVM contract address"
            }
        try:
            checksum = Web3.to_checksum_address(contract_address)
            contract = self.w3.eth.contract(address=checksum, abi=ERC20_ABI)

            try:
                name = contract.functions.name().call()
            except Exception:
                name = "Unknown Token"

            try:
                symbol = contract.functions.symbol().call()
            except Exception:
                symbol = "UNKNOWN"

            try:
                decimals = contract.functions.decimals().call()
            except Exception:
                decimals = 18

            return {
                "valid": True,
                "address": checksum,
                "name": name,
                "symbol": symbol,
                "decimals": decimals
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
