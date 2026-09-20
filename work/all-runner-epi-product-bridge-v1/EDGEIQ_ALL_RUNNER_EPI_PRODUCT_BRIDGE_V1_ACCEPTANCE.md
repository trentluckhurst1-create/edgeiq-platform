# EDGEiQ All-Runner EPI Product Bridge V1 Acceptance

## Result

- Status: PASS
- Form Guide historical slots: 2044
- Certified direct EPI matches: 958
- Certified deterministic representation matches: 84
- Total historicalEpi populated in candidate: 1042
- Governed blanks: 1002
- Final classification sum: 2044

## Governance

- Certified EPI artifact was read-only and hash-checked against the certified SHA256.
- Warehouse, HPR, and production Form Guide artifacts were not modified.
- Market data was not used as an EPI input.
- No replacement EPI values were calculated.
- No fuzzy horse matching, date tolerance, or distance tolerance was used.
- Deterministic representation matches were limited to source-proven blank distance recovery by unique race, Ballarat SYN to SYNTHETIC spelling, and Sandown layout expansion by unique race.

## Outputs

- Candidate Form Guide: `work\all-runner-epi-product-bridge-v1\edgeiq_form_guide_enriched_v2.ALL_RUNNER_EPI_BRIDGE_CANDIDATE.json`
- Slot classification CSV: `work\all-runner-epi-product-bridge-v1\edgeiq_all_runner_epi_product_bridge_v1_slot_classification.csv`
- Slot classification JSON: `work\all-runner-epi-product-bridge-v1\edgeiq_all_runner_epi_product_bridge_v1_slot_classification.json`
- Validation JSON: `work\all-runner-epi-product-bridge-v1\edgeiq_all_runner_epi_product_bridge_v1_validation.json`

## Classification Counts

- CERTIFIED_EPI_DETERMINISTIC_REPRESENTATION_MATCH: 84
- CERTIFIED_EPI_UNIQUE_MATCH: 958
- LEGITIMATE_NO_EPI_INVALID_CALCULATION: 6
- LEGITIMATE_NO_EPI_UNMATCHED_BENCHMARK: 872
- OUTSIDE_WAREHOUSE_SOURCE_COVERAGE: 96
- SOURCE_HISTORY_MISMATCH: 25
- SOURCE_HISTORY_MISMATCH_DATE_CONFLICT: 1
- SOURCE_HISTORY_MISMATCH_REPRESENTATION_UNPROVEN: 2
