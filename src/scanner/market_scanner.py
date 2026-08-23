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
                    # Leg 1 Quote
                    tokens_out = dex_adapter.get_quote(initial_gat, base_token, token_address)
                    logger.info(f"[QUOTE]\nExpected output: {tokens_out:,.2f} {symbol}")

                    # Leg 2 Quote (Sell Test)
                    buy_tax = token.get("buy_tax", 0.0)
                    sell_tax = token.get("sell_tax", 0.0)
                    tokens_received = tokens_out * (1 - (buy_tax / 100.0))
                    final_gat_gross = dex_adapter.get_quote(tokens_received, token_address, base_token)
                    final_gat_after_taxes = final_gat_gross * (1 - (sell_tax / 100.0))
                    logger.info(f"[SELL TEST]\nExpected {settings.BASE_TOKEN_SYMBOL}: {final_gat_after_taxes:,.2f}")

                    # Cost breakdown
                    gas_cost = dex_adapter.estimate_gas(base_token, token_address, initial_gat) * 2
                    dex_fees = initial_gat * 0.0025 * 2
                    slippage = initial_gat * (settings.MAX_SLIPPAGE_PERCENT / 100.0)
                    logger.info(f"[COST]\nGas: {gas_cost:.4f} {settings.BASE_TOKEN_SYMBOL}\nDEX Fees: {dex_fees:.4f} {settings.BASE_TOKEN_SYMBOL}\nSlippage: {slippage:.4f} {settings.BASE_TOKEN_SYMBOL}")

                    # Net profit
                    net_gat = final_gat_after_taxes - gas_cost - slippage
                    profit = net_gat - initial_gat
                    logger.info(f"[NET]\nInitial: {initial_gat:.2f} {settings.BASE_TOKEN_SYMBOL}\nFinal: {net_gat:.2f} {settings.BASE_TOKEN_SYMBOL}\nProfit: {profit:.2f} {settings.BASE_TOKEN_SYMBOL}")

                    # Process through arbitrage engine
                    res = self.engine.process_opportunity(
                        dex_name=dex_name,
                        target_token=token_address,
                        initial_gat=initial_gat,
                        token_info=token
                    )

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
