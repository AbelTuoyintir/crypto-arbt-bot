## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-08-24 - Avoid Duplicate DEX Quotes in Safety & Simulation Pipeline

**Learning:** `TokenSafetyAnalyzer` and `TradeSimulator` sequential phases were executing duplicate DEX adapter quotes (`Leg 1` and `Leg 2`) for identical token pairs and test amounts, doubling execution time per trade cycle. Validating `test_amount_gat == initial_gat` allows reusing pre-calculated quotes safely while preserving exact profitability logic and price impact accuracy.
**Action:** Always pass through and reuse intermediate calculation results (like quotes and gas estimations) across pipeline stages when input parameters match.
