import logging
from web3 import Web3
from config.settings import settings
from src.wallet.wallet_manager import WalletManager

logger = logging.getLogger("TransactionManager")

class TransactionManager:
    def __init__(self, wallet_manager: WalletManager = None, w3: Web3 = None):
        self.w3 = w3 or Web3(Web3.HTTPProvider(settings.RPC_URL))
        self.wallet_manager = wallet_manager or WalletManager(rpc_url=settings.RPC_URL)

    def estimate_gas_cost(self, tx_params: dict = None) -> float:
        """Estimate gas cost in ETH/BNB."""
        try:
            gas_price = self.w3.eth.gas_price
        except Exception:
            gas_price = self.w3.to_wei(3, 'gwei')

        gas_limit = 300000  # Default swap gas estimate
        if tx_params and 'to' in tx_params:
            try:
                gas_limit = self.w3.eth.estimate_gas(tx_params)
            except Exception as e:
                logger.warning(f"Failed to estimate precise gas limit: {e}. Using default {gas_limit}")

        cost_wei = gas_price * gas_limit
        return float(self.w3.from_wei(cost_wei, 'ether'))

    def send_transaction(self, tx_dict: dict) -> dict:
        """Send a transaction with safety checks and error handling."""
        if not self.wallet_manager.has_wallet():
            return {
                "success": False,
                "error": "No wallet loaded",
                "tx_hash": None
            }

        if not settings.ENABLE_LIVE_TRADING:
            logger.info("LIVE_TRADING is disabled. Simulating transaction execution.")
            return {
                "success": True,
                "error": None,
                "tx_hash": "0xsimulated_tx_hash_" + self.wallet_manager.get_masked_address()
            }

        sender = self.wallet_manager.get_address()

        try:
            nonce = self.w3.eth.get_transaction_count(sender, 'pending')
            gas_price = self.w3.eth.gas_price

            tx = {
                'from': sender,
                'nonce': nonce,
                'gasPrice': gas_price,
                'gas': tx_dict.get('gas', 300000),
                'chain_id': settings.CHAIN_ID,
                **tx_dict
            }

            signed_tx = self.wallet_manager.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()

            logger.info(f"Transaction submitted. Hash: {tx_hash_hex}")

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            if receipt.status == 1:
                return {
                    "success": True,
                    "error": None,
                    "tx_hash": tx_hash_hex,
                    "receipt": receipt
                }
            else:
                return {
                    "success": False,
                    "error": "Transaction reverted on chain",
                    "tx_hash": tx_hash_hex,
                    "receipt": receipt
                }

        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tx_hash": None
            }
