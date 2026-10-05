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

        # 2. Simulate Leg 1: GAT -> TOKEN
        # Optimization: Reuse pre-calculated quotes from safety analysis only if test_amount_gat matches initial_gat
        tokens_out = 0.0
        final_gat_gross = 0.0
        if safety_res.get("test_amount_gat") == initial_gat:
            tokens_out = safety_res.get("tokens_received", 0.0)
            final_gat_gross = safety_res.get("final_gat_gross", 0.0)

        if tokens_out <= 0:
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
        buy_tax = safety_res.get("buy_tax", 0.0)
        tokens_received = tokens_out * (1.0 - (buy_tax / 100.0))

        # 3. Simulate Leg 2: TOKEN -> GAT
        if final_gat_gross <= 0:
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

    def simulate_triangular_arbitrage_cycle(
        self,
        token_a: str,
        token_b: str,
        initial_gat: float = 100.0,
        token_a_info: Dict[str, Any] = None,
        token_b_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Simulate complete 3-leg triangular cycle: GAT -> TOKEN A -> TOKEN B -> GAT.
        Validates safety for both intermediate tokens, quotes each swap leg,
        estimates total gas costs across 3 legs, and calculates net return.
        """
        base_token = settings.BASE_TOKEN_ADDRESS
        if token_a_info is None:
            token_a_info = {}
        if token_b_info is None:
            token_b_info = {}

        # 1. Token Safety Analysis for Token A & Token B
        safety_a = self.safety_analyzer.analyze_token(
            token_address=token_a,
            token_info=token_a_info,
            test_amount_gat=initial_gat
        )
        if not safety_a["safe"]:
            return {
                "valid": False,
                "rejection_reason": f"Token A safety check failed: {', '.join(safety_a['reasons'])}",
                "safety_analysis_a": safety_a,
                "safety_analysis_b": None,
                "profit_analysis": None
            }

        safety_b = self.safety_analyzer.analyze_token(
            token_address=token_b,
            token_info=token_b_info,
            test_amount_gat=initial_gat
        )
        if not safety_b["safe"]:
            return {
                "valid": False,
                "rejection_reason": f"Token B safety check failed: {', '.join(safety_b['reasons'])}",
                "safety_analysis_a": safety_a,
                "safety_analysis_b": safety_b,
                "profit_analysis": None
            }

        # Combined Safety Analysis Summary
        combined_risk_score = max(safety_a.get("risk_score", 0.0), safety_b.get("risk_score", 0.0))
        safety_summary = {
            "safe": True,
            "risk_score": combined_risk_score,
            "risk_level": "SAFE" if combined_risk_score <= 20 else ("LOW RISK" if combined_risk_score <= 40 else "MEDIUM RISK"),
            "token_a": safety_a,
            "token_b": safety_b
        }

        # 2. Simulate Leg 1: GAT -> TOKEN A
        try:
            token_a_out = self.dex_adapter.get_quote(initial_gat, base_token, token_a)
        except Exception as e:
            return {
                "valid": False,
                "rejection_reason": f"Failed quote on Leg 1 (GAT -> Token A): {e}",
                "safety_analysis": safety_summary,
                "profit_analysis": None
            }

        if token_a_out <= 0:
            return {
                "valid": False,
                "rejection_reason": "Leg 1 (GAT -> Token A) returned 0 tokens",
                "safety_analysis": safety_summary,
                "profit_analysis": None
            }

        token_a_buy_tax = safety_a.get("buy_tax", 0.0)
        token_a_net = token_a_out * (1.0 - (token_a_buy_tax / 100.0))

        # 3. Simulate Leg 2: TOKEN A -> TOKEN B
        try:
            token_b_out = self.dex_adapter.get_quote(token_a_net, token_a, token_b)
        except Exception as e:
            return {
                "valid": False,
                "rejection_reason": f"Failed quote on Leg 2 (Token A -> Token B): {e}",
                "safety_analysis": safety_summary,
                "profit_analysis": None
            }

        if token_b_out <= 0:
            return {
                "valid": False,
                "rejection_reason": "Leg 2 (Token A -> Token B) returned 0 tokens",
                "safety_analysis": safety_summary,
                "profit_analysis": None
            }

        token_a_sell_tax = safety_a.get("sell_tax", 0.0)
        token_b_buy_tax = safety_b.get("buy_tax", 0.0)
        token_b_net = token_b_out * (1.0 - (token_a_sell_tax / 100.0)) * (1.0 - (token_b_buy_tax / 100.0))

        # 4. Simulate Leg 3: TOKEN B -> GAT
        try:
            final_gat_gross = self.dex_adapter.get_quote(token_b_net, token_b, base_token)
        except Exception as e:
            return {
                "valid": False,
                "rejection_reason": f"Failed quote on Leg 3 (Token B -> GAT): {e}",
                "safety_analysis": safety_summary,
                "profit_analysis": None
            }

        if final_gat_gross <= 0:
            return {
                "valid": False,
                "rejection_reason": "Leg 3 (Token B -> GAT) returned 0 GAT",
                "safety_analysis": safety_summary,
                "profit_analysis": None
            }

        # 5. Estimate Gas Costs across all 3 legs
        gas_leg1 = self.dex_adapter.estimate_gas(base_token, token_a, initial_gat)
        gas_leg2 = self.dex_adapter.estimate_gas(token_a, token_b, token_a_net)
        gas_leg3 = self.dex_adapter.estimate_gas(token_b, base_token, token_b_net)
        total_gas_gat = gas_leg1 + gas_leg2 + gas_leg3

        # 6. Profit Calculation
        token_b_sell_tax = safety_b.get("sell_tax", 0.0)
        profit_res = self.profit_calculator.calculate_triangular_round_trip(
            initial_gat=initial_gat,
            token_a_gross=token_a_out,
            token_b_gross=token_b_out,
            final_gat_gross=final_gat_gross,
            token_a_buy_tax=token_a_buy_tax,
            token_a_sell_tax=token_a_sell_tax,
            token_b_buy_tax=token_b_buy_tax,
            token_b_sell_tax=token_b_sell_tax,
            slippage_percent=settings.MAX_SLIPPAGE_PERCENT,
            gas_cost_gat=total_gas_gat
        )

        if not profit_res["profitable"]:
            return {
                "valid": False,
                "rejection_reason": f"Unprofitable triangular cycle: {profit_res['reason']}",
                "safety_analysis": safety_summary,
                "profit_analysis": profit_res,
                "token_a_received": token_a_net,
                "token_b_received": token_b_net,
                "final_gat_gross": final_gat_gross,
                "total_gas_gat": total_gas_gat
            }

        return {
            "valid": True,
            "rejection_reason": None,
            "safety_analysis": safety_summary,
            "profit_analysis": profit_res,
            "token_a_received": token_a_net,
            "token_b_received": token_b_net,
            "final_gat_gross": final_gat_gross,
            "total_gas_gat": total_gas_gat
        }
