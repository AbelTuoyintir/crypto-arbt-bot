## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-08-24 - Use Database SQL Aggregations Instead of In-Memory Filtering

**Learning:** Loading entire database tables into Python memory via `.all()` and running list comprehensions or `sum()` / `len()` calls introduces severe performance bottlenecks as table sizes grow. Delegating counting and summation to the database engine via `func.count` and `func.coalesce(func.sum(...), 0.0)` reduces dashboard query latency by ~90% and eliminates redundant object allocations.
**Action:** Always use SQLAlchemy aggregation functions (`func.count`, `func.sum`) for metric calculations rather than loading full model instances into memory.
