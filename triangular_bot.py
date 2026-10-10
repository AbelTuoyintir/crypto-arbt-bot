import os
import sys
import time
import argparse
import logging
from typing import List, Dict, Any

from config.settings import settings
from src.dex.manager import DEXManager
from src.dex.pancakeswap_adapter import PancakeSwapAdapter
from src.core.engine import ArbitrageEngine
from src.scanner.market_scanner import MarketScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [TRIANGULAR_BOT] %(message)s'
)
logger = logging.getLogger("TriangularBot")

# Sample token addresses on BSC
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
BUSD = "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"
USDT = "0x55d398326f99059fF775485246999027B3197955"
CAKE = "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
ETH = "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"

DEFAULT_TRIANGULAR_PAIRS = [
    {
        "token_a": {"address": WBNB, "symbol": "WBNB", "liquidity": 500000.0, "buy_tax": 0.0, "sell_tax": 0.0},
        "token_b": {"address": BUSD, "symbol": "BUSD", "liquidity": 500000.0, "buy_tax": 0.0, "sell_tax": 0.0}
    },
    {
        "token_a": {"address": USDT, "symbol": "USDT", "liquidity": 400000.0, "buy_tax": 0.0, "sell_tax": 0.0},
        "token_b": {"address": CAKE, "symbol": "CAKE", "liquidity": 200000.0, "buy_tax": 0.0, "sell_tax": 0.0}
    },
    {
        "token_a": {"address": WBNB, "symbol": "WBNB", "liquidity": 500000.0, "buy_tax": 0.0, "sell_tax": 0.0},
        "token_b": {"address": CAKE, "symbol": "CAKE", "liquidity": 200000.0, "buy_tax": 0.0, "sell_tax": 0.0}
    },
    {
        "token_a": {"address": ETH, "symbol": "ETH", "liquidity": 300000.0, "buy_tax": 0.0, "sell_tax": 0.0},
        "token_b": {"address": BUSD, "symbol": "BUSD", "liquidity": 500000.0, "buy_tax": 0.0, "sell_tax": 0.0}
    }
]

def create_triangular_bot_engine() -> tuple[DEXManager, ArbitrageEngine, MarketScanner]:
    """Initialize DEX adapters, engine, and market scanner for triangular arbitrage."""
    dex_manager = DEXManager()

    # Try initializing real PancakeSwap adapter, or fallback if RPC is offline
    try:
        pancake_adapter = PancakeSwapAdapter()
        dex_manager.register_adapter("PancakeSwap", pancake_adapter)
    except Exception as e:
        logger.warning(f"Could not connect to live RPC for PancakeSwap: {e}. Registered DEX adapters ready for simulation.")

    engine = ArbitrageEngine(dex_manager=dex_manager)
    scanner = MarketScanner(dex_manager=dex_manager, engine=engine)
    return dex_manager, engine, scanner

def run_triangular_bot(
    interval: int = 5,
    iterations: int = None,
    initial_gat: float = 100.0,
    single_run: bool = False
):
    """Run continuous or single-pass 95% profit rate triangular arbitrage bot."""
    dex_manager, engine, scanner = create_triangular_bot_engine()

    logger.info("==========================================================")
    logger.info("   🚀 GAT ENHANCED TRIANGULAR ARBITRAGE BOT INITIALIZED")
    logger.info(f"   Base Token        : {settings.BASE_TOKEN_NAME} ({settings.BASE_TOKEN_SYMBOL})")
    logger.info(f"   Trading Mode      : {settings.TRADING_MODE.upper()}")
    logger.info(f"   High Win-Rate Mode: {settings.HIGH_WIN_RATE_MODE}")
    logger.info(f"   Target Win Rate   : {settings.TARGET_WIN_RATE_PERCENT}%")
    logger.info(f"   Min Confidence    : {settings.MIN_CONFIDENCE_SCORE}%")
    logger.info(f"   Daily Profit Target: {settings.TARGET_DAILY_PROFIT_PERCENT}%")
    logger.info("==========================================================")

    engine.log_strategy_disclaimer()

    loop_count = 0
    try:
        while True:
            loop_count += 1
            logger.info(f"\n--- Scan Iteration #{loop_count} ---")

            # Scan triangular token pairs
            results = scanner.scan_triangular_market(
                token_pairs=DEFAULT_TRIANGULAR_PAIRS,
                initial_gat=initial_gat
            )

            # Summarize loop results
            win_rate = engine.risk_manager.get_daily_win_rate()
            logger.info(f"[SUMMARY] Daily Trades: {engine.risk_manager.daily_trades} | Daily Win Rate: {win_rate:.1f}% (Target: {settings.TARGET_WIN_RATE_PERCENT}%)")

            if single_run or (iterations and loop_count >= iterations):
                logger.info("Completed requested scanning iterations. Bot shutting down cleanly.")
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Triangular Trading Bot stopped by user.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GAT Enhanced 95% Profit Rate Triangular Trading Bot")
    parser.add_argument("--interval", type=int, default=5, help="Scan interval in seconds (default: 5)")
    parser.add_argument("--iterations", type=int, default=None, help="Number of iterations to run (default: infinite)")
    parser.add_argument("--initial-gat", type=float, default=100.0, help="Initial trade size in GAT (default: 100.0)")
    parser.add_argument("--single-run", action="store_true", help="Run a single market scan cycle and exit")

    args = parser.parse_args()
    run_triangular_bot(
        interval=args.interval,
        iterations=args.iterations,
        initial_gat=args.initial_gat,
        single_run=args.single_run
    )
