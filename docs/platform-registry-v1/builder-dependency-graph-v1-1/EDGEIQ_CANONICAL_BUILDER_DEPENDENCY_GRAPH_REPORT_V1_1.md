# EDGEIQ Canonical Builder Dependency Graph V1.1

## Executive Summary

- Verdict: **PASS**
- Canonical nodes: **1280**
- Resolved dependency edges: **197**
- Orphan builders: **1163**
- Builders with discovered inputs: **488**
- Builders with claimed outputs: **201**

## Correction from V1

V1 passed structural reconciliation while producing zero edges. V1.1 adds source-schema profiling, dynamic builder resolution, path-column scoring, and a mandatory non-zero-edge acceptance criterion.

## Governance Rule

The unit fails when zero producer-to-consumer edges are resolved.
