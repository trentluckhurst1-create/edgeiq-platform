# EDGEIQ Canonical Data Architecture Audit V1

- Generated: `2026-07-27T20:38:44.417442+00:00`
- Repository files: `52428`
- Data files: `16782`
- Python builders: `5700`
- Frontend services: `980`
- Data references: `160845`
- Missing data references: `18116`
- Unreferenced data files: `8207`
- Exact duplicate groups: `15296`
- Basename collision groups: `13087`
- Checkpoint-like files: `4381`

## Interpretation

This is a discovery audit, not a deletion directive.

- Missing references require investigation.
- Unreferenced files may still be manual inputs, archival evidence or dynamically resolved.
- Duplicate hashes identify byte-identical files only.
- Basename collisions identify possible canonical ambiguity.
- Checkpoint-like files are reported but not altered.

## Output files

- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_FILE_INVENTORY.csv`
- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_DATA_REFERENCES.csv`
- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_MISSING_REFERENCES.csv`
- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_DATA_USAGE.csv`
- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_DUPLICATE_GROUPS.csv`
- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_BASENAME_COLLISIONS.csv`
- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_CHECKPOINT_FILES.csv`
- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_BUILDER_OUTPUT_MENTIONS.csv`
- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_PYTHON_DEPENDENCIES.csv`
- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_REPORT.json`
- `EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V1_SUMMARY.json`
