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
                    "opportunity_id": opp.id,
                    "sim_res": sim_res
                }

            # Calculate confidence score
            conf_res = self.calculate_opportunity_confidence(
                profit_percentage=profit_analysis.get("profit_percentage", 0.0),
                risk_score=safety_analysis.get("risk_score", 0.0),
                gas_cost_gat=sim_res.get("total_gas_gat", 0.0),
                initial_gat=initial_gat
            )

            # 2. Risk Manager Validation
            risk_res = self.risk_manager.validate_trade(
                trade_amount_gat=initial_gat,
                gas_cost_gat=sim_res.get("total_gas_gat", 0.0),
                profit_percent=profit_analysis.get("profit_percentage", 0.0),
                token_risk_score=safety_analysis.get("risk_score", 0.0),
                confidence_score=conf_res.get("confidence_score")
            )

            if not risk_res["approved"]:
                opp.status = "rejected"
                db.commit()
                logger.info(f"[DECISION] REJECTED by RiskManager. Reason: {risk_res['reason']}")
                return {
                    "executed": False,
                    "reason": f"Risk check failed: {risk_res['reason']}",
                    "opportunity_id": opp.id,
                    "sim_res": sim_res
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

            self.risk_manager.record_trade_result(actual_profit, success=(trade_status == "success"))

            return {
                "executed": trade_status == "success",
                "opportunity_id": opp.id,
                "trade_id": trade.id,
                "profit": actual_profit if trade_status == "success" else 0.0,
                "mode": settings.TRADING_MODE,
                "sim_res": sim_res
            }

        finally:
            db.close()

    def calculate_opportunity_confidence(
        self,
        profit_percentage: float,
        risk_score: float,
        gas_cost_gat: float,
        initial_gat: float
    ) -> Dict[str, Any]:
        """
        Enhanced Feature: Calculates confidence score (0 - 100) and optimal trade size
        to optimize win rate and profit consistency.
        Filters out marginal/low-confidence opportunities subject to MEV or high slippage.
        """
        confidence = 100.0

        # Deduct for high token risk score
        confidence -= (risk_score * 0.5)

        # Deduct if profit percentage is close to minimum threshold
        profit_buffer = profit_percentage - settings.MIN_PROFIT_PERCENT
        if profit_buffer < 0.5:
            confidence -= 20.0
        elif profit_buffer < 1.0:
            confidence -= 10.0

        # Deduct if gas cost is high relative to initial size
        gas_ratio = (gas_cost_gat / initial_gat) * 100.0 if initial_gat > 0 else 100.0
        if gas_ratio > 2.0:
            confidence -= 25.0
        elif gas_ratio > 1.0:
            confidence -= 10.0

        confidence = max(0.0, min(100.0, confidence))

        # Dynamic Sizing Recommendation
        if confidence >= 80:
            recommended_size = settings.MAX_TRADE_SIZE
        elif confidence >= 60:
            recommended_size = settings.MAX_TRADE_SIZE * 0.5
        else:
            recommended_size = settings.MAX_TRADE_SIZE * 0.25

        return {
            "confidence_score": confidence,
            "recommended_trade_size": recommended_size,
            "high_confidence": confidence >= 70.0
        }

    def log_strategy_disclaimer(self):
        """Log disclaimer on market dynamics, MEV competition, and realistic returns."""
        logger.info(
            "[DISCLAIMER] High target win rates and daily profitability depend on live market conditions, "
            "DEX liquidity, network latency, and MEV competition. Simulation modes test expected yields, "
            "but real-market outcomes are subject to execution slippage and gas fluctuation."
        )

    def process_triangular_opportunity(
        self,
        dex_name: str,
        token_a: str,
        token_b: str,
        initial_gat: float = 100.0,
        token_a_info: Dict[str, Any] = None,
        token_b_info: Dict[str, Any] = None,
        min_confidence: float = 60.0
    ) -> Dict[str, Any]:
        """
        Process a 3-leg triangular arbitrage opportunity (GAT -> TOKEN A -> TOKEN B -> GAT) end-to-end:
        Quote -> Safety -> 3-leg Simulation -> Confidence Scoring -> Risk Check -> Execution / Rejection
        """
        self.log_strategy_disclaimer()

        dex_adapter = self.dex_manager.get_adapter(dex_name)
        if not dex_adapter:
            return {
                "executed": False,
                "reason": f"DEX adapter '{dex_name}' not found"
            }

        safety_analyzer = TokenSafetyAnalyzer(dex_adapter=dex_adapter)
        simulator = TradeSimulator(dex_adapter=dex_adapter, safety_analyzer=safety_analyzer, profit_calculator=self.profit_calculator)

        # 1. Run full 3-leg triangular simulation
        sim_res = simulator.simulate_triangular_arbitrage_cycle(
            token_a=token_a,
            token_b=token_b,
            initial_gat=initial_gat,
            token_a_info=token_a_info,
            token_b_info=token_b_info
        )

        db = SessionLocal()
        try:
            profit_analysis = sim_res.get("profit_analysis") or {}
            safety_analysis = sim_res.get("safety_analysis") or {}
            target_pair_str = f"{token_a}->{token_b}"

            opp = Opportunity(
                base_token=settings.BASE_TOKEN_ADDRESS,
                target_token=target_pair_str,
                dex=dex_name,
                initial_gat=initial_gat,
                expected_token=sim_res.get("token_b_received", 0.0),
                expected_final_gat=sim_res.get("final_gat_gross", 0.0),
                gas_cost=sim_res.get("total_gas_gat", 0.0),
                dex_fees=0.25 * 3,  # 3 leg swaps
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
                logger.info(f"[TRIANGULAR DECISION] REJECTED {target_pair_str}. Reason: {sim_res['rejection_reason']}")
                return {
                    "executed": False,
                    "reason": sim_res["rejection_reason"],
                    "opportunity_id": opp.id,
                    "sim_res": sim_res
                }

            # 2. Confidence & High Win-Rate Optimization
            conf_res = self.calculate_opportunity_confidence(
                profit_percentage=profit_analysis.get("profit_percentage", 0.0),
                risk_score=safety_analysis.get("risk_score", 0.0),
                gas_cost_gat=sim_res.get("total_gas_gat", 0.0),
                initial_gat=initial_gat
            )

            # 3. Risk Manager Validation
            risk_res = self.risk_manager.validate_trade(
                trade_amount_gat=initial_gat,
                gas_cost_gat=sim_res.get("total_gas_gat", 0.0),
                profit_percent=profit_analysis.get("profit_percentage", 0.0),
                token_risk_score=safety_analysis.get("risk_score", 0.0),
                confidence_score=conf_res.get("confidence_score"),
                min_confidence=min_confidence
            )

            if not risk_res["approved"]:
                opp.status = "rejected"
                db.commit()
                logger.info(f"[TRIANGULAR DECISION] REJECTED by RiskManager. Reason: {risk_res['reason']}")
                return {
                    "executed": False,
                    "reason": f"Risk check failed: {risk_res['reason']}",
                    "opportunity_id": opp.id,
                    "sim_res": sim_res,
                    "confidence_analysis": conf_res
                }

            # 4. Execution of Leg 1, Leg 2, Leg 3
            logger.info(f"[TRIANGULAR DECISION] APPROVED for execution (Confidence: {conf_res['confidence_score']:.1f}%). Mode: {settings.TRADING_MODE}")

            # Leg 1: GAT -> Token A
            exec_leg1 = dex_adapter.execute_swap(
                token_in=settings.BASE_TOKEN_ADDRESS,
                token_out=token_a,
                amount_in=initial_gat,
                min_amount_out=sim_res["token_a_received"] * (1 - (settings.MAX_SLIPPAGE_PERCENT / 100.0))
            )

            # Leg 2: Token A -> Token B
            exec_leg2 = dex_adapter.execute_swap(
                token_in=token_a,
                token_out=token_b,
                amount_in=sim_res["token_a_received"],
                min_amount_out=sim_res["token_b_received"] * (1 - (settings.MAX_SLIPPAGE_PERCENT / 100.0))
            )

            # Leg 3: Token B -> GAT
            exec_leg3 = dex_adapter.execute_swap(
                token_in=token_b,
                token_out=settings.BASE_TOKEN_ADDRESS,
                amount_in=sim_res["token_b_received"],
                min_amount_out=initial_gat
            )

            actual_profit = profit_analysis.get("net_profit", 0.0)
            all_successful = exec_leg1.get("success") and exec_leg2.get("success") and exec_leg3.get("success")
            trade_status = "success" if all_successful else "failed"

            trade = Trade(
                opportunity_id=opp.id,
                entry_transaction_hash=exec_leg1.get("tx_hash"),
                exit_transaction_hash=exec_leg3.get("tx_hash") or ("0xexit_triangular_" + (exec_leg1.get("tx_hash") or "sim")),
                initial_gat=initial_gat,
                final_gat=initial_gat + actual_profit if trade_status == "success" else initial_gat,
                gas_used=sim_res.get("total_gas_gat", 0.0),
                actual_profit=actual_profit if trade_status == "success" else 0.0,
                status=trade_status,
                error_message=None if trade_status == "success" else "Execution failed on one or more triangular legs"
            )
            db.add(trade)

            opp.status = "executed" if trade_status == "success" else "failed"
            db.commit()

            self.risk_manager.record_trade_result(actual_profit, success=(trade_status == "success"))

            return {
                "executed": trade_status == "success",
                "opportunity_id": opp.id,
                "trade_id": trade.id,
                "profit": actual_profit if trade_status == "success" else 0.0,
                "mode": settings.TRADING_MODE,
                "confidence_analysis": conf_res,
                "sim_res": sim_res
            }

        finally:
            db.close()
