# EDGEiQ Engineering Specification Library

This library is the canonical engineering authority for the EDGEiQ Beta workspaces. It replaces earlier short outline recovery files with repository-grounded, implementation-grade specifications.

## Purpose

The library tells future implementation tasks what to build, where it belongs in the current repository, which data contracts own each value, and which UI behaviours are prohibited. It is documentation and governance, not a production implementation.

## Source-Of-Truth Order

1. Explicit locked requirements in the current task.
2. Current mounted application architecture and imports.
3. Current canonical builders, services and data contracts.
4. Existing passing audits.
5. Current rendered screenshots and visual-audit captures.
6. Earlier product specification documents as supporting context only.

## Product Outline Versus Engineering Specification

A product outline says what the workspace should achieve. An engineering specification defines component ownership, TypeScript contracts, data lineage, null behaviour, loading/unavailable/stale/error states, accessibility, tests, audits and acceptance criteria. Codex must use the engineering specification when implementing.

## How Codex Should Consume This Library

Read `MASTER/MASTER-001_EDGEIQ_BETA_ENGINEERING_DESIGN_SYSTEM.md` first. Then read exactly one workspace specification. Inspect the active files named in that workspace. Create a checkpoint. Implement only the scoped workspace. Run the workspace builder/audit, `npm run build`, and screenshot verification where applicable.

## Versioning

Each document carries an ID and version. Changes to locked columns, source ownership, benchmark sign convention, prohibited language or React/builder boundaries require a new revision entry and audit update.

## Audits

Run `python scripts/audit_edgeiq_engineering_specification_library_v1.py`. The audit writes text, JSON and inventory CSV outputs under `public/data/`. `scripts/validate_edgeiq_engineering_specification_library_v1.ps1` runs the audit and prints inventory.

## Completion Verification

A workspace implementation is complete only when the implementation report confirms exact column order, null/stale/error state behaviour, builder/React boundary, screenshots where required, data-contract audits and build status. File existence alone is not completion.
