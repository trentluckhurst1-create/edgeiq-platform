# EDGEIQ Platform Governance Dashboard V1.1

## Platform Status

- Governed verdict: **PASS**
- Platform governance status: **PASS_WITH_GOVERNANCE_ACTIONS**
- Governance maturity index: **64.0092**

> The maturity index is a weighted governance-coverage indicator. It is not a product-quality, data-accuracy, model-performance, or launch-readiness score.

## Headline Metrics

| Metric | Value |
|---|---:|
| Canonical builders | 1280 |
| Confirmed active/truncated defects | 3 |
| Resolved dependency edges | 197 |
| Orphan builders | 1163 |
| Product feeds | 7228 |
| Owned product feeds | 2951 |
| Unowned product feeds | 4277 |
| Multiple-evidenced-owner feeds | 1001 |

## Coverage

| Coverage area | Percentage |
|---|---:|
| Estimated canonical parse health | 99.7763% |
| Canonical scope reconciliation | 100.0% |
| Builder graph connection | 9.1406% |
| Product feed ownership | 40.8273% |

## Priority Governance Actions

- **HIGH â€” ACTIVE_OR_TRUNCATED_PARSE_DEFECT (3):** Repair individually through governed scripts and rerun the parse-failure auditor.
- **MEDIUM â€” RETAINED_PARSE_FAILURE_REVIEW (792):** Classify using stronger source provenance and lifecycle evidence.
- **MEDIUM â€” ORPHAN_CANONICAL_BUILDER (1163):** Determine whether each is standalone, externally triggered, historical, or missing dependency evidence.
- **MEDIUM â€” UNRESOLVED_DEPENDENCY (2013):** Normalise path semantics and assign upstream ownership.
- **HIGH â€” MULTIPLE_FEED_OWNERS (1001):** Select one authoritative owner or document an explicit shared-ownership contract.
- **HIGH â€” UNOWNED_PRODUCT_FEED (4277):** Assign a canonical owner or exclude the feed from supported product scope.

## Completed Governance Units

1. Canonical Builder Registry V1.1
2. Canonical Parse Failure Auditor V1
3. Canonical Scope Refiner V1
4. Canonical Builder Dependency Graph V1.1
5. Product Feed Registry V1.1
6. Platform Governance Dashboard V1.1

## Correction from V1

V1 assumed exact metric names in upstream summary JSON. V1.1 records every source schema and resolves required metrics through governed aliases and nested-key discovery. Missing required metrics now fail with the full list of available source keys.

## Governance Boundary

This dashboard consolidates governed evidence. It does not repair source code, delete files, assign ownership without evidence, lower thresholds, or claim that unresolved records are healthy.
