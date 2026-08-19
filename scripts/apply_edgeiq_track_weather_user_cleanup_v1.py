from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

TRACK = (
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


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def find_weather_workspace() -> Path:
    matches: list[Path] = []

    component_root = (
        ROOT
        / "src"
        / "edgeiq-os"
        / "race"
        / "components"
    )

    for path in component_root.glob("*.tsx"):
        text = read(path)

        if "Meeting weather and race-day conditions" in text:
            matches.append(path)

    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one Weather workspace, found {len(matches)}: "
            f"{[str(path) for path in matches]}"
        )

    return matches[0]


def remove_function_render(
    source: str,
    component_name: str,
) -> tuple[str, int]:
    pattern = re.compile(
        rf"^[ \t]*<{re.escape(component_name)}"
        rf"(?:\s+[^<>]*?)?\s*/>[ \t]*\r?\n",
        flags=re.MULTILINE,
    )

    return pattern.subn("", source, count=1)


def remove_jsx_aside_containing(
    source: str,
    marker: str,
) -> tuple[str, int]:
    marker_position = source.find(marker)

    if marker_position < 0:
        return source, 0

    aside_start = source.rfind("<aside", 0, marker_position)

    if aside_start < 0:
        return source, 0

    token_pattern = re.compile(
        r"</?aside(?:\s[^<>]*?)?>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    depth = 0

    for match in token_pattern.finditer(source, aside_start):
        token = match.group(0)

        if token.startswith("</"):
            depth -= 1

            if depth == 0:
                end = match.end()

                while end < len(source) and source[end] in " \t":
                    end += 1

                if end < len(source) and source[end] == "\r":
                    end += 1

                if end < len(source) and source[end] == "\n":
                    end += 1

                return source[:aside_start] + source[end:], 1
        else:
            depth += 1

    raise RuntimeError(
        f"Could not balance Weather aside containing: {marker}"
    )


# ============================================================
# TRACK WORKSPACE
# ============================================================

track = read(TRACK)
original_track = track


# Add one display-label helper immediately before HistoricalComparison.
historical_marker = (
    "function HistoricalComparison"
    "({ model }: { model: MeetingTrackViewModel }) {"
)

helper = '''function historicalMetricLabel(value: string): string {
  const key = value.trim().toUpperCase();

  if (key === "INSIDE WIN %") return "Inner Barrier Win %";
  if (key === "MIDDLE WIN %") return "Middle Barrier Win %";
  if (key === "WIDE WIN %") return "Outside Barrier Win %";

  return value;
}

'''

if "function historicalMetricLabel(" not in track:
    position = track.find(historical_marker)

    if position < 0:
        raise RuntimeError(
            "HistoricalComparison function was not found."
        )

    track = track[:position] + helper + track[position:]


old_historical_rows = '''            {model.historicalRows.map((row) => (
              <tr key={row.metric}>
                <td className="is-left"><strong>{row.metric}</strong></td>
                <td>{valueOrUnavailable(row.today)}</td>
                <td>{valueOrUnavailable(row.last3Meetings)}</td>
                <td>{valueOrUnavailable(row.last10Meetings)}</td>
              </tr>
            ))}
'''

new_historical_rows = '''            {model.historicalRows
              .filter(
                (row) =>
                  ![
                    "LANE DISTRIBUTION",
                    "SETTLING POSITION DISTRIBUTION",
                  ].includes(row.metric.trim().toUpperCase()),
              )
              .map((row) => (
                <tr key={row.metric}>
                  <td className="is-left">
                    <strong>{historicalMetricLabel(row.metric)}</strong>
                  </td>
                  <td>{valueOrUnavailable(row.today)}</td>
                  <td>{valueOrUnavailable(row.last3Meetings)}</td>
                  <td>{valueOrUnavailable(row.last10Meetings)}</td>
                </tr>
              ))}
'''

count = track.count(old_historical_rows)

if count != 1:
    raise RuntimeError(
        f"Expected one Historical Comparison row map, found {count}."
    )

track = track.replace(
    old_historical_rows,
    new_historical_rows,
    1,
)


track, notes_render_count = remove_function_render(
    track,
    "TrackNotes",
)

if notes_render_count != 1:
    raise RuntimeError(
        f"Expected one TrackNotes render, removed {notes_render_count}."
    )


for required in (
    '"Inner Barrier Win %"',
    '"Middle Barrier Win %"',
    '"Outside Barrier Win %"',
    '"LANE DISTRIBUTION"',
    '"SETTLING POSITION DISTRIBUTION"',
    "historicalMetricLabel(row.metric)",
):
    if required not in track:
        raise RuntimeError(
            f"Required Track change was not installed: {required}"
        )

if "<TrackNotes model={model} />" in track:
    raise RuntimeError("Track Notes panel render still remains.")

if track == original_track:
    raise RuntimeError("No Track workspace changes were produced.")


# ============================================================
# WEATHER WORKSPACE
# ============================================================

WEATHER = find_weather_workspace()

weather = read(WEATHER)
original_weather = weather


# Remove title metadata paragraph containing generatedAt/status data.
weather, metadata_count = re.subn(
    r'''
    [ \t]*<p>\s*
    (?:
      (?!</p>).
    )*
    model\.(?:generatedAt|trackName|meetingName|status)
    (?:
      (?!</p>).
    )*
    </p>\s*
    ''',
    "",
    weather,
    count=1,
    flags=re.DOTALL | re.VERBOSE,
)

if metadata_count == 0:
    # Fallback for the exact visual line when the model fields differ.
    weather, metadata_count = re.subn(
        r'''
        [ \t]*<p>\s*
        \{[^{}]*(?:meeting|track)[^{}]*\}
        .*?
        \{[^{}]*(?:generatedAt|updatedAt|status)[^{}]*\}
        .*?
        </p>\s*
        ''',
        "",
        weather,
        count=1,
        flags=re.DOTALL | re.VERBOSE | re.IGNORECASE,
    )


# Remove the developer-facing partial-shell message.
weather = re.sub(
    r'''
    [ \t]*<p[^>]*>\s*
    Partial\ shell\ remains\ visible\ so\ source\ gaps\ are\ auditable\.
    \s*</p>\s*
    ''',
    "",
    weather,
    count=1,
    flags=re.IGNORECASE | re.VERBOSE,
)


# Remove source captions such as "Official weather feed".
weather = re.sub(
    r'''
    [ \t]*
    \{
      [^{}\n]*source[^{}\n]*
      \?
      \s*<small[^>]*>
      .*?
      </small>
      \s*:\s*null
    \}
    ''',
    "",
    weather,
    flags=re.DOTALL | re.IGNORECASE | re.VERBOSE,
)

weather = re.sub(
    r'''
    [ \t]*<small[^>]*>
    \s*(?:Official\ weather\ feed|[^<>{}]*weather\ feed)\s*
    </small>\s*
    ''',
    "",
    weather,
    flags=re.IGNORECASE | re.VERBOSE,
)


# Remove the Source and Updated At entries from arrays used by summary cards.
weather = re.sub(
    r'''
    ^[ \t]*
    \[
      \s*["'`](?:SOURCE|UPDATED\ AT)["'`]
      \s*,.*?
    \],
    [ \t]*\r?\n
    ''',
    "",
    weather,
    flags=re.MULTILINE | re.IGNORECASE | re.VERBOSE,
)


# Remove the circled descriptive header text.
for label in (
    "Official meeting facts",
    "Meeting-day weather table",
    "Builder-owned impact context",
):
    weather = re.sub(
        rf'''
        [ \t]*<strong[^>]*>\s*
        {re.escape(label)}
        \s*</strong>\s*
        ''',
        "",
        weather,
        count=1,
        flags=re.IGNORECASE | re.VERBOSE,
    )


# Remove only the explanatory hourly-unavailable sentence.
weather = re.sub(
    r'''
    [ \t]*<p[^>]*>\s*
    Hourly\ meeting\ weather\ has\ not\ been\ supplied
    \s+by\ the\ governed\ weather\ feed\.
    \s*</p>\s*
    ''',
    "",
    weather,
    count=1,
    flags=re.IGNORECASE | re.VERBOSE,
)


# Remove a conventional OperationalRail render when present.
weather, operational_render_count = remove_function_render(
    weather,
    "OperationalRail",
)

# If the right rail is rendered directly, remove the aside containing Source State.
weather, source_aside_count = remove_jsx_aside_containing(
    weather,
    "Source State",
)

# A second separate aside may contain Weather Notes.
weather, notes_aside_count = remove_jsx_aside_containing(
    weather,
    "Weather Notes",
)


# Validation of visible requested removals.
for forbidden in (
    "Partial shell remains visible so source gaps are auditable.",
    "Official meeting facts",
    "Meeting-day weather table",
    "Builder-owned impact context",
    "Hourly meeting weather has not been supplied by the governed weather feed.",
    "<OperationalRail model={model} />",
):
    if forbidden in weather:
        raise RuntimeError(
            f"Visible Weather content still remains: {forbidden}"
        )

if weather == original_weather:
    raise RuntimeError("No Weather workspace changes were produced.")


# ============================================================
# CSS
# ============================================================

css = read(CSS)

css_marker = "/* EDGEIQ TRACK WEATHER USER CLEANUP V1 */"

css_block = r'''

/* EDGEIQ TRACK WEATHER USER CLEANUP V1 */
.eiq-weather-v1-layout {
  display: block !important;
  grid-template-columns: minmax(0, 1fr) !important;
}

.eiq-weather-v1-main,
.eiq-weather-v1-stack {
  width: 100%;
  min-width: 0;
}

.eiq-weather-v1-summary,
.eiq-weather-v1-grid {
  width: 100%;
}

.eiq-weather-v1-summary small,
.eiq-weather-v1-field-grid small {
  display: none !important;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"


# Write only after every validation passes.
TRACK.write_text(track, encoding="utf-8")
WEATHER.write_text(weather, encoding="utf-8")
CSS.write_text(css, encoding="utf-8")

print("EDGEIQ_TRACK_WEATHER_USER_CLEANUP_V1_APPLIED")
print("track_removed=LANE_DISTRIBUTION")
print("track_removed=SETTLING_POSITION_DISTRIBUTION")
print("track_removed=TRACK_NOTES_PANEL")
print("track_renamed=INNER_BARRIER_WIN_PERCENT")
print("track_renamed=MIDDLE_BARRIER_WIN_PERCENT")
print("track_renamed=OUTSIDE_BARRIER_WIN_PERCENT")
print("weather_removed=HEADER_METADATA")
print("weather_removed=PARTIAL_SHELL_MESSAGE")
print("weather_removed=SOURCE_CAPTIONS")
print("weather_removed=SOURCE_AND_UPDATED_AT_FIELDS")
print("weather_removed=SOURCE_STATE_RAIL")
print("weather_removed=WEATHER_NOTES_RAIL")
print("weather_removed=DEVELOPER_HEADER_LABELS")
print(f"track={TRACK}")
print(f"weather={WEATHER}")
print(f"css={CSS}")
