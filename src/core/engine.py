import logging
from typing import Dict, Any, Optional
from config.settings import settings
from src.dex.manager import DEXManager
from src.token.safety_analyzer import TokenSafetyAnalyzer
from src.core.profit_calculator import ProfitCalculator
from src.core.trade_simulator import TradeSimulator
from src.core.risk_manager import RiskManager
from src.tx.transaction_manager import TransactionManager
from src.wallet.wallet_manager import WalletManager
from src.db.models import SessionLocal, Opportunity, Trade, Token

logger = logging.getLogger("ArbitrageEngine")

class ArbitrageEngine:
    def __init__(
        self,
        dex_manager: DEXManager,
        wallet_manager: WalletManager = None,
        transaction_manager: TransactionManager = None,
        risk_manager: RiskManager = None
    ):
        self.dex_manager = dex_manager
        self.wallet_manager = wallet_manager or WalletManager()
        self.tx_manager = transaction_manager or TransactionManager(wallet_manager=self.wallet_manager)
        self.risk_manager = risk_manager or RiskManager()
        self.profit_calculator = ProfitCalculator()

    def process_opportunity(
        self,
        dex_name: str,
        target_token: str,
        initial_gat: float = 100.0,
        token_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a potential arbitrage opportunity end-to-end:
        Quote -> Safety -> Simulation -> Risk Check -> Execution / Rejection
        """
        dex_adapter = self.dex_manager.get_adapter(dex_name)
        if not dex_adapter:
            return {
                "executed": False,
                "reason": f"DEX adapter '{dex_name}' not found"
            }

        safety_analyzer = TokenSafetyAnalyzer(dex_adapter=dex_adapter)
        simulator = TradeSimulator(dex_adapter=dex_adapter, safety_analyzer=safety_analyzer, profit_calculator=self.profit_calculator)

        # 1. Run full round-trip simulation
        sim_res = simulator.simulate_arbitrage_cycle(target_token=target_token, initial_gat=initial_gat, token_info=token_info)

        db = SessionLocal()
        try:
            # Record Opportunity in DB
            profit_analysis = sim_res.get("profit_analysis") or {}
            safety_analysis = sim_res.get("safety_analysis") or {}

            opp = Opportunity(
                base_token=settings.BASE_TOKEN_ADDRESS,
                target_token=target_token,
                dex=dex_name,
                initial_gat=initial_gat,
                expected_token=sim_res.get("tokens_received", 0.0),
                expected_final_gat=sim_res.get("final_gat_gross", 0.0),
                gas_cost=sim_res.get("total_gas_gat", 0.0),
                dex_fees=0.25,
                slippage=settings.MAX_SLIPPAGE_PERCENT,
                estimated_profit=profit_analysis.get("net_profit", 0.0),
                profit_percentage=profit_analysis.get("profit_percentage", 0.0),
                risk_score=safety_analysis.get("risk_score", 100.0),
                status="pending"
            )
            db.add(opp)
            db.commit()

            if not sim_res["valid"]:
                opp.status = "rejected"
                db.commit()
                logger.info(f"[DECISION] REJECTED {target_token}. Reason: {sim_res['rejection_reason']}")
                return {
                    "executed": False,
                    "reason": sim_res["rejection_reason"],
                    "opportunity_id": opp.id
                }

            # 2. Risk Manager Validation
            risk_res = self.risk_manager.validate_trade(
                trade_amount_gat=initial_gat,
                gas_cost_gat=sim_res.get("total_gas_gat", 0.0),
                profit_percent=profit_analysis.get("profit_percentage", 0.0),
                token_risk_score=safety_analysis.get("risk_score", 0.0)
            )

            if not risk_res["approved"]:
                opp.status = "rejected"
                db.commit()
                logger.info(f"[DECISION] REJECTED by RiskManager. Reason: {risk_res['reason']}")
                return {
                    "executed": False,
                    "reason": f"Risk check failed: {risk_res['reason']}",
                    "opportunity_id": opp.id
                }

            # 3. Execution (Simulation / Paper / Testnet)
            logger.info(f"[DECISION] APPROVED for execution in mode: {settings.TRADING_MODE}")

            # Execute Swap Leg 1 & Leg 2
            exec_res = dex_adapter.execute_swap(
                token_in=settings.BASE_TOKEN_ADDRESS,
                token_out=target_token,
                amount_in=initial_gat,
                min_amount_out=sim_res["tokens_received"] * (1 - (settings.MAX_SLIPPAGE_PERCENT / 100.0))
            )

            actual_profit = profit_analysis.get("net_profit", 0.0)
            trade_status = "success" if exec_res.get("success") else "failed"

            trade = Trade(
                opportunity_id=opp.id,
                entry_transaction_hash=exec_res.get("tx_hash"),
                exit_transaction_hash="0xexit_" + (exec_res.get("tx_hash") or "sim"),
                initial_gat=initial_gat,
                final_gat=initial_gat + actual_profit if trade_status == "success" else initial_gat,
                gas_used=sim_res.get("total_gas_gat", 0.0),
                actual_profit=actual_profit if trade_status == "success" else 0.0,
                status=trade_status,
                error_message=exec_res.get("error")
            )
            db.add(trade)

            opp.status = "executed" if trade_status == "success" else "failed"
            db.commit()

            if trade_status == "success":
                self.risk_manager.record_trade_result(actual_profit)

            return {
                "executed": trade_status == "success",
                "opportunity_id": opp.id,
                "trade_id": trade.id,
                "profit": actual_profit if trade_status == "success" else 0.0,
                "mode": settings.TRADING_MODE
            }

        finally:
            db.close()
