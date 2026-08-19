# EDGEiQ Historical Performance Identity Audit V1

Historical race runners: `24`
Racing.com horse/runner codes available: `24`
Identity map exists: `NO`
Identity map rows: `0`
Exact identity matches: `0`
Identity misses: `24`
Ambiguous identities: `0`

## Finding
Historical identity is not the first zero-row stage because the performance rating base currently has zero rows. However, once normalisation is restored, the active observation builder would still require `config/performance-intelligence/edgeiq_horse_performance_identity_map_v1.csv` and source horse names from rating-base rows.
The current V2 sectional and lengths rows expose `canonical_runner_id` but no source horse name or canonical horse id under the active exact-name identity-map contract. No deterministic repair is applied in this audit.
