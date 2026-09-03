## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-08-25 - Use SQL Aggregations Instead of In-Memory Python Iteration on Query Sets

**Learning:** In Flask/SQLAlchemy dashboards backed by tables that accumulate high volumes of data over time (e.g. trade logs or arbitrage opportunities), fetching full model instances (`db.query(...).all()`) and aggregating in Python requires O(N) memory allocation and object instantiation time. Replacing in-memory loops with SQLAlchemy aggregate functions (`func.count`, `func.sum`, `func.coalesce`) processes calculations directly in the database engine in O(1) memory and executes significantly faster.
**Action:** Always push metrics aggregation and counts to the SQL engine level rather than pulling entire record sets into Python memory.
