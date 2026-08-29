## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-08-25 - Reuse Safety-Check DEX Quotes in Trade Simulation

**Learning:** `TokenSafetyAnalyzer` executes round-trip DEX quotes to verify sellability before trade simulation. Reusing these quotes in `TradeSimulator` when `initial_gat` matches `quote_initial_gat` reduces DEX quote calculations by 50% per simulation cycle while maintaining fallback safety if initial trade amounts differ.
**Action:** Pass pre-calculated quotes along pipeline stages with input validation metadata to avoid duplicate quote/RPC calls.
