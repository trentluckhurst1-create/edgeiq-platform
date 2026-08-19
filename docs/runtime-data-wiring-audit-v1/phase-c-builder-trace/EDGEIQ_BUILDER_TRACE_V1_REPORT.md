# EDGEIQ_BUILDER_TRACE_V1

Generated: 2026-07-27T21:54:15.805977+00:00

## Summary

- Problem field rows: 428
- Empty field rows: 109
- Low-population field rows: 319
- Affected runtime feeds: 28
- Source files scanned: 15938
- Feeds with builder candidates: 28
- Feeds without builder candidates: 0
- Missing-calculation rows: 281
- Missing-write rows: 0
- Logic-present problem rows: 147
- Overall status: REVIEW_REQUIRED

## Trace Status Counts

- FIELD_NOT_FOUND_IN_BUILDER: 216
- FIELD_REFERENCE_ONLY: 3
- LOGIC_PRESENT_BUT_OUTPUT_EMPTY: 56
- LOGIC_PRESENT_PARTIAL_POPULATION: 91
- OUTPUT_FIELD_DECLARED_CALCULATION_NOT_CONFIRMED: 62

## Interpretation

- NO_BUILDER_IDENTIFIED means no credible source producer was found.
- FIELD_NOT_FOUND_IN_BUILDER means the feed field is absent from its candidate producer.
- CALCULATED_BUT_WRITE_NOT_CONFIRMED means calculation evidence exists but output mapping was not confirmed.
- OUTPUT_FIELD_DECLARED_CALCULATION_NOT_CONFIRMED means the output schema contains the field but calculation evidence was not found.
- LOGIC_PRESENT_BUT_OUTPUT_EMPTY means both calculation and write evidence exist, so upstream values or governed conditions require inspection.
- LOGIC_PRESENT_PARTIAL_POPULATION means sparse population may be governed or upstream-dependent.
