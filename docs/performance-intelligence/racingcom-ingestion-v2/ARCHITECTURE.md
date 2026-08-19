# Architecture

The governed chain is split into nine units:

1. Calendar producer forensic trace.
2. Meeting discovery.
3. Race discovery.
4. CSV admission and acquisition queue.
5. Speed-page discovery.
6. CSV acquisition and cache ledger.
7. Parser isolation.
8. Canonical warehouse production.
9. E2E regression and migration decision.

The core rule is simple: no race URL, race number, speed-data URL, or CSV URL is invented. Every downstream record carries provenance back to source evidence.
