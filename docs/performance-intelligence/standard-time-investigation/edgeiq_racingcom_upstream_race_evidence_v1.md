# EDGEIQ Racing.com Upstream Race Evidence V1

Generated UTC: `2026-07-22T07:54:55.436735+00:00`

## Governance boundary

- Read-only forensic diagnostic.
- No network access.
- No production builder executed.
- No V1 or V2 contract modified.
- No cache modified.

## Source population

- Calendar rows: **568**
- Completed-probe rows: **110**
- Combined source rows: **678**

## Race evidence origin

- `EXPLICIT_RACE_COLUMN`: **678**

## Date findings

- Future-dated source rows: **144**

Future-dated rows cannot constitute completed-race evidence.

## Meeting expansion findings

- Source meeting groups: **50**
- Exact race sequence `1?12`: **44**
- Future meetings with exact sequence `1?12`: **12**

## Source independence

- Canonical races appearing in both source files: **0**

Presence in both sources does not automatically prove independence if one source was generated from the other. This diagnostic records overlap only.

## Interpretation

An explicit race number in a source column is stronger than a race number recovered solely from a URL.

A future race page URL is scheduling or construction evidence, not completed-race or CSV-existence evidence.

The V2 foundation correctly avoided generating CSV URLs, but its source-admission classification must be tightened if upstream files contain constructed race pages.

## Decision

**UPSTREAM_RACE_EVIDENCE_REQUIRES_REMEDIATION**

## Artifacts

- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_upstream_race_evidence_ledger_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_upstream_meeting_expansion_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_upstream_source_overlap_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_upstream_source_columns_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_upstream_race_evidence_audit_v1.csv`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_upstream_race_evidence_v1.json`
- `docs/performance-intelligence/standard-time-investigation/edgeiq_racingcom_upstream_race_evidence_v1.md`
