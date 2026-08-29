## 2026-03-31 - Avoid storing plaintext private keys on class instances
**Vulnerability:** `WalletManager.__init__` stored raw plaintext private keys in `self.private_key`, exposing sensitive wallet credentials in instance memory, `__dict__`, `vars()`, and potential `repr()` or error dumps.
**Learning:** `Account.from_key()` only needs the key during initialization to construct the `Account` instance. Retaining the raw string key on `self` is unnecessary.
**Prevention:** Process private keys in local variable scope during `__init__` and do not store raw key strings as instance attributes.
