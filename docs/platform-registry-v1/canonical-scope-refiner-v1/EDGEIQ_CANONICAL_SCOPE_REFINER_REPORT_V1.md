# EDGEIQ Canonical Scope Refiner V1

## Executive Summary

- Verdict: **PASS**
- Canonical builders before refinement: **1341**
- Canonical builders after refinement: **1280**
- Deterministic scope exclusions: **61**
- Retained canonical parse failures: **792**
- Estimated refined canonical parse health: **38.125%**

## Scope Policy

The refiner excludes only records whose forensic classification provides deterministic evidence that they are generated, checkpoint, archived, PowerShell wrappers, embedded-source wrappers, or otherwise noncanonical.

`ACTIVE_CODE`, `TRUNCATED`, and `UNKNOWN` records remain canonical and are carried into the remediation queue.

## Exclusions by Classification

| Classification | Count |
|---|---:|
| ARCHIVED | 46 |
| CHECKPOINT | 14 |
| GENERATED | 1 |

## Retained Failures by Classification

| Classification | Count |
|---|---:|
| UNKNOWN | 789 |
| ACTIVE_CODE | 3 |

## Governance Result

This unit refines classification evidence only. It does not modify or delete any source builder. The refined registry is a governed derivative output for the next dependency-graph phase.
