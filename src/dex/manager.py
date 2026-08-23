import logging
from typing import Dict, List, Optional, Any
from src.dex.base_adapter import BaseDEXAdapter

logger = logging.getLogger("DEXManager")

class DEXManager:
    def __init__(self):
        self._adapters: Dict[str, BaseDEXAdapter] = {}

    def register_adapter(self, name: str, adapter: BaseDEXAdapter):
        self._adapters[name] = adapter
        logger.info(f"Registered DEX adapter: {name}")

    def get_adapter(self, name: str) -> Optional[BaseDEXAdapter]:
        return self._adapters.get(name)

    def list_adapters(self) -> List[str]:
        return list(self._adapters.keys())

    def get_best_quote(self, amount_in: float, token_in: str, token_out: str) -> Dict[str, Any]:
        best_dex = None
        max_output = 0.0

        for name, adapter in self._adapters.items():
            try:
                output = adapter.get_quote(amount_in, token_in, token_out)
                if output > max_output:
                    max_output = output
                    best_dex = name
            except Exception as e:
                logger.error(f"Error getting quote from DEX adapter {name}: {e}")

        return {
            "dex": best_dex,
            "amount_in": amount_in,
            "amount_out": max_output
        }
