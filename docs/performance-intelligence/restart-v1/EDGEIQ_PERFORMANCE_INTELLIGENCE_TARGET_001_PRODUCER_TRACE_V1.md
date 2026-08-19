# EDGEIQ Performance Intelligence Target 001 Producer Trace V1

## Verdict

**PASS**

## Target

`public/data/edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv`

- CSV status: `HEADER_ONLY`
- Data rows: `0`
- Columns: `30`

## Strongest Producer Candidate

`scripts/build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py`

- Producer score: `85`
- Exact target matches: `1`
- Matching lines: `26`

## Reference Summary

- Repository text files scanned: `36091`
- Exact references found: `67`
- Producer candidates: `3`
- Orchestrators: `0`
- Audits/verifiers: `4`
- Contracts/schemas: `0`
- Runtime/React references: `0`

## Producer Candidates

| Rank | File | Type | Score | Matches |
|---:|---|---|---:|---:|
| 1 | `scripts/build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py` | BUILDER_CANDIDATE | 85 | 1 |
| 2 | `scripts/build_edgeiq_race_entry_performance_context_fact_v1.py` | BUILDER_CANDIDATE | 65 | 1 |
| 3 | `scripts/build_edgeiq_performance_intelligence_restart_baseline_v1.py` | BUILDER_CANDIDATE | 50 | 1 |

## Possible Direct Dataset Dependencies

| Referenced path | Role | Exists | CSV status | Rows |
|---|---|---:|---|---:|
| `edgeiq_horse_performance_rating_fact_v1.csv` | POSSIBLE_DIRECT_DEPENDENCY | TRUE | POPULATED | 24 |
| `edgeiq_race_entry_fact_v1.csv` | POSSIBLE_DIRECT_DEPENDENCY | TRUE | POPULATED | 204 |
| `edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv` | TARGET_OUTPUT | TRUE | HEADER_ONLY | 0 |

## Governed Finding

The strongest producing script has been identified using exact filename references, file role and output-writing indicators.

This unit does not claim that any possible dataset reference is definitively an input until Unit 002C validates how the producer opens and consumes it.

## Governed Next Action

**TRACE_TARGET_001_DIRECT_INPUT_ROW_COUNTS**

Inspect the strongest producer candidate and measure each directly consumed upstream input. Stop at the first populated-to-zero transition.

No repair is authorised.
