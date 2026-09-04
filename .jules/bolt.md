## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-08-25 - Reuse Quote Calculations Across Sequential Analysis Steps

**Learning:** When performing token safety checks followed immediately by trade simulation, both steps execute identical round-trip DEX quotes (`get_quote`). Passing computed quote outputs (`tokens_out`, `final_gat_gross`) downstream in the analysis result dictionary allows `TradeSimulator` to reuse quote values directly, cutting external DEX/RPC quote invocations by 50% per simulation cycle.
**Action:** Share intermediate quote and computation results between pipeline stages (e.g. Safety -> Simulator) when inputs match, avoiding redundant external RPC queries.
