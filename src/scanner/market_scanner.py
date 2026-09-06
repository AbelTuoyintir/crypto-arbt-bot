import time
import logging
from typing import List, Dict, Any
from config.settings import settings
from src.dex.manager import DEXManager
from src.core.engine import ArbitrageEngine

# Configure structured logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("MarketScanner")

class MarketScanner:
    def __init__(self, dex_manager: DEXManager, engine: ArbitrageEngine = None):
        self.dex_manager = dex_manager
        self.engine = engine or ArbitrageEngine(dex_manager=dex_manager)

    def scan_market(self, target_tokens: List[Dict[str, Any]], initial_gat: float = 100.0) -> List[Dict[str, Any]]:
        """
        Scan all supported DEXs and tokens for GAT arbitrage opportunities.
        Emits structured logs: [SCAN], [QUOTE], [SELL TEST], [COST], [NET], [DECISION].
        """
        results = []
        base_token = settings.BASE_TOKEN_ADDRESS

        for token in target_tokens:
            token_address = token.get("address")
            symbol = token.get("symbol", "UNKNOWN")

            logger.info(f"\n[SCAN]\n{settings.BASE_TOKEN_SYMBOL} -> {symbol} ({token_address})")

            for dex_name in self.dex_manager.list_adapters():
                dex_adapter = self.dex_manager.get_adapter(dex_name)
                if not dex_adapter:
                    continue

                try:
                    # Process through arbitrage engine (performs safety checks and simulation without redundant manual quotes)
                    res = self.engine.process_opportunity(
                        dex_name=dex_name,
                        target_token=token_address,
                        initial_gat=initial_gat,
                        token_info=token
                    )

                    profit = res.get("profit", 0.0)
                    results.append({
                        "token": symbol,
                        "dex": dex_name,
                        "profit": profit,
                        "engine_res": res
                    })

                except Exception as e:
                    logger.error(f"Error scanning pair {symbol} on {dex_name}: {e}")

        return results

    def start_scanning_loop(self, target_tokens: List[Dict[str, Any]], interval_seconds: int = 5, iterations: int = None):
        """Run continuous market scanning loop."""
        logger.info(f"Starting MarketScanner loop (interval: {interval_seconds}s)...")
        count = 0
        try:
            while True:
                self.scan_market(target_tokens)
                count += 1
                if iterations and count >= iterations:
                    break
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Market scanner stopped by user.")
