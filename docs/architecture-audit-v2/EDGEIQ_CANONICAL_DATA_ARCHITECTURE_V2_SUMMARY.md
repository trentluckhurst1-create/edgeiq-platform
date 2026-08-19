# EDGEIQ_CANONICAL_DATA_ARCHITECTURE_V2

- Generated UTC: `2026-07-27T20:57:08.758071+00:00`
- Repository: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM`
- Overall status: **REVIEW_REQUIRED**

## Production findings

- repository_files: `52441`
- live_production_files: `25469`
- live_production_data_files: `7233`
- live_production_source_files: `4047`
- production_data_references: `17336`
- production_missing_data_references: `2758`
- production_unreferenced_data_files: `3085`
- production_exact_duplicate_groups: `376`
- production_duplicate_potential_redundant_bytes: `2786043148`
- production_basename_collision_groups: `103`
- production_python_dependency_rows: `8470`
- production_python_syntax_errors: `1936`

## Domain separation

- archive: `418` files, `95683087` bytes
- audit_output: `12` files, `108311498` bytes
- checkpoint: `21251` files, `15360010230` bytes
- documentation: `987` files, `360015857` bytes
- generated_output: `602` files, `33839909` bytes
- other_repository: `764` files, `72539606` bytes
- performance_intelligence_evidence: `1347` files, `15290767294` bytes
- performance_intelligence_output: `1362` files, `204424605` bytes
- production_automation: `3189` files, `28711897` bytes
- production_frontend: `1077` files, `36576780` bytes
- production_public_asset: `12229` files, `98853173` bytes
- production_public_data: `8956` files, `18180777287` bytes
- production_root: `18` files, `778089` bytes
- source_discovery_evidence: `229` files, `27967910` bytes

## Interpretation rules

- Checkpoints and archives are not treated as live production.
- A missing string reference requires review; it is not automatically a runtime defect.
- An unreferenced data file is not automatically obsolete.
- Duplicate files are evidence for review only; nothing was deleted.
