# CODEX Issue #5 Execution Governance Audit

Status: **GOVERNANCE INVALID - DO NOT RELY ON ISSUE #5 FIT RESULTS**

Scope: Review of the completed Issue #5 bake-off on PR #6 after commit `3b900dce`. No model fitting, scoring, market access, closed price-source search, identity reconstruction, or mixed-year source row read was performed for this audit.

## 1. Issue #5 Result Validity

The completed Issue #5 fit/scoring results are **not governance-valid** under the approved plan.

Reason:

- `scripts/research/run_codex_issue5_bounded_bakeoff_20261010.py` reads `perf026` at lines 127-131 via `pd.read_csv(perf026, ..., chunksize=500000)`.
- The `race_date <= 2024` restriction is applied only after each chunk is already loaded.
- The approved plan explicitly prohibited row-level chunk filtering from mixed-year files because sealed-year rows would be read before exclusion.
- Existing metadata does not certify `perf026` as sealed-year-free. `outputs/research/profitability_program/v2/V2_001_DATA_ESTATE_INVENTORY.csv` lists `edgeiq_certified_flat_walk_forward_epi_026.csv` as a 473,548,512-byte file with `race_date`.
- Existing coverage metadata `outputs/research/model_lab_026/certified_epi_coverage_by_year_026.csv` includes rows for 2025 and 2026.

Therefore the run breached the sealed-year source-admission rule before fitting. The reported A/C/D metrics and `RETAIN_STAGE011` verdict from the executed bake-off are quarantined as governance-invalid. Stage011 itself remains preserved as the prior baseline/champion, but the Issue #5 execution cannot be used as fresh evidence.

## 2. Stage016 Context Dataset Availability

No legally admissible 2021-2024-only Stage016 context dataset was found through approved lineage.

Observed approved-lineage context sources:

- `outputs/research/model_lab_031/certified_current_race_context_031.csv`
- `outputs/research/model_lab_032/certified_current_race_context_032.csv`

Both appear in existing inventories as broad historical context authorities, not sealed-year-free 2021-2024 partitions. The LAB031 summary reports 631,102 output rows and is sourced from the canonical performance warehouse / LAB026 calculated universe. Existing LAB026 coverage metadata includes 2025 and 2026, so LAB031/LAB032 cannot be admitted by row filtering under the current sealed-year rule.

Files named `PL001_ENRICHED_LOCAL_UNIVERSE_2021_2024.csv` and `PL002_ENRICHED_LOCAL_UNIVERSE_2021_2024.csv` exist, but existing inventory shows market/SP fields such as `starting_price`, `market_raw_p`, `market_overround`, and `market_devig_p`. They are not approved Stage016 context lineage and are not admissible for this model bake-off.

## 3. Exact B/E/F/G Blockers

Candidates B/E/F/G require `F1_STAGE016_44`, which is `F0_STAGE011_35` plus LAB031 Stage016 context features.

The blockers are:

- No pre-existing sealed-year-free 2021-2024 LAB031/LAB032 context partition was found.
- The available LAB031/LAB032 context authorities are mixed-year sources.
- The approved plan forbids reading mixed-year rows and then filtering out sealed years.
- The prior script correctly fail-closed B/E/F/G for LAB031 context admission, but the overall run was already invalid because `perf026` had been read the same forbidden way.

## 4. Narrowest Compliant Next Experiment

No further learner comparison is compliant yet.

The narrowest compliant next step is a **non-fitting source-admission repair audit**:

1. Locate an existing, pre-generated, sealed-year-free 2021-2024 artifact for both:
   - strict-prior clean placing history needed by Stage011 reconstruction; and
   - LAB031/LAB032 Stage016 context features.
2. Use metadata, filenames, existing governance JSON/CSV, and checksums only. Do not read mixed-year source rows.
3. If both sealed-year-free artifacts exist and contain the exact Stage011 race/runner universe, amend Issue #5 execution to use only those admitted artifacts.
4. If either artifact does not exist, stop and request a separate governance decision on how a sealed-year-free export can be produced upstream without exposing 2025-2026 rows to the research runner.

Only after that source-admission repair passes should a model run be re-authorised. The next model experiment should be the original A-H budget, not a new learner search.
