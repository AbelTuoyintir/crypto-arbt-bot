## 2026-08-24 - Cache Gas Price RPC Calls in DEX Adapter

**Learning:** Web3 RPC calls like `w3.eth.gas_price` introduce ~35-200ms of synchronous network latency per invocation. When called multiple times during each token scan/simulation cycle, this significantly slows down market scanning and trade analysis. Short-TTL (e.g. 5s) caching of network gas prices drastically reduces loop overhead while maintaining accurate gas estimation.
**Action:** Always cache high-frequency read-only RPC calls (like gas price or block numbers) with a configurable TTL when doing batch calculations or market scanning.

## 2026-08-24 - Avoid Duplicate DEX Quotes in Safety & Simulation Pipeline

**Learning:** `TokenSafetyAnalyzer` and `TradeSimulator` sequential phases were executing duplicate DEX adapter quotes (`Leg 1` and `Leg 2`) for identical token pairs and test amounts, doubling execution time per trade cycle. Validating `test_amount_gat == initial_gat` allows reusing pre-calculated quotes safely while preserving exact profitability logic and price impact accuracy.
**Action:** Always pass through and reuse intermediate calculation results (like quotes and gas estimations) across pipeline stages when input parameters match.
## 2026-09-26 - Cache Immutable ERC20 Metadata in Token Utilities

**Learning:** Web3 contract calls to fetch token `name()`, `symbol()`, and `decimals()` incur 3 synchronous HTTP RPC calls per token lookup (~100-300ms network latency). Because ERC20 token metadata is immutable, caching token metadata in-memory per contract checksum address completely eliminates redundant network calls during scanning loops.
**Action:** Always cache immutable token metadata per checksum address and return copies of cached dictionaries to avoid mutation side-effects.

## 2026-10-15 - Delegate MarketScanner Directly to Engine Simulation Pipeline

**Learning:** `MarketScanner` was making manual preliminary DEX `get_quote` and `estimate_gas` calls prior to passing opportunities to `ArbitrageEngine.process_opportunity`. Because the engine's `TradeSimulator` performs its own simulation cycle, this doubled the total DEX quote calls (4 quote calls + 3 gas calls per token pair scan). Having `process_opportunity` return `sim_res` and delegating directly in `MarketScanner` eliminates all redundant preliminary DEX quotes and cuts scan overhead by ~50%.
**Action:** Always structure scanner loops to delegate simulation/quoting to the downstream pipeline engine once and reuse returned simulation results for logging and analysis.

## 2026-11-18 - Use Direct SQL Aggregations in Dashboard API Metrics

**Learning:** Fetching all ORM records (`db.query(Model).all()`) to sum values in Python causes O(N) memory allocation and ORM object instantiation per request. Using SQL-level aggregation (`func.coalesce(func.sum(...), 0.0)`) offloads computation to the database engine, returning a single scalar float in O(1) memory.
**Action:** Always prefer SQL scalar aggregations (`func.sum()`, `func.count()`) over Python in-memory iterations when computing endpoint metrics or total stats.
