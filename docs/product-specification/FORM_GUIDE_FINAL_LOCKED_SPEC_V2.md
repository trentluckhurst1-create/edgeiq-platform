# FORM GUIDE FINAL LOCKED SPEC V2

This spec supersedes the rejected runtime of the prior Form Guide rebuild. The approved screenshot remains the visual target, but V2 requires the live workspace to render a rich selected runner, a populated profile matrix, and governed recent-form evidence instead of sparse placeholder panels.

## Live Component Contract

- Component: `src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx`
- Required root marker: `data-edgeiq-workspace="form-guide-final-locked"`
- Default capture viewport: `1536x1024`, deviceScaleFactor `1`, browser zoom `100%`
- No race selector chip row inside FORM GUIDE
- No visible Metric Guide panel/button
- No empty stat cards masquerading as intelligence

## Layout Regions

1. Race header with race identity and compact metadata.
2. Toolbar row with Ratings View, info, customise, and export controls.
3. All-runner summary table, 16 default visible columns.
4. Expanded selected-runner sheet directly beneath selected row.
5. Runner hero with silk, identity, and current metric strip.
6. Three-column analysis band: Today Match, Horse Profile matrix, short match read.
7. Recent Form table with last eight starts and sectional cells.
8. Sectional legend immediately below the recent form table.

## Data Rules

- Missing visible values render as `—`.
- Do not render raw placeholders such as UNKNOWN, NOT LOADED, SOURCE GAP, null, undefined, NaN, or 0.0% for missing data.
- Use governed enriched FORM data where available.
- Pricing/probability/rating model math is not changed.
