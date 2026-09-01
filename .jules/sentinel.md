## 2026-03-30 - Prevent Plaintext Private Key Instance Variable Exposure
**Vulnerability:** `WalletManager` stored unencrypted raw private keys as an instance attribute (`self.private_key`), exposing secret credentials via `vars()`, `__dict__`, string formatting, or object inspection.
**Learning:** Initializing secrets as instance variables retains sensitive material in memory attached to long-lived objects beyond initialization.
**Prevention:** Use local variables or immediate scope processing for raw secrets during initialization, holding only necessary instantiated objects (like `Account`).
