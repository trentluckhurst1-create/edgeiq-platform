# EDGEiQ Track Map Design Template V1

Status: LOCKED TEMPLATE  
Applies to: all EDGEiQ racecourse track maps  
Based on: final approved Caulfield / Caulfield Heath design

## Purpose

EDGEiQ track maps must look like premium racing intelligence schematics.

They are not club brochures.
They are not satellite images.
They are not dashboard widgets.
They are professional track intelligence assets.

## Core Style

Background:
- #020611
- #03070d
- #07111f

Panel background:
- rgba(3, 7, 13, 0.72)

Panel border:
- rgba(88, 255, 223, 0.15)

Primary text:
- #f4f7fb

Muted text:
- #a8b3c9

EDGEiQ accent:
- #58ffdf

Course Proper:
- #f2f4f7

Heath / Synthetic / Inner Track:
- #9cf5d6

Positive / secondary green:
- #7cf28a

Warning:
- #f5c451

Regression / risk:
- #ff4d4d

## Typography

Use clean uppercase headings.

Recommended:
- Inter
- Arial fallback
- letter spacing for section titles
- large bold track name

Track title:
- font-weight: 900+
- uppercase
- large

Section headers:
- uppercase
- small
- EDGEiQ accent colour

## Layout Rules

Track map must be the hero.

Target proportions:
- Track/circuit: 65–75% of canvas
- Support panels: 25–35% of canvas

Do not crowd the circuit.

Do not place panels over the track.

Do not add decorative cards unless they provide race-day information.

## Required Panels

Top left:
- EDGEiQ Track Map
- Track name
- Course type

Top pills:
- Track rating
- Rail position
- Updated time

Top/right:
- Track details table:
  - Circumference
  - Width
  - Home straight

Legend:
- Course Proper
- Heath / Synthetic / Inner Track where relevant

Bottom:
- Distance Starts
- Meeting Conditions

Meeting Conditions:
- Track Rating
- Rail
- Rainfall
- Irrigation
- Wind
- Temperature

## Track Rendering Rules

Use SVG paths.

Track lines must be:
- smooth
- clean
- consistent width
- professional
- evenly spaced
- geometric

Use:
- stroke-linecap="round"
- stroke-linejoin="round"
- shape-rendering="geometricPrecision"

Do not use:
- lumpy paint-like strokes
- thick blobs
- rough hand-drawn paths
- excessive glow
- raster screenshots
- club logos
- MRC/VRC branding

Course Proper should be a clean white rail-style strip.

Heath / Synthetic should be a clean mint strip.

Spacing between track paths must remain even around the circuit.

## Distance Labels

Distance labels must be:
- clear
- outside the track where possible
- aligned with the correct start marker
- not overlapping track lines
- not crossing the circuit with long dashed lines

Use:
- small dot marker
- short tick/leader only when required
- minimal label

## Forbidden

Do not include:
- MRC branding
- Melbourne Racing Club branding
- VRC branding
- fake bias panels
- fake performance claims
- random icons
- excessive marketing copy
- decorative filler
- satellite backgrounds

## Approved Visual Direction

The approved Caulfield map uses:
- dark EDGEiQ background
- large clean track circuit
- white Course Proper
- mint Heath Track
- minimal panels
- sharp rail strip icon
- understated distance labels
- professional premium product feel

This is the master visual standard for future tracks.

## Future Dynamic Layers

Reserve design room for:
- live rail overlay
- wind direction overlay
- rainfall/irrigation context
- pace map overlay
- historical bias overlay
- run-style advantage zones
- replay marker overlays

Do not show these unless the data is ready.

## File Naming

Use:

public/assets/tracks/{track_name}_edgeiq.svg

Examples:
- caulfield_edgeiq.svg
- flemington_edgeiq.svg
- sandown_hillside_edgeiq.svg
- sandown_lakeside_edgeiq.svg
- bendigo_edgeiq.svg

## Validation

Every track map must pass:

1. SVG parses successfully.
2. No external club branding.
3. No raster embeds unless explicitly approved.
4. No overlapping text.
5. Circuit is the visual hero.
6. Distance markers match source map.
7. npm run build passes.

