# GAT-Based Multi-Token Arbitrage Trading Bot

Production-quality **crypto arbitrage trading bot** whose base settlement asset is **Global Access Tech (GAT)**.

The bot operates on the fundamental trading cycle:
```text
GAT → Token A → GAT
```

Executing trades **only** when the estimated final GAT balance exceeds the initial GAT balance after accounting for ALL costs and risks (gas, DEX fees, buy/sell taxes, slippage, price impact).

---

## Key Features & Safety Mechanisms

### 1. Capital Preservation & Mandatory Round-Trip Simulation
- **Never assumes a token can be sold back into GAT.**
- Before considering any trade, the bot executes a mandatory complete two-leg simulation (`GAT -> Token A` followed by `Token A -> GAT`).
- If the sell leg fails, reverts, or returns zero GAT, the token is instantly rejected.

### 2. Token Risk Engine (`TokenSafetyAnalyzer`)
Categorizes token safety into 5 risk tiers:
- **0 - 20**: SAFE
- **21 - 40**: LOW RISK
- **41 - 60**: MEDIUM RISK
- **61 - 80**: HIGH RISK
- **81 - 100**: BLOCKED

Rejects tokens with honeypot behavior, excessive buy/sell taxes, trading pauses, transfer restrictions, blacklists/whitelists, or low liquidity/volume.

### 3. Modular DEX Adapters & Manager
Supports multiple decentralized exchanges through extensible DEX adapters providing:
- `get_quote()`
- `estimate_output()`
- `estimate_gas()`
- `simulate_swap()`
- `execute_swap()`
- `get_liquidity()`
- `get_pool_price()`

Includes `PancakeSwapAdapter` for BSC and `DEXManager` to rank best quotes across DEXs.

### 4. Safety Controls & Mainnet Protection
- Default mode: `TRADING_MODE=simulation`, `REAL_MONEY=false`, `ENABLE_LIVE_TRADING=false`.
- Configurable risk parameters: `MIN_PROFIT_PERCENT`, `MAX_SLIPPAGE_PERCENT`, `MAX_BUY_TAX_PERCENT`, `MAX_SELL_TAX_PERCENT`, `MAX_TRADE_SIZE`, `MAX_DAILY_LOSS`, `MAX_DAILY_TRADES`, `MAX_GAS_COST`.
- Includes an emergency **Kill Switch** that halts all trading if risk limits are violated.

### 5. Atomic Execution Principles
When deployed with smart contract integration on EVM chains, the complete cycle is performed atomically within a single transaction contract:
```text
GAT → Swap → TOKEN → Swap → GAT
```
If any step fails or output falls below minimum profit, the contract reverts the entire transaction. Note: atomic contracts do not eliminate all external risks (e.g., oracle failure, token tax changes, network congestion).

---

## Directory Architecture

```text
gat-arbitrage-bot/
├── src/
│   ├── core/
│   │   ├── engine.py
│   │   ├── profit_calculator.py
│   │   ├── trade_simulator.py
│   │   └── risk_manager.py
│   ├── dex/
│   │   ├── base_adapter.py
│   │   ├── pancakeswap_adapter.py
│   │   └── manager.py
│   ├── token/
│   │   ├── safety_analyzer.py
│   │   └── token_utils.py
│   ├── wallet/
│   │   └── wallet_manager.py
│   ├── db/
│   │   ├── models.py
│   │   └── migrations/
│   ├── scanner/
│   │   └── market_scanner.py
│   ├── tx/
│   │   └── transaction_manager.py
│   └── dashboard/
│       └── app.py
├── config/
│   ├── settings.py
│   └── .env.example
├── tests/
│   ├── test_profit.py
│   ├── test_safety.py
│   ├── test_trading.py
│   └── test_risk.py
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Getting Started

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Configuration

Copy `config/.env.example` to `config/.env` and adjust parameters:

```env
BASE_TOKEN_NAME=Global Access Tech
BASE_TOKEN_SYMBOL=GAT
BASE_TOKEN_ADDRESS=0x1111111111111111111111111111111111111111
RPC_URL=https://bsc-dataseed.binance.org/

TRADING_MODE=simulation
REAL_MONEY=false
ENABLE_LIVE_TRADING=false

MIN_PROFIT_PERCENT=1.0
MAX_SLIPPAGE_PERCENT=0.5
MAX_BUY_TAX_PERCENT=2.0
MAX_SELL_TAX_PERCENT=2.0
MIN_LIQUIDITY=10000.0
```

### 3. Running Web Dashboard

```bash
python src/dashboard/app.py
```
Navigate to `http://localhost:5000` to view real-time portfolio, arbitrage, profit, and risk metrics.

### 4. Running Tests

```bash
pytest
```

### 5. Running with Docker Compose

```bash
docker-compose up --build
```
