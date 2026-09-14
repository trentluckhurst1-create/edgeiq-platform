# EDGEiQ Performance Workspace V2 Audit

Run timestamp: 2026-09-14T06:42:56+10:00
Pipeline date override used for recovery: 2026-09-13
Visible workspace: `src/edgeiq-os/race/components/PerformanceWorkspace.tsx`

## Outcome

PASS with documented upstream coverage limitation.

Performance Workspace V2 now reads governed current-runner prior-history rows from the runner detail shards and displays a governed sectional evidence band. The sectional band is evidence-only. It does not mutate fair price, probability, market action, decision labels, or execution state.

The fresh recapture no longer reproduces the earlier 299-runner Sale/Kilmore accepted universe. With `EDGEIQ_PIPELINE_DATE=2026-09-13`, the current published product catalog contains:

| Meeting date | Meeting | Races | Runners |
| --- | --- | ---: | ---: |
| 2026-09-13 | Sale | 8 | 101 |
| 2026-09-14 | Hamilton | 8 | 103 |

Total current runners: 204.

Kilmore is not present in the fresh Racing.com recapture for this run, so Kilmore browser acceptance was not performed. Stale Kilmore data was not reused.

## Source Hierarchy

The V2 current-runner history feed is built by `scripts/build_edgeiq_current_runner_performance_history_v1.py`.

Priority order:

1. `RESULTS_REPORT_GOVERNED`
2. `RESULTS_HISTORY_CLEAN`
3. `HISTORICAL_FORM_TABLE`
4. `FORM_CARD_RUNS_WITH_STEWARDS`
5. `FULL_CAREER_FORM`
6. `RACING_COM_LAST_PROFESSIONAL_RACE`
7. `RACING_COM_LAST_FIVE_FALLBACK`, only when no stronger strict-prior source rows exist

No fallback row infers track, distance, rating, early sectional, or late sectional values from `lastFive`.

## Identity And Temporal Rules

Current-runner identity key:

`current_race_date | canonical current track | current race number | canonical horse name`

Historical-row eligibility:

`historical_race_date < current_race_date`

Validation result: 0 strict-prior violations across 785 history rows.

Identity certification emitted by the V2 feed:

`HORSE_NAME_CANONICAL_EXACT_STRICT_PRIOR`

## Coverage

Output feed: `public/data/edgeiq_current_runner_performance_history_v1.csv`

| Metric | Count |
| --- | ---: |
| Current runners | 204 |
| History rows | 785 |
| Runners with 1+ prior history row | 141 |
| Runners with 3+ prior history rows | 87 |
| Runners with 5+ prior history rows | 59 |
| Rows with date | 785 |
| Rows with track | 785 |
| Rows with distance | 723 |
| Rows with class | 609 |
| Rows with going | 557 |
| Rows with finish | 736 |
| Rows with margin | 644 |
| Rows with rating | 285 |
| Rows with early sectional | 0 |
| Rows with late sectional | 0 |
| Rows with any sectional | 0 |

History source counts:

| Source | Rows |
| --- | ---: |
| RESULTS_HISTORY_CLEAN | 336 |
| RESULTS_REPORT_GOVERNED | 227 |
| FORM_CARD_RUNS_WITH_STEWARDS | 105 |
| RACING_COM_LAST_PROFESSIONAL_RACE | 100 |
| FULL_CAREER_FORM | 17 |

## Sectional Evidence

Strict governed sectional source:

`public/data/edgeiq_sectional_governed_v29.csv`

Join key:

`historical_race_date | canonical historical track | historical race number | canonical horse name`

Strict V29 sectional matches for the current 204-runner universe: 0.

Quarantine file not used:

`public/data/edgeiq_sectional_governed_v29_quarantine.csv`

UI behavior:

When strict sectional evidence is unavailable, the workspace displays `NO SECTIONAL HISTORY` and `LIMITED DATA`. It does not derive labels from older board fields or quarantined data.

## Pricing And Decision Immutability

No pricing, probability, market-action, decision, or execution scripts were run for this audit.

Reference files observed during the audit:

| File | Rows | SHA-256 |
| --- | ---: | --- |
| `public/data/edgeiq_sectional_governed_v29.csv` | 25,843 | `0F6FF521F7718C9FCF3E47132CD8FCC8136AC10864F4813AD40A3E065990CEF0` |
| `public/data/edgeiq_sectional_governed_v29_quarantine.csv` | 46,154 | `463226DAFA015C7475C55548391F65C86619B8D1A23001462E206ED6033DA09E` |
| `public/data/edgeiq_live_runner_board_sectionals_v31.csv` | 503 | `CD0F9D703B8709658DB1F802C10311DF78B217C5B848B6A3C59D2B5318AE0570` |

The V31 live runner board sectional sidecar was observed only as an existing file and was not used to change V2 history, pricing, or decisions.

## Build And Browser Acceptance

Commands:

```powershell
$env:EDGEIQ_PIPELINE_DATE='2026-09-13'
python scripts\build_edgeiq_current_runner_performance_history_v1.py
python scripts\build_edgeiq_race_detail_shards_v1.py
npm run build
```

Build result: PASS.

Local preview checked at:

`http://127.0.0.1:4176/`

The in-app browser controller failed before initialization with `failed to write kernel assets: The system cannot find the path specified. (os error 3)`. Acceptance was completed with local Playwright against the same preview URL.

Browser acceptance path:

1. Open `Meetings`.
2. Open Sale R5.
3. Open `Performance`.

Observed result:

| Check | Result |
| --- | --- |
| Performance workspace mounted | PASS |
| Sale R5 runner count | 11 |
| Runner detail rows visible | PASS |
| Prior-history rows visible for Magic Drum | 5 |
| `Performance detail not supplied.` absent | PASS |
| Governed sectional evidence band visible | PASS |
| Sectional status | `NO SECTIONAL HISTORY` / `LIMITED DATA` |

Second published-meeting smoke path:

1. Open `Meetings`.
2. Switch to `Tomorrow Mon, 14 Sept`.
3. Open Hamilton R5.
4. Open `Performance`.

Observed result:

| Check | Result |
| --- | --- |
| Performance workspace mounted | PASS |
| Hamilton R5 runner count | 11 |
| Prior-history rows visible for Side Piece | 1 |
| `Performance detail not supplied.` absent | PASS |
| Governed sectional evidence band visible | PASS |

## Remaining Limitations

1. Kilmore is absent from the fresh upstream recapture and therefore absent from the current published catalog.
2. Strict V29 sectional join coverage is zero for the current 204-runner universe.
3. Several named performance fact tables remain empty for current runners.
4. Some current runners still rely on Racing.com last-professional-race rows or have no strong prior-history source rows.
