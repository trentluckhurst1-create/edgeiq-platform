# EDGEiQ Racing UI System Audit

Status: ACTIVE DESIGN AUTHORITY

## Product intent

EDGEiQ Racing is professional horse-racing form, ratings, mapping and pricing software. It must read as one operating system, not a collection of independently designed web pages.

## Audit findings

The repository contains several generations of visual styling, including legacy OS CSS, terminal overrides, design-system CSS and approved UI CSS. Components remain functionally useful, but historical styling layers caused inconsistent typography, panel treatment, density, controls and workspace hierarchy.

The active application now resolves that drift through a final software UI authority loaded after legacy styles.

## Active software design authority

The final visual layers are:

- `src/edgeiq-os/styles/edgeiqSoftwareSystem.css`
- `src/edgeiq-os/styles/edgeiqSoftwareModules.css`
- `src/edgeiq-os/styles/edgeiqSoftwareRaceShell.css`
- `src/edgeiq-os/styles/edgeiqSoftwareSecondary.css`

These are loaded last from `src/main.tsx` and therefore own the live product presentation.

## Global design rules

### Colour

- Application background: cool light grey
- Primary surfaces: white
- Primary accent: EDGEiQ blue
- Headings: deep navy
- Body text: dark slate
- Muted text: cool grey
- Positive: green
- Warning/pending: amber
- Negative/error: red

No workspace should introduce a new colour system without an explicit product-level decision.

### Geometry

- Primary radius: 6px
- Compact control radius: 4px
- Thin neutral borders
- Very restrained shadows
- Avoid oversized rounded marketing cards
- Avoid decorative gradients and glow effects

### Typography

EDGEiQ uses compact software hierarchy:

- Workspace title: approximately 23px, strong
- Section title: approximately 16px
- Panel title: 10-11px uppercase/strong
- Table headers: approximately 9px uppercase
- Table/body data: approximately 10-12px
- Numeric intelligence uses tabular figures

Large editorial/marketing headings are not part of the racing workspaces.

### Density

EDGEiQ is an analysis product. It should favour information density, clear grouping and rapid scanning over large empty spaces.

### Navigation

- One persistent left application navigation
- One persistent application topbar
- One consistent workspace masthead
- Race tabs use the same compact tab treatment everywhere
- Active states use EDGEiQ blue

### Cards and panels

All functional panels must use the same white surface, neutral border, compact radius and restrained shadow.

Nested cards should be minimised. A panel can contain rows, tables, metrics or compact subsections without visually turning every item into a separate website card.

### Tables

Tables are a primary EDGEiQ interface pattern:

- White body rows
- Cool grey header row
- Compact uppercase column headings
- Neutral row dividers
- Subtle hover state
- Blue-tinted selected row
- Tabular numeric figures
- No heavy zebra-striping unless there is a specific analytical reason

### Controls

Buttons, selects, inputs and filters must use the shared compact control geometry.

Primary actions use EDGEiQ blue. Secondary actions use white with a neutral border. Avoid one-off button colours and large pill controls.

### States

Ready / positive = green

Pending / awaiting = amber

Error / negative = red

Unavailable data must remain visibly unavailable and must never be visually disguised as supplied evidence.

## Workspace coverage

The unified software treatment covers:

- Home
- Meetings
- Meeting / race navigation
- Race
- Field
- Form
- Performance
- EPI
- Map
- Market
- Overview
- Insights
- Results
- Review
- Compare
- Lab
- Settings

## Shell standard

`WorkspaceShell` is the global workspace authority. Every screen receives:

- product topbar
- workspace eyebrow
- workspace title
- workspace metadata
- live-workspace status
- content stage
- product footer

New workspaces should be mounted inside this shell rather than creating their own global page frame.

## Development rule

Do not create a new standalone theme for a new EDGEiQ feature.

New components must first use the existing software tokens, shared panel treatment, typography, tables and controls. Component-specific CSS should only describe layout or genuine racing-specific visualisation behaviour.

## Legacy CSS

Legacy CSS remains in the repository because some existing components still depend on its structural rules. It is not the visual design authority. The final software layers override its visual styling.

A later refactor can progressively remove obsolete declarations after each workspace is verified, but removal should be done safely and separately from the current visual standardisation.
