## 2026-09-05 - EVM Token Address Validation in Safety Analyzer
**Vulnerability:** `TokenSafetyAnalyzer` lacked input validation for target token address strings, allowing malformed or invalid address formats to pass through to DEX adapter and Web3 contract calls.
**Learning:** Checking `Web3.is_address()` at the entry point of token analysis prevents unhandled Web3 errors and ensures malformed token addresses are blocked with maximum risk score before attempting RPC or swap quotes.
**Prevention:** Always validate EVM address formats with `Web3.is_address()` on untrusted token address inputs before invoking Web3/DEX operations, and ensure test suites use 40-character hex EVM addresses in mock token addresses.
