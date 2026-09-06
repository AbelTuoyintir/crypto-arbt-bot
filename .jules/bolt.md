## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-09-06 - Pass Cached Quotes Across Simulation Pipeline

**Learning:** `MarketScanner`, `TokenSafetyAnalyzer`, and `TradeSimulator` were performing duplicate Leg 1 & Leg 2 quote calculations sequentially during every market scan (up to 6 `get_quote` calls per token pair). Storing quote results in the safety analysis dictionary allows downstream simulators to reuse pre-calculated quotes, cutting redundant DEX quote calls by 66.7%.
**Action:** Pass pre-computed quotes through intermediate stage result dictionaries in multi-stage analysis pipelines instead of re-fetching quotes at each stage.
