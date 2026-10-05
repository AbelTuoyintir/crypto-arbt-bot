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
                    # Optimization: Delegate simulation directly to ArbitrageEngine first
                    # to eliminate duplicate DEX quotes and gas estimation calls per scan cycle.
                    res = self.engine.process_opportunity(
                        dex_name=dex_name,
                        target_token=token_address,
                        initial_gat=initial_gat,
                        token_info=token
                    )

                    sim_res = res.get("sim_res") or {}
                    profit_analysis = sim_res.get("profit_analysis") or {}
                    safety_analysis = sim_res.get("safety_analysis") or {}

                    # Leg 1 Quote
                    tokens_out = sim_res.get("tokens_received", 0.0)
                    logger.info(f"[QUOTE]\nExpected output: {tokens_out:,.2f} {symbol}")

                    # Leg 2 Quote (Sell Test)
                    final_gat_gross = sim_res.get("final_gat_gross", 0.0)
                    sell_tax = safety_analysis.get("sell_tax", token.get("sell_tax", 0.0))
                    final_gat_after_taxes = final_gat_gross * (1 - (sell_tax / 100.0))
                    logger.info(f"[SELL TEST]\nExpected {settings.BASE_TOKEN_SYMBOL}: {final_gat_after_taxes:,.2f}")

                    # Cost breakdown
                    gas_cost = sim_res.get("total_gas_gat", 0.0)
                    dex_fees = initial_gat * 0.0025 * 2
                    slippage = initial_gat * (settings.MAX_SLIPPAGE_PERCENT / 100.0)
                    logger.info(f"[COST]\nGas: {gas_cost:.4f} {settings.BASE_TOKEN_SYMBOL}\nDEX Fees: {dex_fees:.4f} {settings.BASE_TOKEN_SYMBOL}\nSlippage: {slippage:.4f} {settings.BASE_TOKEN_SYMBOL}")

                    # Net profit
                    profit = profit_analysis.get("net_profit", 0.0)
                    net_gat = initial_gat + profit
                    logger.info(f"[NET]\nInitial: {initial_gat:.2f} {settings.BASE_TOKEN_SYMBOL}\nFinal: {net_gat:.2f} {settings.BASE_TOKEN_SYMBOL}\nProfit: {profit:.2f} {settings.BASE_TOKEN_SYMBOL}")

                    results.append({
                        "token": symbol,
                        "dex": dex_name,
                        "profit": profit,
                        "engine_res": res
                    })

                except Exception as e:
                    logger.error(f"Error scanning pair {symbol} on {dex_name}: {e}")

        return results

    def scan_triangular_market(
        self,
        token_pairs: List[Dict[str, Any]],
        initial_gat: float = 100.0
    ) -> List[Dict[str, Any]]:
        """
        Scan all supported DEXs for triangular arbitrage opportunities across token pairs (Token A, Token B).
        `token_pairs` should be a list of dicts with:
        {'token_a': {'address': ..., 'symbol': ...}, 'token_b': {'address': ..., 'symbol': ...}}
        Emits structured logs: [TRIANGULAR SCAN], [LEG 1 QUOTE], [LEG 2 QUOTE], [LEG 3 QUOTE], [COST], [NET], [DECISION].
        """
        results = []

        for pair in token_pairs:
            token_a = pair.get("token_a", {})
            token_b = pair.get("token_b", {})
            addr_a = token_a.get("address")
            addr_b = token_b.get("address")
            sym_a = token_a.get("symbol", "TOKEN_A")
            sym_b = token_b.get("symbol", "TOKEN_B")

            logger.info(f"\n[TRIANGULAR SCAN]\n{settings.BASE_TOKEN_SYMBOL} -> {sym_a} -> {sym_b} -> {settings.BASE_TOKEN_SYMBOL}")

            for dex_name in self.dex_manager.list_adapters():
                dex_adapter = self.dex_manager.get_adapter(dex_name)
                if not dex_adapter:
                    continue

                try:
                    res = self.engine.process_triangular_opportunity(
                        dex_name=dex_name,
                        token_a=addr_a,
                        token_b=addr_b,
                        initial_gat=initial_gat,
                        token_a_info=token_a,
                        token_b_info=token_b
                    )

                    sim_res = res.get("sim_res") or {}
                    profit_analysis = sim_res.get("profit_analysis") or {}

                    t_a_out = sim_res.get("token_a_received", 0.0)
                    t_b_out = sim_res.get("token_b_received", 0.0)
                    final_gat = sim_res.get("final_gat_gross", 0.0)

                    logger.info(f"[LEG 1 QUOTE]\nExpected {sym_a}: {t_a_out:,.2f}")
                    logger.info(f"[LEG 2 QUOTE]\nExpected {sym_b}: {t_b_out:,.2f}")
                    logger.info(f"[LEG 3 QUOTE]\nExpected {settings.BASE_TOKEN_SYMBOL}: {final_gat:,.2f}")

                    gas_cost = sim_res.get("total_gas_gat", 0.0)
                    dex_fees = initial_gat * 0.0025 * 3
                    slippage = initial_gat * (settings.MAX_SLIPPAGE_PERCENT / 100.0)
                    logger.info(f"[COST]\nGas: {gas_cost:.4f} {settings.BASE_TOKEN_SYMBOL}\nDEX Fees: {dex_fees:.4f} {settings.BASE_TOKEN_SYMBOL}\nSlippage: {slippage:.4f} {settings.BASE_TOKEN_SYMBOL}")

                    profit = profit_analysis.get("net_profit", 0.0)
                    net_gat = initial_gat + profit
                    logger.info(f"[NET]\nInitial: {initial_gat:.2f} {settings.BASE_TOKEN_SYMBOL}\nFinal: {net_gat:.2f} {settings.BASE_TOKEN_SYMBOL}\nProfit: {profit:.2f} {settings.BASE_TOKEN_SYMBOL}")

                    results.append({
                        "pair": f"{sym_a}->{sym_b}",
                        "dex": dex_name,
                        "profit": profit,
                        "engine_res": res
                    })

                except Exception as e:
                    logger.error(f"Error scanning triangular path {sym_a}->{sym_b} on {dex_name}: {e}")

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
