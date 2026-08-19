from __future__ import annotations

import re
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

RESOLVER = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "services"
    / "trackMapAssets.ts"
)

CSS = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "styles"
    / "edgeiqOsV2.css"
)

PUBLIC_MAPS = ROOT / "public" / "track-maps"

png_files = sorted(PUBLIC_MAPS.glob("*.png"))

if len(png_files) != 69:
    raise RuntimeError(
        f"Expected 69 installed track maps, found {len(png_files)}. "
        "No source files were written."
    )


def normalise(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


# ============================================================
# 1. CREATE RESOLVER DIRECTLY FROM THE 69 INSTALLED FILES
# ============================================================

asset_rows: list[tuple[str, str, str]] = []

for path in png_files:
    display = path.stem.replace("_", " ")
    key = normalise(display)
    asset_rows.append((key, display, f"/track-maps/{path.name}"))

aliases = {
    "GEELONG": "GEELONGTURF",
    "GEELONGSYNTH": "GEELONGSYNTHETIC",

    "PAKENHAM": "PAKENHAMTYNONGTURF",
    "PAKENHAMTURF": "PAKENHAMTYNONGTURF",
    "PAKENHAMSYNTH": "PAKENHAMTYNONGSYNTHETIC",
    "PAKENHAMSYNTHETIC": "PAKENHAMTYNONGSYNTHETIC",
    "PAKENHAMTYNONG": "PAKENHAMTYNONGTURF",

    "MOUNTWYCHEPROOF": "MTWYCHEPROOF",

    "SANDOWNHILLSIDE": "SANDOWN",
    "SANDOWNLAKESIDE": "SANDOWN",
    "SANDOWNH": "SANDOWN",
    "SANDOWNL": "SANDOWN",

    "THEVALLEY": "MOONEEVALLEY",
    "MOONEEVALLEYRACECOURSE": "MOONEEVALLEY",
}

resolver_lines = [
    "export type EdgeiqTrackMapAsset = {",
    "  canonicalTrack: string;",
    "  assetPath: string;",
    "};",
    "",
    "const TRACK_MAP_ASSETS: Record<string, EdgeiqTrackMapAsset> = {",
]

for key, display, asset_path in asset_rows:
    resolver_lines.append(
        f'  {key}: {{ canonicalTrack: "{display}", '
        f'assetPath: "{asset_path}" }},'
    )

resolver_lines.extend([
    "};",
    "",
    "const TRACK_MAP_ALIASES: Record<string, string> = {",
])

for alias, target in sorted(aliases.items()):
    resolver_lines.append(f'  {alias}: "{target}",')

resolver_lines.extend([
    "};",
    "",
    "function normaliseTrackKey(value: unknown): string {",
    '  return String(value ?? "")',
    "    .trim()",
    "    .toUpperCase()",
    '    .replace(/&/g, "AND")',
    '    .replace(/\\bRACECOURSE\\b/g, "")',
    '    .replace(/\\bRACING\\b/g, "")',
    '    .replace(/\\bVICTORIA\\b/g, "")',
    '    .replace(/\\bVIC\\b/g, "")',
    '    .replace(/[^A-Z0-9]/g, "");',
    "}",
    "",
    "export function resolveTrackMapAsset(",
    "  trackName: unknown,",
    "  surfaceName?: unknown,",
    "): EdgeiqTrackMapAsset | null {",
    "  const trackKey = normaliseTrackKey(trackName);",
    "  const surfaceKey = normaliseTrackKey(surfaceName);",
    "  const combinedKey = `${trackKey}${surfaceKey}`;",
    "",
    "  const combinedAlias = TRACK_MAP_ALIASES[combinedKey];",
    "  const trackAlias = TRACK_MAP_ALIASES[trackKey];",
    "",
    "  return (",
    "    TRACK_MAP_ASSETS[combinedKey] ??",
    "    (combinedAlias ? TRACK_MAP_ASSETS[combinedAlias] : undefined) ??",
    "    TRACK_MAP_ASSETS[trackKey] ??",
    "    (trackAlias ? TRACK_MAP_ASSETS[trackAlias] : undefined) ??",
    "    null",
    "  );",
    "}",
    "",
    "export function resolveTrackMapPath(",
    "  trackName: unknown,",
    "  surfaceName?: unknown,",
    "): string | null {",
    "  return resolveTrackMapAsset(trackName, surfaceName)?.assetPath ?? null;",
    "}",
    "",
])

RESOLVER.write_text(
    "\n".join(resolver_lines),
    encoding="utf-8",
)


# ============================================================
# 2. PATCH CONFIRMED LIVE TRACK COMPONENT
# ============================================================

component = COMPONENT.read_text(encoding="utf-8")
original_component = component

resolver_import = (
    'import { resolveTrackMapPath } '
    'from "../services/trackMapAssets";\n'
)

if resolver_import not in component:
    imports = list(
        re.finditer(
            r"^import .*?;\r?\n",
            component,
            flags=re.MULTILINE,
        )
    )

    if not imports:
        raise RuntimeError(
            "Import block not found. No component file was written."
        )

    insert_at = imports[-1].end()

    component = (
        component[:insert_at]
        + resolver_import
        + component[insert_at:]
    )


# Remove the track/status/generated timestamp line.
old_header_text = '''        <p>
          {model.trackName} / {statusText(model.status)}
          {model.generatedAt ? ` / ${model.generatedAt}` : ""}
        </p>
'''

count = component.count(old_header_text)

if count != 1:
    raise RuntimeError(
        f"Expected one Track header metadata block, found {count}. "
        "No component file was written."
    )

component = component.replace(
    old_header_text,
    "",
    1,
)


# Remove Inspection Time and Track Manager from the visible fields.
old_field_grid = '      <FieldGrid items={model.officialFields} />\n'

new_field_grid = '''      <FieldGrid
        items={model.officialFields.filter(
          (item) =>
            !["INSPECTION TIME", "TRACK MANAGER"].includes(
              item.label.trim().toUpperCase(),
            ),
        )}
      />
'''

count = component.count(old_field_grid)

if count != 1:
    raise RuntimeError(
        f"Expected one official FieldGrid render, found {count}. "
        "No component file was written."
    )

component = component.replace(
    old_field_grid,
    new_field_grid,
    1,
)


# Replace only the confirmed TrackMapPanel function.
map_start_marker = (
    "function TrackMapPanel({ model }: "
    "{ model: MeetingTrackViewModel }) {"
)

map_start = component.find(map_start_marker)
map_end = component.find(
    "\nfunction TrackDetails(",
    map_start,
)

if map_start < 0 or map_end < 0:
    raise RuntimeError(
        "Confirmed TrackMapPanel boundaries were not found. "
        "No component file was written."
    )

new_map_panel = '''function TrackMapPanel({ model }: { model: MeetingTrackViewModel }) {
  const installedMap = resolveTrackMapPath(
    model.trackName,
    model.map.courseType,
  );

  return (
    <section className="eiq-track-v1-panel eiq-track-v1-map-panel">
      <header>
        <span>Rail Position and Track Map</span>
        <strong>
          {valueOrUnavailable(
            model.context.find(
              (item) => item.label === "Current Rail Position",
            )?.value,
          )}
        </strong>
      </header>

      {installedMap ? (
        <figure className="eiq-track-v1-map">
          <img
            src={installedMap}
            alt={`${model.trackName} track map`}
          />
        </figure>
      ) : (
        <div className="eiq-track-v1-unavailable">
          <strong>Track map unavailable.</strong>
          <p>No installed Victorian track map matches this meeting.</p>
        </div>
      )}
    </section>
  );
}
'''

component = (
    component[:map_start]
    + new_map_panel
    + component[map_end:]
)


# Remove only the two unwanted visible panel renders.
for target, label in (
    (
        "            <TrackDetails model={model} />\n",
        "TrackDetails render",
    ),
    (
        "        <OperationalRail model={model} />\n",
        "OperationalRail render",
    ),
):
    count = component.count(target)

    if count != 1:
        raise RuntimeError(
            f"Expected one {label}, found {count}. "
            "No component file was written."
        )

    component = component.replace(
        target,
        "",
        1,
    )


# Validate the exact requested changes.
for forbidden in (
    "model.generatedAt ?",
    "model.map.asset",
    "<figcaption>",
    "<TrackDetails model={model} />",
    "<OperationalRail model={model} />",
):
    if forbidden in component:
        raise RuntimeError(
            f"Old visible Track content still remains: {forbidden}"
        )

for required in (
    'from "../services/trackMapAssets"',
    "resolveTrackMapPath(",
    'src={installedMap}',
    '"INSPECTION TIME"',
    '"TRACK MANAGER"',
):
    if required not in component:
        raise RuntimeError(
            f"Required Track change was not installed: {required}"
        )

if component == original_component:
    raise RuntimeError(
        "No Track component changes were produced."
    )


# ============================================================
# 3. APPEND FULL-WIDTH MAP CSS
# ============================================================

css = CSS.read_text(encoding="utf-8")

css_marker = "/* EDGEIQ TRACK MAPS FINAL V1 */"

css_block = r'''

/* EDGEIQ TRACK MAPS FINAL V1 */
.eiq-track-v1-layout {
  display: block !important;
}

.eiq-track-v1-stack {
  width: 100%;
  min-width: 0;
}

.eiq-track-v1-grid {
  display: block !important;
}

.eiq-track-v1-map-panel {
  width: 100%;
  min-width: 0;
}

.eiq-track-v1-map {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 360px;
  margin: 0;
  padding: 20px;
  overflow: hidden;
  background: #ffffff;
}

.eiq-track-v1-map img {
  display: block;
  width: 100%;
  height: auto;
  max-height: 520px;
  object-fit: contain;
  object-position: center;
}
'''

if css_marker not in css:
    css = css.rstrip() + css_block + "\n"


# Write only after every validation succeeds.
COMPONENT.write_text(
    component,
    encoding="utf-8",
)

CSS.write_text(
    css,
    encoding="utf-8",
)

print("EDGEIQ_TRACK_MAPS_FINAL_V1_APPLIED")
print("resolver_created=1")
print(f"resolved_assets={len(png_files)}")
print("removed=HEADER_TIMESTAMP")
print("removed=INSPECTION_TIME")
print("removed=TRACK_MANAGER")
print("removed=MAP_CAPTION")
print("removed=TRACK_DETAILS_RENDER")
print("removed=OPERATIONAL_RAIL_RENDER")
print("map_source=PUBLIC_TRACK_MAPS")
print(f"component={COMPONENT}")
print(f"resolver={RESOLVER}")
print(f"css={CSS}")
