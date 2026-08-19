# EDGEiQ Data Acquisition Strategy Investigation V1

Generated: 2026-07-30 Australia/Sydney

## Executive Decision

EDGEiQ should not depend on one public website, one reverse-engineered endpoint, or one ad hoc recovery pipeline. The sustainable architecture is a governed hybrid model:

- Official licensed feeds for core racing facts.
- Licensed specialist feeds for speed, sectionals and market snapshots.
- BOM registered or paid services for production weather.
- User-supplied official exports as a governed bridge and fallback.
- Public browser-rendered pages only for diagnostics, QA, internal research, or permitted use.
- Protected APIs, hidden credentials, session reuse and access-control bypass are prohibited unless the provider grants explicit authorised API access.

## Best Long-Term Victoria Architecture

The strongest identified canonical route for Victorian and Australian core racing facts is an official/commercial data feed path, especially Racing Australia-approved distribution through BetMakers CoreAPI/managed APIs or another approved distributor such as Racing and Sports. This should cover fields, acceptances, scratchings, gear, weights, barriers, form, results, nominations, trials and official race facts depending contract scope.

Victorian speed and sectional data should be licensed from the relevant rights chain, likely involving Racing Victoria, Racing.com, Champion Data, TripleSdata, BetMakers/Racelab or a specialist provider such as Punting Form. Public display on Racing.com is evidence that the data exists, not evidence that EDGEiQ can automate or commercially reuse it without permission.

Weather should use BOM registered or paid services for product reliability and commercial support. Free BOM feeds can be useful for research if the usage complies with BOM terms.

## What EDGEiQ Owns

EDGEiQ should treat raw racing facts as licensed/source-governed inputs and its own analytics as derived outputs.

Raw inputs include meetings, races, runners, jockeys, trainers, weights, barriers, official times, margins, results, scratchings, gear, track condition, rail, weather, speed data, sectionals and market snapshots.

EDGEiQ-derived analytics include:

- Standard Times
- Lengths v Standard
- Performance Base
- Normalisation
- Horse Ratings
- Race Entry Snapshots
- Projected Performance
- EPI
- Race shape, Nexus and other proprietary intelligence layers where calculated from governed inputs

This separation matters legally and technically: EDGEiQ can own its methodology while still respecting source rights for the raw facts.

## Source Categories

### Public Information

Public pages from Racing.com, Racing Australia and state bodies can be read by humans and used for verification. Public visibility does not automatically grant commercial automation, storage, redistribution or derived-product rights.

### Officially Licensed Access

This is the recommended canonical path for production. It should provide predictable schemas, contractual rights, provider support and auditability.

### User-Supplied Official Exports

A user-import workflow is a practical bridge. It should require file hashing, source attestation, schema validation and rights classification. It is useful for recovery and controlled operations while feed contracts are negotiated.

### Browser-Rendered Public Pages

Browser-rendered extraction can be technically useful for diagnostics and page-schema monitoring, but it is fragile and must be permission-reviewed before production/commercial use. It must not bypass controls or harvest protected credentials.

### Protected APIs

Protected application APIs are not acceptable unless EDGEiQ receives official credentials and written permission. Hidden API keys, cookies, local storage, reverse-engineered GraphQL endpoints, captcha/rate-limit bypass and session reuse are prohibited methods.

## Provider Findings

### Racing.com

Verified terms indicate Racing.com website content is copyright material and commercial use requires express written agreement. Racing.com pages may display rich racing information including sectional/speed data, but that display should be treated as public presentation, not a production licence. Racing.com, RV, Champion Data and TripleSdata should be contacted for authorised speed and sectional access.

### Racing Australia

Racing Australia publishes official racing materials and provides official industry systems. The SNS login page identifies Race Fields, Race Form and Race Results as managed by the national system, but access is restricted to authorised PRA/race-club personnel. EDGEiQ should access this data through an approved commercial distributor or explicit authorisation, not through restricted industry credentials.

### Racing Victoria

Racing Victoria has formal race-field approval rules for publication/use by wagering service providers. Even if EDGEiQ is not acting as a wagering operator, this confirms Victorian race-field data has a formal rights framework. EDGEiQ should document its use case and obtain the correct permission route.

### BetMakers

BetMakers publicly states that it has been appointed as a Racing Australia data wholesaler and offers official Racing Australia data via CoreAPI and managed trading APIs. This is the highest-confidence broad-source route identified for Australian racing facts.

### Racing and Sports

Racing and Sports appears to be an approved distributor of Racing Australia data and offers enhanced information services for bookmakers, racing bodies and retail clients. It should be evaluated as an alternative or complementary provider.

### Punting Form / Sectional Times

Punting Form offers API/CSV/JSON data packs, including overall times, 200m sectionals and positions/margins in running. It is a serious candidate for licensed sectional and timing enrichment, especially where official tracking feeds are unavailable.

### BOM

BOM provides official weather feeds, including station observations. Free feeds have non-commercial and availability limitations; registered or paid services are the appropriate production path.

## Architecture Options

### Option A: Official Licensed Feeds

Strengths: highest legal support, schema stability, support/SLA, full automation, durable production path.

Weaknesses: commercial cost, contract negotiation, integration effort, provider dependency.

Best use: canonical core racing facts and production operations.

Verdict: Recommended foundation.

### Option B: Official Downloadable Files

Strengths: official source, auditable, lower engineering barrier, useful fallback.

Weaknesses: may still have restrictive terms, manual or semi-manual operation, inconsistent formats.

Best use: bridge workflow, recovery, emergency operations, data-quality validation.

Verdict: Recommended as governed fallback.

### Option C: Public Browser-Rendered Information

Strengths: visible, useful for verification, can detect schema/source availability, may fill short-term research gaps.

Weaknesses: legal uncertainty for commercial automation, brittle, no SLA, page changes break collection.

Best use: diagnostics and QA only unless written permission exists.

Verdict: Not a canonical production source.

### Option D: User-Import Workflow

Strengths: legally cleaner if user has official exports and rights; highly auditable; provider-independent fallback.

Weaknesses: manual burden, delayed data, rights still need documentation.

Best use: transition period and controlled fallback.

Verdict: Recommended as bridge.

### Option E: Hybrid Architecture

Strengths: balances sustainability, cost, legality and resilience; lets EDGEiQ run while official feeds are negotiated; preserves fallback paths.

Weaknesses: requires strong governance and source-rights registry.

Best use: EDGEiQ canonical architecture.

Verdict: Recommended.

## Prohibited Methods

EDGEiQ should not use:

- Hidden API keys extracted from web bundles.
- Human cookies, localStorage, session tokens or subscription credentials.
- Access-control, captcha or rate-limit bypass.
- Protected GraphQL/API calls without official permission.
- Credential sharing from Racing Australia SNS or similar restricted systems.
- Automated commercial collection where terms require express written agreement.
- Public content redistribution without rights.

## Governance Requirements

Every source and raw fact should carry:

- source_id
- source_name
- source_type
- acquisition_route
- licence_status
- allowed_use
- permission_reference
- terms_url
- terms_reviewed_at
- acquired_at
- source_version
- provenance_hash
- temporal_status
- canonical_promotion_status

No feed should become canonical until it passes source-rights, schema, identity, temporal and completeness gates.

## Answers to the Investigation Questions

### Which route has best long-term coverage?

Official licensed feeds, especially Racing Australia-approved distribution plus licensed speed/sectional providers.

### Which route is most technically robust?

Provider APIs or structured licensed file feeds with schema contracts and support.

### Which route is most legally supportable?

Written licence/contract, followed by documented user-supplied official exports where user rights are confirmed.

### Which route is least sustainable?

Browser-rendered public pages and protected application APIs without official permission.

### What should Victoria use first?

A hybrid: licensed official core data plus governed user-import fallback, with licensed speed/sectional provider evaluation and BOM registered/paid weather.

### What should not be done?

Do not build the product around protected Racing.com GraphQL extraction, hidden credentials or page scraping as the canonical acquisition path.

## Evidence Basis

Verified facts and provider documentation were reviewed from:

- https://www.racing.com/about-us/terms-and-conditions
- https://www.racingaustralia.horse/
- https://www.racingaustralia.horse/IndustryLogin/SNS_Login.aspx
- https://mdata.racingnsw.com.au/FreeFields/Terms-and-Conditions.aspx
- https://www.racingvictoria.com.au/wagering/race-fields-policy
- https://www.vrc.com.au/latest-news/the-need-for-speed-data/
- https://betmakers.com/articles/betmakers-appointed-racing-australia-data-wholesaler
- https://sectionaltimes.com.au/
- https://www.bom.gov.au/catalogue/data-feeds.shtml
- https://www.bom.gov.au/resources/data-services
- https://www.theracingapi.com/terms-of-service

## Final Recommendation

Adopt Option E. Build EDGEiQ around a source-rights registry and licensed canonical feeds, with official export ingestion as the bridge. Use browser-rendered public pages only as diagnostics and non-blocking verification unless permission is obtained.

This creates a repeatable pattern for Victoria first, then WA, the rest of Australia, Hong Kong and Japan.
