# EDGEIQ Canonical Parse Failure Auditor V1

## Executive Summary

- Verdict: **PASS**
- Canonical builders: **1341**
- Canonical parse failures audited: **853**
- Active or truncated defects: **3**
- Estimated canonical platform health: **99.7763%**

## Classification Analysis

| Classification | Count | Percentage |
|---|---:|---:|
| UNKNOWN | 789 | 92.4971% |
| ARCHIVED | 46 | 5.3927% |
| CHECKPOINT | 14 | 1.6413% |
| ACTIVE_CODE | 3 | 0.3517% |
| GENERATED | 1 | 0.1172% |

## Governance Actions

| Action | Count | Percentage |
|---|---:|---:|
| INVESTIGATE | 789 | 92.4971% |
| EXCLUDE | 47 | 5.51% |
| ARCHIVE | 14 | 1.6413% |
| REPAIR | 3 | 0.3517% |

## Leading Directories

| Directory | Failures | Percentage | Active/Truncated |
|---|---:|---:|---:|
| `scripts` | 842 | 98.7104% | 3 |
| `scripts/performance-intelligence` | 10 | 1.1723% | 0 |
| `scripts/performance-intelligence/phase1_6` | 1 | 0.1172% | 0 |

## Error Analysis

| Observed Error | Count | Percentage |
|---|---:|---:|
| NO_PARSE_FAILURE | 850 | 99.6483% |
| SyntaxError | 3 | 0.3517% |

## Remediation Plan

1. Repair `ACTIVE_CODE` and `TRUNCATED` records in priority order.
2. Investigate `UNKNOWN` records before changing canonical scope.
3. Exclude only classifications supported by deterministic evidence.
4. Re-run Builder Registry v1.1 after governed scope refinement.

## Governance Recommendation

Do not mass-edit parser failures. Use this classification as the evidence base for Canonical Scope Refiner V1.
