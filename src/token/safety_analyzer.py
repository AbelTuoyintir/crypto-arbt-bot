import logging
from typing import Dict, Any, Optional
from web3 import Web3
from config.settings import settings
from src.dex.base_adapter import BaseDEXAdapter

logger = logging.getLogger("TokenSafetyAnalyzer")

class TokenSafetyAnalyzer:
    def __init__(self, base_token_address: str = None, dex_adapter: BaseDEXAdapter = None):
        self.base_token_address = base_token_address or settings.BASE_TOKEN_ADDRESS
        self.dex_adapter = dex_adapter

    def analyze_token(
        self,
        token_address: str,
        token_info: Optional[Dict[str, Any]] = None,
        test_amount_gat: float = 100.0
    ) -> Dict[str, Any]:
        """
        Perform complete validation and sellability test on target token.

        Risk Score categories:
        0-20    SAFE
        21-40   LOW RISK
        41-60   MEDIUM RISK
        61-80   HIGH RISK
        81-100  BLOCKED
        """
        rejection_reasons = []
        risk_score = 0.0

        if token_info is None:
            token_info = {}

        # 1. Address Validation
        if not token_address or not Web3.is_address(token_address) or token_address.lower() == self.base_token_address.lower():
            return {
                "safe": False,
                "risk_score": 100.0,
                "risk_level": "BLOCKED",
                "reasons": ["Invalid target token address or target is base token"],
                "buy_tax": 0.0,
                "sell_tax": 0.0,
                "sellable": False
            }

        # 2. Contract Status Checks (Is Paused / Blacklist / Whitelist restrictions)
        if token_info.get("is_paused", False):
            risk_score += 50.0
            rejection_reasons.append("Trading is paused on token contract")

        if token_info.get("has_blacklist", False):
            risk_score += 30.0
            rejection_reasons.append("Token contract contains blacklist capability")

        if token_info.get("transfer_restricted", False):
            risk_score += 40.0
            rejection_reasons.append("Token transfer restrictions detected")

        # 3. Liquidity & Volume Checks
        liquidity = token_info.get("liquidity", 0.0)
        if self.dex_adapter:
            pool_liq = self.dex_adapter.get_liquidity(self.base_token_address, token_address)
            liquidity = max(liquidity, pool_liq)

        if liquidity < settings.MIN_LIQUIDITY:
            risk_score += 45.0
            rejection_reasons.append(f"Insufficient pool liquidity: {liquidity} < {settings.MIN_LIQUIDITY}")

        # 4. Mandatory Sellability Test (GAT -> TOKEN -> GAT Simulation)
        buy_tax = token_info.get("buy_tax", 0.0)
        sell_tax = token_info.get("sell_tax", 0.0)
        is_honeypot = token_info.get("is_honeypot", False)
        sell_failed = token_info.get("sell_failed", False)

        if is_honeypot or sell_failed:
            risk_score = 100.0
            rejection_reasons.append("Honeypot behavior or sell simulation failed! Token CANNOT be sold back into GAT.")
            return {
                "safe": False,
                "risk_score": 100.0,
                "risk_level": "BLOCKED",
                "reasons": rejection_reasons,
                "buy_tax": buy_tax,
                "sell_tax": sell_tax,
                "sellable": False
            }

        # Round-trip Simulation with DEX Adapter if available
        sellable = True
        if self.dex_adapter:
            # Step 1: Buy GAT -> TOKEN
            tokens_received = self.dex_adapter.get_quote(test_amount_gat, self.base_token_address, token_address)
            tokens_after_buy_tax = tokens_received * (1 - (buy_tax / 100.0))

            if tokens_after_buy_tax <= 0:
                sellable = False
                risk_score = 100.0
                rejection_reasons.append("Buy swap produced zero output")
            else:
                # Step 2: Sell TOKEN -> GAT
                gat_received = self.dex_adapter.get_quote(tokens_after_buy_tax, token_address, self.base_token_address)
                gat_after_sell_tax = gat_received * (1 - (sell_tax / 100.0))

                if gat_after_sell_tax <= 0:
                    sellable = False
                    risk_score = 100.0
                    rejection_reasons.append("Sell simulation failed (0 GAT returned)")

        # 5. Tax Checks
        if buy_tax > settings.MAX_BUY_TAX_PERCENT:
            risk_score += 25.0
            rejection_reasons.append(f"Buy tax {buy_tax}% exceeds max allowed {settings.MAX_BUY_TAX_PERCENT}%")

        if sell_tax > settings.MAX_SELL_TAX_PERCENT:
            risk_score += 25.0
            rejection_reasons.append(f"Sell tax {sell_tax}% exceeds max allowed {settings.MAX_SELL_TAX_PERCENT}%")

        # Cap risk score at 100.0
        risk_score = min(100.0, risk_score)

        # Categorize Risk Level
        if risk_score <= 20:
            risk_level = "SAFE"
        elif risk_score <= 40:
            risk_level = "LOW RISK"
        elif risk_score <= 60:
            risk_level = "MEDIUM RISK"
        elif risk_score <= 80:
            risk_level = "HIGH RISK"
        else:
            risk_level = "BLOCKED"

        is_safe = (risk_score <= settings.MAX_TOKEN_RISK_SCORE) and sellable

        return {
            "safe": is_safe,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "reasons": rejection_reasons,
            "buy_tax": buy_tax,
            "sell_tax": sell_tax,
            "sellable": sellable
        }
