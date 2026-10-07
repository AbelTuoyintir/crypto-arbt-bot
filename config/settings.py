import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

class Settings(BaseModel):
    # Base Token Configuration
    BASE_TOKEN_NAME: str = os.getenv("BASE_TOKEN_NAME", "Global Access Tech")
    BASE_TOKEN_SYMBOL: str = os.getenv("BASE_TOKEN_SYMBOL", "GAT")
    BASE_TOKEN_ADDRESS: str = os.getenv("BASE_TOKEN_ADDRESS", "0x1111111111111111111111111111111111111111")
    CHAIN_ID: int = int(os.getenv("CHAIN_ID", "56"))
    RPC_URL: str = os.getenv("RPC_URL", "https://bsc-dataseed.binance.org/")

    # Wallet
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    KEYSTORE_PATH: str = os.getenv("KEYSTORE_PATH", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///gat_arbitrage.db")

    # Trading Controls
    TRADING_MODE: str = os.getenv("TRADING_MODE", "simulation").lower()  # simulation, paper, testnet
    REAL_MONEY: bool = os.getenv("REAL_MONEY", "false").lower() in ("true", "1", "t")
    ENABLE_LIVE_TRADING: bool = os.getenv("ENABLE_LIVE_TRADING", "false").lower() in ("true", "1", "t")
    EMERGENCY_KILL_SWITCH: bool = os.getenv("EMERGENCY_KILL_SWITCH", "false").lower() in ("true", "1", "t")

    # Profit & Risk Parameters
    MIN_PROFIT_PERCENT: float = float(os.getenv("MIN_PROFIT_PERCENT", "1.0"))
    MAX_SLIPPAGE_PERCENT: float = float(os.getenv("MAX_SLIPPAGE_PERCENT", "0.5"))
    MAX_BUY_TAX_PERCENT: float = float(os.getenv("MAX_BUY_TAX_PERCENT", "2.0"))
    MAX_SELL_TAX_PERCENT: float = float(os.getenv("MAX_SELL_TAX_PERCENT", "2.0"))
    MIN_LIQUIDITY: float = float(os.getenv("MIN_LIQUIDITY", "10000.0"))
    MAX_TRADE_SIZE: float = float(os.getenv("MAX_TRADE_SIZE", "100.0"))
    MAX_DAILY_LOSS: float = float(os.getenv("MAX_DAILY_LOSS", "50.0"))
    MAX_DAILY_TRADES: int = int(os.getenv("MAX_DAILY_TRADES", "50"))
    MAX_GAS_COST: float = float(os.getenv("MAX_GAS_COST", "0.01"))
    MAX_TOKEN_RISK_SCORE: float = float(os.getenv("MAX_TOKEN_RISK_SCORE", "40.0"))

    # High Win-Rate & Daily Profit Rate Target Parameters
    HIGH_WIN_RATE_MODE: bool = os.getenv("HIGH_WIN_RATE_MODE", "true").lower() in ("true", "1", "t")
    TARGET_WIN_RATE_PERCENT: float = float(os.getenv("TARGET_WIN_RATE_PERCENT", "95.0"))
    MIN_CONFIDENCE_SCORE: float = float(os.getenv("MIN_CONFIDENCE_SCORE", "95.0"))
    TARGET_DAILY_PROFIT_PERCENT: float = float(os.getenv("TARGET_DAILY_PROFIT_PERCENT", "5.0"))

settings = Settings()
