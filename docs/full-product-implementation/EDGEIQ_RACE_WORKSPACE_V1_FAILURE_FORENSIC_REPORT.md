# EDGEiQ Race Workspace V1 Failure Forensic Report

Generated: 2026-07-26T17:03:13

## Status

PREVIOUS_RACE_LOCK_REJECTED_CONFIRMED

The rejected Race commit is `24f6583 fix(race): implement locked professional workspace specification`.
It was not reverted. The browser state at `http://localhost:5173` was inspected before source repair.

## Render Path Verified

1. `src/edgeiq-os/race/RaceFileV3.tsx` imports and mounts `RaceWorkspace`.
2. `RaceWorkspace` renders `RaceIntelligenceWorkspace` when the active race tab is `RACE`.
3. Browser DOM on `localhost:5173` confirmed:
   - `data-edgeiq-workspace-key="RACE"`
   - `data-edgeiq-mounted-component="RaceIntelligenceWorkspace"`
   - `.eiq-race-workspace` exists
   - `.eiq-race-v1` exists

Therefore the correct component was mounted. The failure was not a missing component mount.

## Browser Evidence From Rejected State

The live browser inspection found:

- `.edgeiq-os` ancestor: `false`
- `.eiq-product-shell-v4` ancestor: `false`
- `.eiq-approved-shell`: `true`
- `.eiq-race-v1` computed display: `block`
- `.eiq-race-v1__summary` computed display: `block`
- `.eiq-race-v1__summary-card` computed display: `block`
- `.eiq-race-v1__metadata` computed display: `block`
- `.eiq-race-v1__midrow` computed display: `block`
- Race tab strip `.eiq-context-tabs` computed display in Race mode: `none`
- FIELD tab strip `.eiq-context-tabs` computed display in Field mode: `grid`
- FIELD workspace uses `.eiq-workspace-panel`, which has unscoped panel styling and therefore renders acceptably.

## CSS Application Failure

The Race V1 styling was appended under selectors beginning with:

```css
.edgeiq-os .eiq-race-v1
.edgeiq-os .eiq-race-v1__summary
.edgeiq-os .eiq-race-v1__metadata
```

But the actual current product shell root is:

```html
<section class="eiq-approved-shell" data-edgeiq-approved-ui="v1">
```

There is no `.edgeiq-os` wrapper in the live DOM. As a result, Race V1-specific CSS did not match and the browser rendered raw block-flow JSX.

## Race Tab Strip Failure

An older Race-mode rule hides the race workspace tab strip. In rejected Race mode:

- `.eiq-context-tabs` display = `none`
- In FIELD mode, the same selector display = `grid`

This created a Race-only navigation regression while FIELD remained styled.

## JSX / Markup Observations

The Race JSX exists but is highly compressed. Without matching CSS, adjacent inline elements collapse visually, for example:

- `R1Time Not PublishedR2Time Not Published...`
- `TEMPOAwaiting Map Evidence...`
- `17Truly Fierce35.4Available...`

The JSX wrapper did not crash. No runtime exception caused the failure.

## Runtime / Server Findings

- Windows reported Vite listening on port `5173` at `::1`.
- `http://127.0.0.1:5173` refused connection.
- `http://localhost:5173` loaded successfully.
- This matters for acceptance: the browser acceptance must target the user-visible `localhost:5173` instance.

## Why FIELD Looked Correct While RACE Did Not

FIELD uses general workspace classes such as `.eiq-workspace-panel` and `.eiq-context-tabs` that match in the current shell. RACE relied on new dedicated styles scoped to a missing `.edgeiq-os` ancestor and had its tab strip hidden in Race mode. That difference explains the visual split exactly.

## Root Cause

CSS selector scope mismatch plus a Race-only hidden tab strip rule:

1. Race V1 styles were scoped to `.edgeiq-os`, which is absent from the live product shell.
2. The live shell uses `.eiq-approved-shell`.
3. Race tab strip was hidden only in Race mode.
4. FIELD remained acceptable because it uses unscoped shared workspace panel styles.

## Required Repair

- Retarget Race V1 CSS to the live `.eiq-approved-shell` shell.
- Ensure Race mode `.eiq-context-tabs` displays as the same grid tab strip as FIELD.
- Keep the mounted component path unchanged.
- Improve Race-specific markup where unstyled adjacent text was too fragile.
- Keep HOME, MEETINGS and FIELD untouched except for shared CSS that only scopes to Race.

## Forbidden Areas

No pricing math, governed EPI calculation, V6/V7 engines, probability logic, data thresholds, or backend engine files were inspected for modification.
