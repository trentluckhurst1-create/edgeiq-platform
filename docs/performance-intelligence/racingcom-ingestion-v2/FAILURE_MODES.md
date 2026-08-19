# Failure Modes

Known failure modes are explicitly classified:

- Legacy fixed 1-12 race expansion: blocked.
- Constructed CSV URL: blocked.
- Future historical acquisition: blocked.
- Speed page without CSV link: retained as `NO_CSV_LINK_IN_PAGE`.
- Unsupported race identity: rejected as `REJECTED_NO_SPEED_DATA_EVIDENCE`.
- HTML/non-CSV download: rejected by acquisition validation.

Partial failures must not corrupt completed warehouse output.
