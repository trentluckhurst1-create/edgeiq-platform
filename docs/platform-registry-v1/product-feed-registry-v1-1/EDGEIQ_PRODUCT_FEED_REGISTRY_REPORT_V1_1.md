# EDGEIQ Product Feed Registry V1.1

## Executive Summary

- Verdict: **PASS**
- Product feeds discovered: **7228**
- Feeds with ownership evidence: **2951**
- Single-owner feeds: **1950**
- Multiple-evidenced-owner feeds: **1001**
- Unowned feeds: **4277**
- Ownership coverage: **40.8273%**

## Correction from V1

V1 discovered feeds correctly but resolved no owners. V1.1 combines governed output claims with direct canonical Python source-literal evidence. Exact path matches are preferred; unique filename matches are permitted and labelled.

## Ambiguity Policy

Non-unique filename matches are never assigned automatically. They are written to the ambiguous ownership evidence queue.

## Acceptance

The unit fails unless at least one materialised product feed has canonical ownership evidence.
