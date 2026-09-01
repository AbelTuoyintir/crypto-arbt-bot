## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-08-25 - Reuse Round-Trip Safety Analysis Quotes in Trade Simulation

**Learning:** During token analysis and trade simulation cycles, `TokenSafetyAnalyzer` and `TradeSimulator` sequentially execute identical `GAT -> TOKEN` and `TOKEN -> GAT` quote calculations. When reusing quotes across pipeline stages, always validate that input parameters (e.g., `initial_gat` trade amount) match exact test conditions to prevent invalid simulation results.
**Action:** Include calculated quotes and their input parameters in step results so downstream pipeline stages can reuse quotes when arguments match, falling back to fresh queries when they differ.
