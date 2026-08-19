# EDGEIQ FORM GUIDE Trace V1

Generated: 2026-07-18T21:15:48

## Canonical Source Flow

| Product field | Canonical source | Service path | Component path | Availability / gap |
| --- | --- | --- | --- | --- |
| NO | Three-day race catalog / race book runner identity | formGuideNormaliser.runnerNo | RaceFormGuideWorkspace main table | Available from official runner number with source fallback. |
| SILKS | Three-day race catalog / race book runner identity | formGuideNormaliser.silkUrl | RaceFormGuideWorkspace main table and dossier | Available where official silk URL is present; neutral fallback square otherwise. |
| LAST 5 | Enriched form guide / official form string | formGuideNormaliser.lastFive | RaceFormGuideWorkspace main table | Available starts only; no padded dashes. |
| HORSE | Race book + enriched runner join | formGuideNormaliser.runnerName | RaceFormGuideWorkspace main table and dossier | Available through runner catalog or enriched feed. |
| TRAINER | Race book runner fields | formGuideNormaliser.trainer | RaceFormGuideWorkspace main table and dossier | Available where official trainer is supplied. |
| JOCKEY | Race book runner fields | formGuideNormaliser.formatJockey | RaceFormGuideWorkspace main table and recent form | Current jockey available; historical jockey available through enriched fullForm where supplied. |
| WT | Race book runner fields | formGuideNormaliser.weight | RaceFormGuideWorkspace main table and dossier | Available where official carried weight exists. |
| BAR | Race book runner fields | formGuideNormaliser.barrier | RaceFormGuideWorkspace main table and recent form | Current and historical barrier available where supplied. |
| DAYS | Enriched form guide current runner row | daysSinceLastRun | RaceFormGuideWorkspace main table and dossier | Available where last official run date is joined. |
| EPI | edgeiq_epi_current_rating_v1 via enriched feed | formGuideNormaliser.epi | RaceFormGuideWorkspace main table and recent form | React displays only. |
| EARLY SPEED | edgeiq_current_early_speed_v1 via enriched feed | formGuideNormaliser.earlySpeed | RaceFormGuideWorkspace main table | React displays only. |
| LATE SPEED | edgeiq_current_late_speed_v1 via enriched feed | formGuideNormaliser.late | RaceFormGuideWorkspace main table | React displays only. |
| SUITABILITY | edgeiq_current_suitability_v1 via enriched feed | formGuideNormaliser.suitabilityScore | RaceFormGuideWorkspace main table | React displays only. |
| FORM MOMENTUM | edgeiq_current_form_momentum_v1 via enriched feed | formGuideNormaliser.formMomentum | RaceFormGuideWorkspace main table | React displays only. |
| MARKET | current market price carried by enriched feed | formGuideNormaliser.marketPrice | RaceFormGuideWorkspace main table | Current market path only; no component calculation. |
| EDGEiQ PRICE | approved pricing feed carried by enriched feed | formGuideNormaliser.edgeiqPrice | RaceFormGuideWorkspace main table | Displayed as EDGEiQ price; React does not calculate. |
| Career profile | edgeiq_runner_profile_stats_v1 / enriched profile records | formGuideWorkspaceViewModel.buildRunnerProfileDossier | Runner dossier Horse Profile | Career/track/distance/track-dist/class/jockey/prep rows are generic labels with governed records. |
| Conditions profile | edgeiq_runner_profile_stats_v1 / enriched condition records | formGuideWorkspaceViewModel.buildRunnerProfileDossier | Runner dossier Horse Profile | Firm/Good/Soft/Heavy shown when supplied; unavailable otherwise. |
| Today condition match | Current race context + existing matchesToday flag | formGuideWorkspaceViewModel.buildRunnerProfileDossier | Runner dossier Today Match | Generic categories only; no invented match score. |
| Recent form | enriched fullForm | formGuideNormaliser.recentRunsFromEnriched | Runner dossier Recent Form | Up to eight historical starts. |
| Recent form EPI | standardised sectionals epi_post or performanceRating fallback | formGuideNormaliser.recentRunsFromEnriched | Recent Form table | Numeric display where supplied. |
| Recent form ERI | run_ratings_v1 raceRating source value | formGuideNormaliser.recentRunsFromEnriched | Recent Form table | Numeric display where supplied. |
| Recent form ESI segments | edgeiq_form_sectional_profile_feed_v1 split_lengths | formGuideNormaliser.recentRunsFromEnriched | Recent Form table 8-6 / 6-4 / 4-2 / 2-F | Standardised lengths only. No raw times. |
| Position In Running | Not present in current enriched feed contract | formGuideNormaliser.positionInRunning | Recent Form table | Column exists; values stay unavailable until a governed source is added. |
| Key Insights | formGuideNormaliser governed insight groups from available records | formGuideWorkspaceViewModel.buildRunnerProfileDossier | Runner dossier Key Insights | Uses supportable record/market/price notes only. |

## Mock / Demo Risk Trace

- No mock, demo, sample, or synthetic runner metrics are introduced by this tranche.
- No product-facing Confidence column or field is rendered by the FORM GUIDE component.
- No Race Shape or Avg Finish columns are rendered in the FORM GUIDE main table.
- React displays service-shaped fields and does not calculate EPI, ERI, ESI, market, price, suitability, speed, or form momentum.
