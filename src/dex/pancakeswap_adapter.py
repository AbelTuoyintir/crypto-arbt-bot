import logging
import time
from typing import Dict, Any
from web3 import Web3
from src.dex.base_adapter import BaseDEXAdapter
from config.settings import settings

logger = logging.getLogger("PancakeSwapAdapter")

PANCAKE_ROUTER_V2 = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
PANCAKE_FACTORY_V2 = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"

class PancakeSwapAdapter(BaseDEXAdapter):
    def __init__(self, rpc_url: str = None, router_address: str = PANCAKE_ROUTER_V2, factory_address: str = PANCAKE_FACTORY_V2, gas_price_ttl: float = 5.0):
        super().__init__(name="PancakeSwapV2", router_address=router_address, factory_address=factory_address)
        self.rpc_url = rpc_url or settings.RPC_URL
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self._mock_pools = {}
        # Gas price caching attributes (reduces expensive RPC calls during scanning/simulation)
        self.gas_price_ttl = gas_price_ttl
        self._cached_gas_price: float = None
        self._gas_price_updated_at: float = 0.0

    def set_mock_pool(self, token_a: str, token_b: str, reserve_a: float, reserve_b: float, fee_percent: float = 0.25):
        """Set mock pool reserves for offline testing/simulation."""
        # BOLT OPTIMIZATION: Avoid duplicate .lower() calls and min()/max() overhead
        a_low, b_low = token_a.lower(), token_b.lower()
        if a_low < b_low:
            key = f"{a_low}_{b_low}"
            self._mock_pools[key] = {"reserve_a": reserve_a, "reserve_b": reserve_b, "fee": fee_percent}
        else:
            key = f"{b_low}_{a_low}"
            self._mock_pools[key] = {"reserve_a": reserve_b, "reserve_b": reserve_a, "fee": fee_percent}

    def _get_reserves(self, token_in: str, token_out: str):
        # BOLT OPTIMIZATION: High-frequency lookup path optimized by avoiding duplicate .lower()
        # and min()/max() string comparisons during scanning and quote simulations.
        in_low, out_low = token_in.lower(), token_out.lower()
        if in_low < out_low:
            key = f"{in_low}_{out_low}"
            pool = self._mock_pools.get(key)
            if pool:
                return pool["reserve_a"], pool["reserve_b"], pool["fee"]
        else:
            key = f"{out_low}_{in_low}"
            pool = self._mock_pools.get(key)
            if pool:
                return pool["reserve_b"], pool["reserve_a"], pool["fee"]
        # Default mock fallback if not set
        return 100000.0, 100000.0, 0.25

    def get_quote(self, amount_in: float, token_in: str, token_out: str) -> float:
        return self.estimate_output(amount_in, token_in, token_out)

    def estimate_output(self, amount_in: float, token_in: str, token_out: str, fee_bips: int = 25) -> float:
        if amount_in <= 0:
            return 0.0
        reserve_in, reserve_out, fee_pct = self._get_reserves(token_in, token_out)
        fee_multiplier = (10000 - fee_bips) / 10000.0
        amount_in_with_fee = amount_in * fee_multiplier
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in + amount_in_with_fee
        if denominator == 0:
            return 0.0
        return numerator / denominator

    def _get_gas_price(self) -> float:
        """
        Fetch current gas price in ETH/BNB from Web3 RPC, cached for `gas_price_ttl` seconds
        to avoid latency bottlenecks during high-frequency market scanning.
        """
        now = time.time()
        if self._cached_gas_price is None or (now - self._gas_price_updated_at) > self.gas_price_ttl:
            try:
                self._cached_gas_price = float(self.w3.from_wei(self.w3.eth.gas_price, 'ether'))
            except Exception:
                self._cached_gas_price = 3e-9  # 3 gwei default fallback
            self._gas_price_updated_at = now
        return self._cached_gas_price

    def estimate_gas(self, token_in: str, token_out: str, amount_in: float) -> float:
        # Standard Pancakeswap swap gas requirement ~150,000 gas
        # Uses cached gas price to prevent redundant RPC network calls in loops
        gas_price = self._get_gas_price()
        return gas_price * 150000

    def simulate_swap(self, token_in: str, token_out: str, amount_in: float, min_amount_out: float) -> Dict[str, Any]:
        expected_output = self.estimate_output(amount_in, token_in, token_out)
        gas_cost = self.estimate_gas(token_in, token_out, amount_in)

        if expected_output < min_amount_out:
            return {
                "success": False,
                "error": "Slippage tolerance exceeded in simulation",
                "amount_in": amount_in,
                "amount_out": expected_output,
                "min_amount_out": min_amount_out,
                "gas_cost": gas_cost
            }

        return {
            "success": True,
            "error": None,
            "amount_in": amount_in,
            "amount_out": expected_output,
            "min_amount_out": min_amount_out,
            "gas_cost": gas_cost
        }

    def execute_swap(self, token_in: str, token_out: str, amount_in: float, min_amount_out: float) -> Dict[str, Any]:
        sim = self.simulate_swap(token_in, token_out, amount_in, min_amount_out)
        if not sim["success"]:
            return sim

        if not settings.ENABLE_LIVE_TRADING:
            return {
                "success": True,
                "simulated": True,
                "tx_hash": "0xsimulated_pancakeswap_tx_hash",
                "amount_in": amount_in,
                "amount_out": sim["amount_out"],
                "gas_used": sim["gas_cost"]
            }

        return {
            "success": False,
            "error": "Live mainnet trading is disabled by default",
            "tx_hash": None
        }

    def get_liquidity(self, token_a: str, token_b: str) -> float:
        reserve_a, reserve_b, _ = self._get_reserves(token_a, token_b)
        return min(reserve_a, reserve_b)

    def get_pool_price(self, token_in: str, token_out: str) -> float:
        reserve_in, reserve_out, _ = self._get_reserves(token_in, token_out)
        if reserve_in <= 0:
            return 0.0
        return reserve_out / reserve_in
