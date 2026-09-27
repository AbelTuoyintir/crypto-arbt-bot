## 2026-09-26 - EVM Address Format Validation in Token Safety Checks

**Vulnerability:** `TokenSafetyAnalyzer.analyze_token` used basic string non-empty checks on `token_address` instead of strict EVM address checksum/format verification, allowing malformed address strings to bypass format checks and return incorrect risk scores.
**Learning:** Checking string type and length is insufficient for Web3 operations; non-standard or malformed address strings can bypass preliminary validation and trigger unhandled errors or incorrect scoring in downstream DEX calls.
**Prevention:** Always validate target token and contract addresses with `Web3.is_address()` at the input boundary of safety analysis functions before performing DEX pool lookup or swap simulation.
