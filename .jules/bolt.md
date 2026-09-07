## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-09-07 - Reuse DEX Quotes Between Safety Check and Trade Simulator

**Learning:** `TokenSafetyAnalyzer` fetches DEX quotes for Leg 1 and Leg 2 during its sellability test. Immediately after, `TradeSimulator` was executing the exact same `get_quote` calls for the same token and initial amount. Forwarding quote results in `safety_res` and reusing them when `initial_gat == quote_amount_in` cuts DEX adapter / RPC quote calls per trade simulation cycle in half (from 4 calls down to 2).
**Action:** Reuse quotes and simulation results across workflow stages when input parameters (`initial_gat`, token addresses) match, eliminating duplicate RPC/network round-trips.
