# FORM GUIDE APPROVED PIXEL SPEC V1

Source authority: `05_FORM_GUIDE_APPROVED.png`
SHA-256: `B13DB8C7300A3660C0E54600129F37EF877A172ECAB32121F2FDA86D18D7797C`
Canvas: `1536 x 1024`

This spec is the implementation contract for the live FORM GUIDE workspace. It preserves live governed data and limits changes to React structure, copy, interactions, and CSS presentation.

## Major Regions

| Region | x | y | w | h | Role |
| --- | ---: | ---: | ---: | ---: | --- |
| `canvas` | 0 | 0 | 1536 | 1024 | root |
| `left_nav` | 0 | 0 | 186 | 1024 | persistent_navigation |
| `topbar` | 186 | 0 | 1350 | 66 | global_header |
| `content` | 207 | 72 | 1310 | 900 | workspace_content |
| `breadcrumb` | 208 | 78 | 350 | 16 | breadcrumb |
| `race_title` | 208 | 102 | 350 | 34 | race_identity |
| `race_meta` | 208 | 144 | 1010 | 20 | race_metadata |
| `subnav` | 208 | 170 | 1308 | 40 | section_tabs |
| `form_tools` | 993 | 221 | 466 | 22 | form_tools |
| `summary_table` | 208 | 249 | 1308 | 153 | runner_summary_table |
| `expanded_runner` | 208 | 414 | 1308 | 556 | expanded_runner_card |
| `runner_header` | 220 | 426 | 1245 | 62 | selected_runner_header |
| `today_match` | 218 | 497 | 204 | 232 | today_match_panel |
| `profile_matrix` | 428 | 497 | 878 | 232 | horse_profile_matrix |
| `match_insights` | 1310 | 497 | 198 | 232 | match_insights |
| `recent_form` | 220 | 742 | 1280 | 210 | recent_form_table |
| `footer` | 612 | 993 | 850 | 20 | app_footer |

## Required Live Behaviour

- FORM GUIDE opens inside the preserved EDGEiQ race workspace navigation.
- Summary table shows every governed runner from the selected race.
- Expanding a runner shows the selected horse profile, today's match, career matrix, insights, and recent form table.
- The implementation must use live governed data only. Missing values render as a clean dash, not invented content.
- EPI/ERI/pricing/probability/rating calculations are not modified by this spec.

## Required Text System

See `FORM_GUIDE_APPROVED_TEXT_SPEC_V1.csv` for exact visible labels and typography intent.

## Required Geometry

See `FORM_GUIDE_APPROVED_GEOMETRY_V1.csv` for region-level pixel boxes measured against the approved 1536x1024 PNG.
