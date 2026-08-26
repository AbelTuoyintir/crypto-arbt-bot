## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-08-25 - Reuse Quote Calculations Across Token Validation and Trade Simulation

**Learning:** When trade simulation performs token safety checks (`TokenSafetyAnalyzer`) prior to trade evaluation, DEX adapter quotes are calculated for both swap legs during sellability verification. Re-requesting identical quotes in `TradeSimulator` doubles quote calculation and network/contract call overhead. Passing pre-calculated quotes forward and validating that the input amount (`initial_gat == quote_amount_gat`) matches before reuse eliminates redundant calls while preserving calculation safety.
**Action:** Always forward pre-calculated DEX quotes along with their associated input parameters so downstream pipeline stages can safely reuse them without duplicate network or math queries.
