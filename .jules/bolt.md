## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-09-02 - Reuse DEX Quotes Between Token Safety Check and Trade Simulation

**Learning:** During arbitrage scanning, `TokenSafetyAnalyzer.analyze_token()` already performs a buy/sell quote test on DEX adapters. `TradeSimulator` previously executed 2 additional `get_quote()` calls for the exact same pair and amount. Reusing cached quote outputs from the safety check when `test_amount_gat == initial_gat` cuts total quote calls per scan cycle in half (from 4 to 2), significantly reducing simulation latency while preserving strict quote accuracy.
**Action:** Always pass through and reuse intermediate calculation outputs across sequential pipeline stages when input parameters match.
