# EDGEiQ Data Acquisition Roadmap V1

Generated: 2026-07-30 Australia/Sydney

## Recommendation

Adopt Option E: a governed hybrid architecture.

1. Use official licensed feeds for core racing facts.
2. Use licensed specialist/commercial feeds for speed, sectionals and market data.
3. Use BOM registered or paid services for production weather.
4. Keep user-supplied official exports as a governed bridge and emergency fallback.
5. Keep public browser-rendered collection as diagnostics/QA only unless written permission permits automated commercial use.
6. Prohibit hidden credential extraction, protected API reverse engineering, login/session reuse, access-control bypass and terms-contrary automation.

## Victoria Sequence

1. Confirm EDGEiQ use case in writing: private/internal, commercial racing intelligence, wagering product support, or media/content product.
2. Seek Racing Australia/BetMakers or approved distributor access for fields, acceptances, scratchings, gear, weights, barriers, form, results, official times and margins.
3. Seek Racing.com/RV/Champion Data/TripleSdata or licensed sectional-provider access for speed, sectionals, lane, stride, distance covered and in-running position data.
4. Establish BOM weather service path: registered/paid if commercial, free only if allowed for the usage tier.
5. Build the EDGEiQ source-rights registry: source, licence class, allowed use, permission reference, expiry, acquisition route, raw retention policy and redistribution rights.
6. Add deterministic import contracts for user-supplied official exports while commercial access is negotiated.
7. Require every raw fact to carry source_id, source_version, acquired_at, terms_version, provenance_hash, licence_status and allowed_use.
8. Keep EDGEiQ calculations separate from raw source facts: Standard Times, Lengths v Standard, Performance Base, Normalisation, Ratings and EPI are EDGEiQ-owned analytics derived from governed inputs.
9. Pilot Victoria end-to-end; only then replicate the same source-rights registry and provider evaluation for WA, other Australian jurisdictions, Hong Kong and Japan.

## Expansion Sequence

1. WA: validate race-field approval regime and official provider/distributor route before ingestion.
2. Other Australia: repeat jurisdiction-by-jurisdiction terms/licensing mapping.
3. Hong Kong: engage HKJC/licensed providers; do not assume public website reuse.
4. Japan: engage JRA/NAR/licensed distributors; plan translation and identity-governance separately.

## Immediate Engineering Tasks After Decision

1. Create `source_rights_registry` and `acquisition_route_registry` tables.
2. Create `raw_fact_lineage` schema across all canonical raw facts.
3. Create user-import staging with hash validation, schema validation and source attestation.
4. Create provider adapters behind feature flags with no protected-API credential harvesting.
5. Create a production-readiness gate: no field becomes canonical unless source rights and temporal provenance pass.
