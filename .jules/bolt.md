## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-09-26 - Cache Immutable ERC20 Metadata in Token Utilities

**Learning:** Web3 contract calls to fetch token `name()`, `symbol()`, and `decimals()` incur 3 synchronous HTTP RPC calls per token lookup (~100-300ms network latency). Because ERC20 token metadata is immutable, caching token metadata in-memory per contract checksum address completely eliminates redundant network calls during scanning loops.
**Action:** Always cache immutable token metadata per checksum address and return copies of cached dictionaries to avoid mutation side-effects.
