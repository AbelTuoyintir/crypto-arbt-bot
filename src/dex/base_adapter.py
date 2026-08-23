from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseDEXAdapter(ABC):
    """Abstract base class for all DEX adapters."""

    def __init__(self, name: str, router_address: str, factory_address: str):
        self.name = name
        self.router_address = router_address
        self.factory_address = factory_address

    @abstractmethod
    def get_quote(self, amount_in: float, token_in: str, token_out: str) -> float:
        """Get expected amount out for a given swap amount."""
        pass

    @abstractmethod
    def estimate_output(self, amount_in: float, token_in: str, token_out: str, fee_bips: int = 25) -> float:
        """Estimate output amount considering pool reserves and DEX fees."""
        pass

    @abstractmethod
    def estimate_gas(self, token_in: str, token_out: str, amount_in: float) -> float:
        """Estimate gas cost for executing a swap."""
        pass

    @abstractmethod
    def simulate_swap(self, token_in: str, token_out: str, amount_in: float, min_amount_out: float) -> Dict[str, Any]:
        """Simulate a swap execution without committing a transaction."""
        pass

    @abstractmethod
    def execute_swap(self, token_in: str, token_out: str, amount_in: float, min_amount_out: float) -> Dict[str, Any]:
        """Execute a swap transaction on the DEX."""
        pass

    @abstractmethod
    def get_liquidity(self, token_a: str, token_b: str) -> float:
        """Get pool liquidity in terms of reserve value or quote asset."""
        pass

    @abstractmethod
    def get_pool_price(self, token_in: str, token_out: str) -> float:
        """Get spot pool price ratio (token_out per token_in)."""
        pass
