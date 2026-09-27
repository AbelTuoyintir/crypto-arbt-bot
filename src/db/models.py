from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from config.settings import settings

Base = declarative_base()

class Token(Base):
    __tablename__ = 'tokens'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False)
    name = Column(String(128), nullable=False)
    contract_address = Column(String(64), unique=True, nullable=False, index=True)
    chain_id = Column(Integer, nullable=False, default=56)
    decimals = Column(Integer, nullable=False, default=18)
    risk_score = Column(Float, nullable=False, default=0.0)
    buy_tax = Column(Float, nullable=False, default=0.0)
    sell_tax = Column(Float, nullable=False, default=0.0)
    liquidity = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default='active')  # active, blocked, warning
    last_checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Opportunity(Base):
    __tablename__ = 'opportunities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    base_token = Column(String(64), nullable=False)
    target_token = Column(String(64), nullable=False)
    dex = Column(String(64), nullable=False)
    initial_gat = Column(Float, nullable=False)
    expected_token = Column(Float, nullable=False)
    expected_final_gat = Column(Float, nullable=False)
    gas_cost = Column(Float, nullable=False, default=0.0)
    dex_fees = Column(Float, nullable=False, default=0.0)
    slippage = Column(Float, nullable=False, default=0.0)
    estimated_profit = Column(Float, nullable=False, default=0.0, index=True)
    profit_percentage = Column(Float, nullable=False, default=0.0)
    risk_score = Column(Float, nullable=False, default=0.0, index=True)
    status = Column(String(32), nullable=False, default='pending', index=True)  # pending, rejected, executed, failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class Trade(Base):
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, nullable=True)
    entry_transaction_hash = Column(String(128), nullable=True)
    exit_transaction_hash = Column(String(128), nullable=True)
    initial_gat = Column(Float, nullable=False)
    final_gat = Column(Float, nullable=False)
    gas_used = Column(Float, nullable=False, default=0.0)
    actual_profit = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, index=True)  # success, failed, reverted
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

# Database Engine & Session setup
engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
