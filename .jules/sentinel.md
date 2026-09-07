## 2026-08-24 - Validate EVM Address Format in TokenSafetyAnalyzer

**Vulnerability:** Target token addresses passed to `TokenSafetyAnalyzer.analyze_token` were not validated with `Web3.is_address`, allowing malformed address strings to propagate to DEX adapters and Web3 contract calls.
**Learning:** `TokenSafetyAnalyzer` is the primary entry point for token risk assessment. Validating EVM address formats early using `Web3.is_address` prevents unexpected exceptions down the stack. When adding `Web3.is_address` validation, all test mocks must use valid 40-character EVM addresses (e.g. `0x0000000000000000000000000000000000000001`).
**Prevention:** Always validate EVM contract addresses at the outer boundary before invoking contract calls or DEX queries.
