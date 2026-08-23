import logging
from typing import Dict, Any
from config.settings import settings

logger = logging.getLogger("ProfitCalculator")

class ProfitCalculator:
    def __init__(self, min_profit_percent: float = None):
        self.min_profit_percent = min_profit_percent if min_profit_percent is not None else settings.MIN_PROFIT_PERCENT

    def calculate_round_trip(
        self,
        initial_gat: float,
        token_received_gross: float,
        final_gat_gross: float,
        buy_tax_percent: float = 0.0,
        sell_tax_percent: float = 0.0,
        dex_fee_percent: float = 0.25,
        slippage_percent: float = 0.5,
        gas_cost_gat: float = 0.0,
        price_impact_percent: float = 0.0,
        other_costs_gat: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates full round-trip profitability for GAT -> TOKEN -> GAT
        incorporating DEX fees, buy/sell taxes, slippage, gas cost, and price impact.
        """
        if initial_gat <= 0:
            return {
                "profitable": False,
                "net_profit": 0.0,
                "profit_percentage": 0.0,
                "reason": "Initial GAT amount must be greater than zero"
            }

        # Step 1: Buy Leg (GAT -> TOKEN) with buy tax accounted for
        tokens_after_buy_tax = token_received_gross * (1.0 - (buy_tax_percent / 100.0))

        # Adjust final gross GAT proportionally to tokens remaining after buy tax
        if token_received_gross > 0:
            effective_final_gat_gross = final_gat_gross * (tokens_after_buy_tax / token_received_gross)
        else:
            effective_final_gat_gross = 0.0

        # Step 2: Sell Leg (TOKEN -> GAT) applying sell tax
        gat_after_sell_tax = effective_final_gat_gross * (1.0 - (sell_tax_percent / 100.0))

        # Apply Slippage and Price Impact allowances
        slippage_deduction = gat_after_sell_tax * (slippage_percent / 100.0)
        price_impact_deduction = gat_after_sell_tax * (price_impact_percent / 100.0)

        # Net GAT estimate after all deductions
        net_gat = gat_after_sell_tax - slippage_deduction - price_impact_deduction - gas_cost_gat - other_costs_gat

        net_profit = net_gat - initial_gat
        profit_percentage = (net_profit / initial_gat) * 100.0

        is_profitable = (net_profit > 0) and (profit_percentage >= self.min_profit_percent)

        return {
            "profitable": is_profitable,
            "initial_gat": initial_gat,
            "gross_final_gat": final_gat_gross,
            "net_final_gat": max(0.0, net_gat),
            "net_profit": net_profit,
            "profit_percentage": profit_percentage,
            "gas_cost": gas_cost_gat,
            "buy_tax_percent": buy_tax_percent,
            "sell_tax_percent": sell_tax_percent,
            "slippage_percent": slippage_percent,
            "price_impact_percent": price_impact_percent,
            "reason": None if is_profitable else ("Profit below threshold" if net_profit > 0 else "Unprofitable round trip")
        }
