# EDGEiQ Target 001 Schema Authority Decision V1

## Decision

Use `public/data/edgeiq_race_entry_fact_v1.csv` as the authoritative race-entry input for Target 001 and adapt its current canonical contract inside the Target 001 producer.

## Reason

Unit 002D scanned the repository and found no populated dataset matching the old Target 001 race-entry input contract. The current canonical race-entry fact is populated and governed, but uses the successor live/current schema.

## Guardrails

- Target 001 output schema is unchanged.
- No duplicate race-entry authority is created.
- No thresholds are weakened.
- No data is fabricated.
- The point-in-time rule remains `selected_rating_as_of_date < race_date`.
- Non-active or scratched entries are not emitted as declared governed snapshots.

## Adapter Mapping

- `race_id` comes from `canonical_race_id`.
- `runner_id` and `canonical_horse_id` come from `canonical_runner_id`.
- `canonical_horse_name` comes from `runner_name`.
- `race_entry_evidence_sha256` comes from `source_hash`.
- `race_entry_id` is deterministic from canonical race/runner/source identity.
