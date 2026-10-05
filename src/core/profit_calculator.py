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

    def calculate_triangular_round_trip(
        self,
        initial_gat: float,
        token_a_gross: float,
        token_b_gross: float,
        final_gat_gross: float,
        token_a_buy_tax: float = 0.0,
        token_a_sell_tax: float = 0.0,
        token_b_buy_tax: float = 0.0,
        token_b_sell_tax: float = 0.0,
        dex_fee_percent: float = 0.25,
        slippage_percent: float = 0.5,
        gas_cost_gat: float = 0.0,
        price_impact_percent: float = 0.0,
        other_costs_gat: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates full 3-leg triangular arbitrage profitability:
        GAT -> TOKEN A -> TOKEN B -> GAT
        incorporating DEX fees, buy/sell taxes for intermediate tokens,
        gas costs across 3 legs, slippage, and price impact.
        """
        if initial_gat <= 0:
            return {
                "profitable": False,
                "net_profit": 0.0,
                "profit_percentage": 0.0,
                "reason": "Initial GAT amount must be greater than zero"
            }

        # Step 1: Leg 1 (GAT -> TOKEN A) after Token A buy tax
        token_a_after_buy_tax = token_a_gross * (1.0 - (token_a_buy_tax / 100.0))

        # Adjust Token B output proportionally if Token A net amount was reduced by buy tax
        if token_a_gross > 0:
            token_b_effective_gross = token_b_gross * (token_a_after_buy_tax / token_a_gross)
        else:
            token_b_effective_gross = 0.0

        # Step 2: Leg 2 (TOKEN A -> TOKEN B) after Token A sell tax & Token B buy tax
        token_b_after_taxes = token_b_effective_gross * (1.0 - (token_a_sell_tax / 100.0)) * (1.0 - (token_b_buy_tax / 100.0))

        # Step 3: Leg 3 (TOKEN B -> GAT) adjust final GAT proportionally to token B net amount
        if token_b_gross > 0:
            effective_final_gat = final_gat_gross * (token_b_after_taxes / token_b_gross)
        else:
            effective_final_gat = 0.0

        # Apply Token B sell tax
        gat_after_all_taxes = effective_final_gat * (1.0 - (token_b_sell_tax / 100.0))

        # Deduct Slippage and Price Impact allowances
        slippage_deduction = gat_after_all_taxes * (slippage_percent / 100.0)
        price_impact_deduction = gat_after_all_taxes * (price_impact_percent / 100.0)

        # Net GAT estimate after all costs
        net_gat = gat_after_all_taxes - slippage_deduction - price_impact_deduction - gas_cost_gat - other_costs_gat

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
            "token_a_buy_tax": token_a_buy_tax,
            "token_a_sell_tax": token_a_sell_tax,
            "token_b_buy_tax": token_b_buy_tax,
            "token_b_sell_tax": token_b_sell_tax,
            "slippage_percent": slippage_percent,
            "price_impact_percent": price_impact_percent,
            "reason": None if is_profitable else ("Profit below threshold" if net_profit > 0 else "Unprofitable triangular round trip")
        }
