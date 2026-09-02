import logging
from typing import Dict, Any
from config.settings import settings
from src.dex.base_adapter import BaseDEXAdapter
from src.token.safety_analyzer import TokenSafetyAnalyzer
from src.core.profit_calculator import ProfitCalculator

logger = logging.getLogger("TradeSimulator")

class TradeSimulator:
    def __init__(
        self,
        dex_adapter: BaseDEXAdapter,
        safety_analyzer: TokenSafetyAnalyzer = None,
        profit_calculator: ProfitCalculator = None
    ):
        self.dex_adapter = dex_adapter
        self.safety_analyzer = safety_analyzer or TokenSafetyAnalyzer(dex_adapter=dex_adapter)
        self.profit_calculator = profit_calculator or ProfitCalculator()

    def simulate_arbitrage_cycle(
        self,
        target_token: str,
        initial_gat: float = 100.0,
        token_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Simulate complete GAT -> TOKEN -> GAT round-trip cycle.
        Validates safety, quotes, gas costs, slippage, and net return.
        """
        base_token = settings.BASE_TOKEN_ADDRESS
        if token_info is None:
            token_info = {}

        # 1. Run Token Safety Analysis
        safety_res = self.safety_analyzer.analyze_token(
            token_address=target_token,
            token_info=token_info,
            test_amount_gat=initial_gat
        )

        if not safety_res["safe"]:
            return {
                "valid": False,
                "rejection_reason": f"Safety check failed: {', '.join(safety_res['reasons'])}",
                "safety_analysis": safety_res,
                "profit_analysis": None
            }

        # Performance Optimization: TokenSafetyAnalyzer already calculated quotes during the safety check
        # (tokens_received and gat_received). Re-using them when initial_gat matches test_amount_gat
        # eliminates 2 redundant get_quote calls per cycle.
        buy_tax = safety_res.get("buy_tax", 0.0)
        can_use_cache = (safety_res.get("test_amount_gat") == initial_gat)
        cached_tokens_out = safety_res.get("tokens_received", 0.0) if can_use_cache else 0.0
        cached_final_gat_gross = safety_res.get("gat_received", 0.0) if can_use_cache else 0.0

        # 2. Simulate Leg 1: GAT -> TOKEN
        if cached_tokens_out > 0:
            tokens_out = cached_tokens_out
        else:
            try:
                tokens_out = self.dex_adapter.get_quote(initial_gat, base_token, target_token)
            except Exception as e:
                return {
                    "valid": False,
                    "rejection_reason": f"Failed quote on Leg 1 (GAT -> TOKEN): {e}",
                    "safety_analysis": safety_res,
                    "profit_analysis": None
                }

        if tokens_out <= 0:
            return {
                "valid": False,
                "rejection_reason": "Leg 1 (GAT -> TOKEN) returned 0 tokens",
                "safety_analysis": safety_res,
                "profit_analysis": None
            }

        # Apply buy tax
        tokens_received = tokens_out * (1.0 - (buy_tax / 100.0))

        # 3. Simulate Leg 2: TOKEN -> GAT
        if cached_final_gat_gross > 0:
            final_gat_gross = cached_final_gat_gross
        else:
            try:
                final_gat_gross = self.dex_adapter.get_quote(tokens_received, target_token, base_token)
            except Exception as e:
                return {
                    "valid": False,
                    "rejection_reason": f"Failed quote on Leg 2 (TOKEN -> GAT): {e}",
                    "safety_analysis": safety_res,
                    "profit_analysis": None
                }

        if final_gat_gross <= 0:
            return {
                "valid": False,
                "rejection_reason": "Leg 2 (TOKEN -> GAT) returned 0 GAT (Sell simulation failed)",
                "safety_analysis": safety_res,
                "profit_analysis": None
            }

        # 4. Estimate Gas Costs for 2 swaps
        gas_leg1 = self.dex_adapter.estimate_gas(base_token, target_token, initial_gat)
        gas_leg2 = self.dex_adapter.estimate_gas(target_token, base_token, tokens_received)
        total_gas_gat = gas_leg1 + gas_leg2

        # 5. Profit Calculation
        sell_tax = safety_res.get("sell_tax", 0.0)
        profit_res = self.profit_calculator.calculate_round_trip(
            initial_gat=initial_gat,
            token_received_gross=tokens_out,
            final_gat_gross=final_gat_gross,
            buy_tax_percent=buy_tax,
            sell_tax_percent=sell_tax,
            slippage_percent=settings.MAX_SLIPPAGE_PERCENT,
            gas_cost_gat=total_gas_gat
        )

        if not profit_res["profitable"]:
            return {
                "valid": False,
                "rejection_reason": f"Unprofitable cycle: {profit_res['reason']}",
                "safety_analysis": safety_res,
                "profit_analysis": profit_res,
                "tokens_received": tokens_received,
                "final_gat_gross": final_gat_gross,
                "total_gas_gat": total_gas_gat
            }

        return {
            "valid": True,
            "rejection_reason": None,
            "safety_analysis": safety_res,
            "profit_analysis": profit_res,
            "tokens_received": tokens_received,
            "final_gat_gross": final_gat_gross,
            "total_gas_gat": total_gas_gat
        }
