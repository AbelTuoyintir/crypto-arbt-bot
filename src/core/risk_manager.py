import logging
from typing import Dict, Any
from config.settings import settings

logger = logging.getLogger("RiskManager")

class RiskManager:
    def __init__(self):
        self.daily_trades = 0
        self.daily_successful_trades = 0
        self.daily_loss = 0.0
        self.kill_switch_active = settings.EMERGENCY_KILL_SWITCH

    def trigger_kill_switch(self, reason: str = "Manual trigger"):
        self.kill_switch_active = True
        logger.critical(f"EMERGENCY KILL SWITCH TRIGGERED! Reason: {reason}")

    def reset_kill_switch(self):
        self.kill_switch_active = False
        logger.info("Kill switch reset. Normal operation resumed.")

    def record_trade_result(self, profit_or_loss_gat: float, success: bool = True):
        self.daily_trades += 1
        if success and profit_or_loss_gat > 0:
            self.daily_successful_trades += 1
        if profit_or_loss_gat < 0 or not success:
            loss_amount = abs(profit_or_loss_gat) if profit_or_loss_gat < 0 else 0.0
            self.daily_loss += loss_amount
            if self.daily_loss >= settings.MAX_DAILY_LOSS:
                self.trigger_kill_switch(f"Daily loss limit exceeded ({self.daily_loss} >= {settings.MAX_DAILY_LOSS})")

    def get_daily_win_rate(self) -> float:
        """Returns current daily win rate percentage (0.0 to 100.0). Returns 100.0 if no trades yet."""
        if self.daily_trades == 0:
            return 100.0
        return (self.daily_successful_trades / self.daily_trades) * 100.0

    def validate_trade(
        self,
        trade_amount_gat: float,
        gas_cost_gat: float,
        profit_percent: float,
        token_risk_score: float,
        confidence_score: float = None,
        min_confidence: float = 60.0
    ) -> Dict[str, Any]:
        """Validate if a trade meets all risk management rules before execution."""

        if confidence_score is not None and confidence_score < min_confidence:
            return {
                "approved": False,
                "reason": f"Confidence score ({confidence_score:.1f}) below required minimum ({min_confidence:.1f}) for target win rate"
            }

        if self.kill_switch_active or settings.EMERGENCY_KILL_SWITCH:
            return {
                "approved": False,
                "reason": "Emergency Kill Switch is ACTIVE. Trading halted."
            }

        if self.daily_trades >= settings.MAX_DAILY_TRADES:
            return {
                "approved": False,
                "reason": f"Max daily trades limit reached ({self.daily_trades} >= {settings.MAX_DAILY_TRADES})"
            }

        if self.daily_loss >= settings.MAX_DAILY_LOSS:
            return {
                "approved": False,
                "reason": f"Max daily loss limit exceeded ({self.daily_loss} >= {settings.MAX_DAILY_LOSS})"
            }

        if trade_amount_gat > settings.MAX_TRADE_SIZE:
            return {
                "approved": False,
                "reason": f"Trade size exceeds max limit ({trade_amount_gat} > {settings.MAX_TRADE_SIZE})"
            }

        if gas_cost_gat > settings.MAX_GAS_COST:
            return {
                "approved": False,
                "reason": f"Gas cost exceeds max allowed ({gas_cost_gat} > {settings.MAX_GAS_COST})"
            }

        if profit_percent < settings.MIN_PROFIT_PERCENT:
            return {
                "approved": False,
                "reason": f"Profit percentage below min threshold ({profit_percent:.2f}% < {settings.MIN_PROFIT_PERCENT}%)"
            }

        if token_risk_score > settings.MAX_TOKEN_RISK_SCORE:
            return {
                "approved": False,
                "reason": f"Token risk score too high ({token_risk_score} > {settings.MAX_TOKEN_RISK_SCORE})"
            }

        # Check high win-rate / confidence threshold if enabled
        if settings.HIGH_WIN_RATE_MODE and confidence_score is not None:
            required_confidence = settings.MIN_CONFIDENCE_SCORE
            # If current daily win rate falls below target (95%), increase strictness
            if self.get_daily_win_rate() < settings.TARGET_WIN_RATE_PERCENT:
                required_confidence = max(required_confidence, 98.0)

            if confidence_score < required_confidence:
                return {
                    "approved": False,
                    "reason": f"Confidence score below target for high win-rate mode ({confidence_score:.1f}% < {required_confidence:.1f}%)"
                }

        return {
            "approved": True,
            "reason": "Trade meets all risk requirements"
        }
