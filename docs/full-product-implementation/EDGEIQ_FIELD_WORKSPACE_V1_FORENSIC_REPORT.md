# EDGEIQ FIELD WORKSPACE V1 Forensic Report

## Status Before Remediation
FIELD was functional but not locked. Browser and source inspection showed a basic acceptances-style table rather than a governed product workspace.

## Render Path Verified
RaceFileV3.tsx mounts RaceWorkspace for race view. RaceWorkspace maps the FIELD tab to FieldWorkspace. FieldWorkspace builds display rows through buildFieldWorkspaceRows in fieldWorkspaceViewModel.ts and receives governed form data from normaliseFormGuideRace.

## Header Finding
FIELD uses RaceWorkspace's shared non-RACE header. The header was not duplicated inside FieldWorkspace, but the shared header allowed raw administrative race text to appear as user-facing TRACK or SURFACE metadata when source fields were concatenated.

## Tab Finding
The workspace tab strip is generated from RaceWorkspace's tabs array. FIELD lacked the compact tab geometry applied to the repaired RACE workspace, allowing REVIEW to wrap awkwardly at desktop widths.

## Last-Five Data Finding
Last-five data already exists in FormGuideRaceDisplay.runners[].recentRuns and FieldWorkspace already had dormant expansion logic. The interaction was incomplete because only the runner-name button opened it, the expansion included an unnecessary navigation button, and the no-history copy was internal.

## Scratched Finding
Scratching status can arrive from official/status flags, formGuide.scratched, and a presentation market value of Scratched. The FIELD view model only trusted some status flags, so rows could show market Scratched while retaining ACTIVE status.

## EDGEiQ Semantics Finding
The current FIELD edgeiq column is primarily EPI/current performance rating data, not EDGEiQ price. The visible compact column label must therefore be EPI rather than generic EDGEiQ.

## CSS Finding
Live shell scoping uses .eiq-approved-shell. Older .edgeiq-os scoped rules do not reliably affect the approved shell. FIELD needed approved-shell scoped table, header, tab and expansion rules.

## Remediation Scope
The fix is presentation/view-model only: RaceWorkspace header sanitisation, FieldWorkspace structure/interaction, FieldWorkspace view-model scratch and weight handling, and FIELD CSS. No pricing, probability, EPI calculation, V6/V7 engine, backend, FORM workspace, HOME, MEETINGS or RACE logic is changed.
