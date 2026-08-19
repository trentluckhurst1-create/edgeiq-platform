from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

COMPONENT = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingTrackWorkspace.tsx"
)

CSS = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "styles"
    / "edgeiqOsV2.css"
)

component = COMPONENT.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")

original_component = component


# ============================================================
# 1. ALLOW FIELD GRID SOURCE LABELS TO BE DISABLED
# ============================================================

old_field_grid = '''function FieldGrid({ items }: { items: TrackValue[] }) {
  return (
    <dl className="eiq-track-v1-field-grid">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{valueOrUnavailable(item.value)}</dd>
          {item.source ? <small>{item.source}</small> : null}
        </div>
      ))}
    </dl>
  );
}
'''

new_field_grid = '''function FieldGrid({
  items,
  showSources = true,
}: {
  items: TrackValue[];
  showSources?: boolean;
}) {
  return (
    <dl className="eiq-track-v1-field-grid">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{valueOrUnavailable(item.value)}</dd>
          {showSources && item.source ? <small>{item.source}</small> : null}
        </div>
      ))}
    </dl>
  );
}
'''

count = component.count(old_field_grid)

if count != 1:
    raise RuntimeError(
        f"Expected one FieldGrid function, found {count}. "
        "No files were written."
    )

component = component.replace(
    old_field_grid,
    new_field_grid,
    1,
)


# ============================================================
# 2. REPLACE TRACK CONDITION WITH GOVERNED DISPLAY RULES
# ============================================================

old_track_condition = '''function TrackCondition({ model }: { model: MeetingTrackViewModel }) {
  return (
    <section className="eiq-track-v1-panel">
      <header>
        <span>Track Condition</span>
        <strong>Official condition fields</strong>
      </header>
      <FieldGrid
        items={model.officialFields.filter(
          (item) =>
            !["INSPECTION TIME", "TRACK MANAGER"].includes(
              item.label.trim().toUpperCase(),
            ),
        )}
      />
    </section>
  );
}
'''

new_track_condition = '''const SPECIAL_INSTRUMENT_TRACKS = new Set([
  "FLEMINGTON",
  "CAULFIELD",
  "CAULFIELD HEATH",
  "MOONEE VALLEY",
  "SANDOWN HILLSIDE",
  "SANDOWN LAKESIDE",
  "MORNINGTON",
]);

function normaliseTrackDisplayName(value: string): string {
  return value
    .trim()
    .toUpperCase()
    .replace(/[-_/]+/g, " ")
    .replace(/\\s+/g, " ");
}

function normaliseConditionLabel(value: string): string {
  return value
    .trim()
    .toUpperCase()
    .replace(/[-_/]+/g, " ")
    .replace(/\\s+/g, " ");
}

function formatMillimetres(value: string | null | undefined): string | null | undefined {
  if (!value) return value;

  const trimmed = value.trim();

  if (!trimmed) return value;

  const upper = trimmed.toUpperCase();

  if (
    upper === "UNAVAILABLE" ||
    upper === "NOT SUPPLIED" ||
    upper === "N/A" ||
    upper === "NA"
  ) {
    return value;
  }

  if (/\\bMM\\b/i.test(trimmed)) {
    return trimmed;
  }

  const numericMatch = trimmed.match(/^-?\\d+(?:\\.\\d+)?$/);

  if (numericMatch) {
    return `${trimmed} mm`;
  }

  return trimmed;
}

function buildTrackConditionFields(model: MeetingTrackViewModel): TrackValue[] {
  const trackName = normaliseTrackDisplayName(model.trackName);
  const showInstrumentFields = SPECIAL_INSTRUMENT_TRACKS.has(trackName);

  return model.officialFields
    .filter((item) => {
      const label = normaliseConditionLabel(item.label);

      if (["INSPECTION TIME", "TRACK MANAGER"].includes(label)) {
        return false;
      }

      if (
        !showInstrumentFields &&
        ["GOING STICK", "MOISTURE"].includes(label)
      ) {
        return false;
      }

      return true;
    })
    .map((item) => {
      const label = normaliseConditionLabel(item.label);

      let displayLabel = item.label;
      let displayValue = item.value;

      if (label === "PENETROMETER AVERAGE") {
        displayLabel = "PENETROMETER";
      }

      if (label === "RAIN 7D" || label === "RAIN 7 D") {
        displayLabel = "RAIN 7 DAYS";
      }

      if (
        label === "IRRIGATION 7D" ||
        label === "IRRIGATION 7 D"
      ) {
        displayLabel = "IRRIGATION 7 DAYS";
      }

      if (
        label === "RAIN 24H" ||
        label === "RAIN 24 H" ||
        label === "RAIN 7D" ||
        label === "RAIN 7 D" ||
        label === "RAIN 7 DAYS" ||
        label === "IRRIGATION 24H" ||
        label === "IRRIGATION 24 H" ||
        label === "IRRIGATION 7D" ||
        label === "IRRIGATION 7 D" ||
        label === "IRRIGATION 7 DAYS"
      ) {
        displayValue = formatMillimetres(item.value);
      }

      return {
        ...item,
        label: displayLabel,
        value: displayValue,
      };
    });
}

function TrackCondition({ model }: { model: MeetingTrackViewModel }) {
  const conditionFields = buildTrackConditionFields(model);

  return (
    <section className="eiq-track-v1-panel">
      <header>
        <span>Track Condition</span>
        <strong>Official condition fields</strong>
      </header>

      <FieldGrid
        items={conditionFields}
        showSources={false}
      />
    </section>
  );
}
'''

count = component.count(old_track_condition)

if count != 1:
    raise RuntimeError(
        f"Expected one TrackCondition function, found {count}. "
        "No files were written."
    )

component = component.replace(
    old_track_condition,
    new_track_condition,
    1,
)


# ============================================================
# 3. VALIDATE COMPONENT BEFORE WRITING
# ============================================================

required_markers = (
    "SPECIAL_INSTRUMENT_TRACKS",
    '"CAULFIELD HEATH"',
    '"SANDOWN HILLSIDE"',
    '"SANDOWN LAKESIDE"',
    "buildTrackConditionFields(model)",
    'displayLabel = "PENETROMETER"',
    'displayLabel = "RAIN 7 DAYS"',
    'displayLabel = "IRRIGATION 7 DAYS"',
    "formatMillimetres(item.value)",
    "showSources={false}",
)

for marker in required_markers:
    if marker not in component:
        raise RuntimeError(
            f"Required Track display rule was not installed: {marker}"
        )

if component == original_component:
    raise RuntimeError(
        "No MeetingTrackWorkspace changes were produced."
    )


# ============================================================
# 4. APPEND NATIVE-SIZE, SHARP MAP DISPLAY CSS
# ============================================================

css_marker = "/* EDGEIQ TRACK CONDITION AND SHARP MAP V1 */"

css_block = r'''

/* EDGEIQ TRACK CONDITION AND SHARP MAP V1 */
.eiq-track-v1-map {
  display: flex !important;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 0 !important;
  margin: 0;
  padding: 20px;
  overflow: visible;
  background: #ffffff;
}

.eiq-track-v1-map img {
  display: block;
  width: auto !important;
  height: auto !important;
  max-width: 100% !important;
  max-height: none !important;
  margin: 0 auto;
  object-fit: contain !important;
  object-position: center;
  image-rendering: auto;
  transform: none !important;
  scale: none !important;
}

.eiq-track-v1-field-grid > div {
  min-width: 0;
}

.eiq-track-v1-field-grid dd {
  white-space: normal;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"


# Write only after all component validation succeeds.
COMPONENT.write_text(
    component,
    encoding="utf-8",
)

CSS.write_text(
    css,
    encoding="utf-8",
)

print("EDGEIQ_TRACK_CONDITION_AND_SHARP_MAP_V1_APPLIED")
print("removed=TRACK_CONDITION_SOURCE_LABELS")
print("renamed=PENETROMETER_AVERAGE_TO_PENETROMETER")
print("renamed=RAIN_7D_TO_RAIN_7_DAYS")
print("renamed=IRRIGATION_7D_TO_IRRIGATION_7_DAYS")
print("units=RAINFALL_AND_IRRIGATION_MM")
print("conditional=GOING_STICK_AND_MOISTURE")
print("map_render=NATIVE_SIZE_CONTAIN")
print(f"component={COMPONENT}")
print(f"css={CSS}")
