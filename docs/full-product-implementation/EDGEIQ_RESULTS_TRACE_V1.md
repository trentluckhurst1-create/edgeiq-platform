# EDGEiQ Results Trace V1

Workspace: RESULTS

Primary product path:
- Meeting-level Results workspace using public/data/edgeiq_meeting_results_terminal_feed_v1.csv.
- Race-level expansion uses current meeting race runner rows and governed standardised length fields only.

Frontend load guard:
- React does not load public/data/edgeiq_results_terminal_feed_v1.csv.
- The meeting results service rejects feeds over 10,000 rows.

Rules applied:
- Fixture/demo result generation removed from Results path.
- Official elapsed race-time display removed from product tables/snapshots.
- Sectional display is EDGEiQ lengths versus standard only.
- Positive sectional values render neutral; negative values retain inside-standard emphasis.
- Stewards actions remain disabled unless a governed internal report path exists.
- Global Results nav reuses the selected meeting context instead of an unconnected search shell.
