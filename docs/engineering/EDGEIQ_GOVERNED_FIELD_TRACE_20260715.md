# EDGEiQ Governed Field Trace - 2026-07-15

Generated: 2026-07-15T15:10:00

This document records every current user-visible analytical field in the race workspace family and the governed data path used to display it. It does not introduce new calculations.

| Workspace | Displayed Field | Canonical Builder | Service | Feed | Coverage | Wired | Reason |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| Race | Race identity | `build_edgeiq_three_day_product_catalog_v1.py` | `threeDayCatalog.ts` | `edgeiq_three_day_product_catalog_v1.json` | 100.00% | yes | meeting/race state |
| Field | Runner number | `build_edgeiq_three_day_product_catalog_v1.py` | `formGuideNormaliser.ts` | `edgeiq_three_day_product_catalog_v1.json` | 50.24% | yes | race field |
| Field | Silks | `build_edgeiq_three_day_product_catalog_v1.py` | `formGuideNormaliser.ts` | `edgeiq_three_day_product_catalog_v1.json` | 0.00% | yes | race field |
| Field | Trainer | `build_edgeiq_three_day_product_catalog_v1.py` | `formGuideNormaliser.ts` | `edgeiq_three_day_product_catalog_v1.json` | 50.24% | yes | race field |
| Field | Jockey | `build_edgeiq_three_day_product_catalog_v1.py` | `formGuideNormaliser.ts` | `edgeiq_three_day_product_catalog_v1.json` | 48.82% | yes | race field |
| Field | Weight | `build_edgeiq_three_day_product_catalog_v1.py` | `formGuideNormaliser.ts` | `edgeiq_three_day_product_catalog_v1.json` | 50.24% | yes | race field |
| Field | Barrier | `build_edgeiq_three_day_product_catalog_v1.py` | `formGuideNormaliser.ts / mapFeed.ts` | `edgeiq_three_day_product_catalog_v1.json / edgeiq_map_terminal_feed_v1.csv` | 50.24% | yes | race field and map feed |
| Performance | EPI | `build_edgeiq_form_guide_enriched_v2.py / build_edgeiq_epi_workspace_terminal_feed_v1.py` | `formGuideNormaliser.ts / epiWorkspaceFeed.ts` | `edgeiq_form_guide_enriched_v2.json / edgeiq_epi_workspace_terminal_feed_v1.csv` | 78.53% | yes | current and historical ratings |
| Performance | ERI | `build_edgeiq_form_guide_enriched_v2.py` | `formGuideNormaliser.ts / epiWorkspaceFeed.ts` | `edgeiq_form_guide_enriched_v2.json / edgeiq_epi_workspace_terminal_feed_v1.csv` | 0.00% | yes | historical race strength |
| Form | Early Speed | `build_edgeiq_current_early_speed_v1.py` | `formGuideNormaliser.ts` | `edgeiq_form_guide_enriched_v2.json` | 50.10% | yes | current race speed projection |
| Form | Late Speed | `build_edgeiq_current_late_speed_v1.py` | `formGuideNormaliser.ts` | `edgeiq_form_guide_enriched_v2.json` | 51.09% | yes | current race late speed projection |
| Form | Suitability | `build_edgeiq_current_suitability_v1.py` | `formGuideNormaliser.ts` | `edgeiq_form_guide_enriched_v2.json` | 76.54% | yes | current race suitability |
| Form | Form Momentum | `build_edgeiq_current_form_momentum_v1.py` | `formGuideNormaliser.ts` | `edgeiq_form_guide_enriched_v2.json` | 77.34% | yes | current form trend |
| Market | Market | `build_edgeiq_market_terminal_feed_v1.py` | `marketFeed.ts / formGuideNormaliser.ts` | `edgeiq_market_terminal_feed_v1.csv / edgeiq_form_guide_enriched_v2.json` | 17.30% | yes | current market when available |
| Market | EDGEiQ Price | `build_edgeiq_form_guide_enriched_v2.py / build_edgeiq_market_terminal_feed_v1.py` | `marketFeed.ts / formGuideNormaliser.ts` | `edgeiq_market_terminal_feed_v1.csv / edgeiq_form_guide_enriched_v2.json` | 91.25% | yes | assessed price |
| Map | Run style / map | `build_edgeiq_map_terminal_feed_v1.py` | `mapFeed.ts` | `edgeiq_map_terminal_feed_v1.csv` | 0.00% | yes | expected settling read |
| Nexus | Key insights | `build_edgeiq_insights_terminal_feed_v1.py` | `insightsFeed.ts` | `edgeiq_insights_terminal_feed_v1.csv` | 0.00% | yes | current race intelligence |
| Results | Race result context | `build_edgeiq_meeting_results_terminal_feed_v1.py / historical run services` | `ResultsWorkspace.ts` | `runner historical run context` | 0.00% | yes | race-level post-result workspace is pending; runner-level historical result context exists |
| Track/Weather | Track and weather | `build_edgeiq_on_track_weather_governed_v1_2.py` | `weatherFeed.ts / MeetingWeatherWorkspace` | `governed live-weather v1.2 outputs` | 0.00% | yes | meeting-level weather integration preserved |
| Scratchings/Gear | Scratchings and gear | `meeting scratchings and gear builders` | `MeetingScratchingsWorkspace / MeetingGearChangesWorkspace` | `meeting governed feeds` | 0.00% | yes | meeting-level tabs |
