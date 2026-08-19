# EDGEiQ Duplicate Performance Evidence Governance V0.1

## Permanent rule

A repeated `performance_id` does not mean source evidence may be deleted.

Every source row remains recorded in the performance-source-evidence membership table.

## Exact duplicate evidence

When all identity fields agree:

- one deterministic canonical performance row is materialised
- the lowest source-row number becomes the canonical representative
- all source rows remain linked to the canonical performance
- the duplicate resolution state is recorded

## Source conflict

When identity fields disagree:

- no conflicting performance is silently materialised
- all conflicting field values are written to the conflict audit
- the performance remains blocked until governed resolution

## Product rule

Application services consume the unique canonical performance table.

Audits and lineage services retain access to every original source-evidence row.
