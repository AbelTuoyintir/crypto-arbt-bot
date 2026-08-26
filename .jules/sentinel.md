## 2026-08-26 - Flask Dashboard HTML Template String Casting & Test Cleanliness
**Vulnerability:** Slicing target_token in Jinja2 template formatting could fail on non-string values or render un-escaped if autoescaping was disabled, and DB testing against the default SQLite database file risked committing modified binary state.
**Learning:** In Flask HTML templates, explicit string conversion (`(opp.target_token|string)`) ensures robust slicing regardless of input data types, and tests creating temporary database objects must clean them up in `finally` blocks and restore original database binary files.
**Prevention:** Use defensive string casting in template expressions and ensure DB cleanup / rollback in test teardowns so local SQLite databases remain pristine.
