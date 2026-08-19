# EDGEiQ Horse Performance Rating Integrity Audit V1

Verdict: PASS

- Historical PI rows: 168
- Normalised rows: 168
- Rating-base rows: 168
- Horse observation rows: 168
- Horse aggregate rows: 24
- Horse rating rows: 24
- Unique rated horses: 24
- Horse-rating hash: 0ab065e2f6046abe5157770ada541f669467c319e2a896eea58c50dbbca6097a

The legacy fact audit scripts still contain stale `current_population_expected` checks from the prior zero-row blocker state. This audit independently verifies the approved current formula, identity, temporal and grain requirements.
