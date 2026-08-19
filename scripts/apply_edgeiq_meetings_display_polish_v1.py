from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

service_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "services"
    / "meetingsFeed.ts"
)

css_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "styles"
    / "edgeiqOsV2.css"
)

service_text = service_path.read_text(encoding="utf-8")
css_text = css_path.read_text(encoding="utf-8")

formatter_anchor = '''function formatGeneratedAt(value: string): string {
  return formatLocalTime(value) || "Not supplied";
}
'''

formatter_replacement = '''function formatGeneratedAt(value: string): string {
  return formatLocalTime(value) || "Not supplied";
}

function formatOfficialUpdate(value: unknown): string {
  const text = usable(value);
  if (!text) return "Not supplied";

  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return text;

  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Australia/Melbourne",
    timeZoneName: "short",
  }).format(parsed);
}
'''

if "function formatOfficialUpdate" not in service_text:
    if formatter_anchor not in service_text:
        raise RuntimeError(
            "Official-update formatter insertion anchor not found. "
            "No files were modified."
        )

    service_text = service_text.replace(
        formatter_anchor,
        formatter_replacement,
        1,
    )

official_update_anchor = '''function officialUpdate(race: ThreeDayRace | undefined, catalog: ThreeDayCatalog): string {
  return firstText(race?.source?.built_at, catalog.generatedAt) || "Not supplied";
}
'''

official_update_replacement = '''function officialUpdate(race: ThreeDayRace | undefined, catalog: ThreeDayCatalog): string {
  const sourceTimestamp = firstText(
    race?.source?.built_at,
    catalog.generatedAt,
  );

  return formatOfficialUpdate(sourceTimestamp);
}
'''

if official_update_anchor not in service_text:
    if "return formatOfficialUpdate(sourceTimestamp);" not in service_text:
        raise RuntimeError(
            "Official-update function anchor not found. "
            "No files were modified."
        )
else:
    service_text = service_text.replace(
        official_update_anchor,
        official_update_replacement,
        1,
    )

css_marker = "/* EDGEIQ MEETINGS DISPLAY POLISH V1 */"

css_block = r'''

/* EDGEIQ MEETINGS DISPLAY POLISH V1 */
.eiq-meetings-engineering__table-scroll {
  overflow-x: auto;
  scrollbar-gutter: stable;
}

.eiq-meetings-engineering__table {
  width: max-content;
  min-width: 1740px;
  table-layout: fixed;
}

.eiq-meetings-engineering__table th,
.eiq-meetings-engineering__table td {
  box-sizing: border-box;
  padding-left: 12px;
  padding-right: 12px;
  white-space: normal;
  overflow-wrap: normal;
  word-break: normal;
}

.eiq-meetings-engineering__table th {
  white-space: nowrap;
}

/* SELECT */
.eiq-meetings-engineering__table th:nth-child(1),
.eiq-meetings-engineering__table td:nth-child(1) {
  width: 86px;
}

/* MEETING */
.eiq-meetings-engineering__table th:nth-child(2),
.eiq-meetings-engineering__table td:nth-child(2) {
  width: 170px;
}

/* STATE */
.eiq-meetings-engineering__table th:nth-child(3),
.eiq-meetings-engineering__table td:nth-child(3) {
  width: 82px;
}

/* RAIL */
.eiq-meetings-engineering__table th:nth-child(4),
.eiq-meetings-engineering__table td:nth-child(4) {
  width: 110px;
}

/* TRACK */
.eiq-meetings-engineering__table th:nth-child(5),
.eiq-meetings-engineering__table td:nth-child(5) {
  width: 112px;
}

/* WEATHER */
.eiq-meetings-engineering__table th:nth-child(6),
.eiq-meetings-engineering__table td:nth-child(6) {
  width: 126px;
}

/* WIND */
.eiq-meetings-engineering__table th:nth-child(7),
.eiq-meetings-engineering__table td:nth-child(7) {
  width: 118px;
}

/* TEMP */
.eiq-meetings-engineering__table th:nth-child(8),
.eiq-meetings-engineering__table td:nth-child(8) {
  width: 104px;
}

/* RACES */
.eiq-meetings-engineering__table th:nth-child(9),
.eiq-meetings-engineering__table td:nth-child(9) {
  width: 76px;
}

/* DECLARED */
.eiq-meetings-engineering__table th:nth-child(10),
.eiq-meetings-engineering__table td:nth-child(10) {
  width: 96px;
}

/* SCRATCHINGS */
.eiq-meetings-engineering__table th:nth-child(11),
.eiq-meetings-engineering__table td:nth-child(11) {
  width: 112px;
}

/* FIRST */
.eiq-meetings-engineering__table th:nth-child(12),
.eiq-meetings-engineering__table td:nth-child(12) {
  width: 92px;
}

/* LAST */
.eiq-meetings-engineering__table th:nth-child(13),
.eiq-meetings-engineering__table td:nth-child(13) {
  width: 92px;
}

/* STATUS */
.eiq-meetings-engineering__table th:nth-child(14),
.eiq-meetings-engineering__table td:nth-child(14) {
  width: 110px;
}

/* EDGEIQ READ */
.eiq-meetings-engineering__table th:nth-child(15),
.eiq-meetings-engineering__table td:nth-child(15) {
  width: 220px;
}

/* OPEN */
.eiq-meetings-engineering__table th:nth-child(16),
.eiq-meetings-engineering__table td:nth-child(16) {
  width: 92px;
}

.eiq-meetings-engineering__rail dd {
  max-width: 58%;
  text-align: right;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.eiq-meetings-engineering__rail dl div:last-child dd {
  font-variant-numeric: tabular-nums;
}
'''

if css_marker not in css_text:
    css_text = css_text.rstrip() + css_block + "\n"

service_path.write_text(service_text, encoding="utf-8")
css_path.write_text(css_text, encoding="utf-8")

print("EDGEIQ_MEETINGS_DISPLAY_POLISH_V1_APPLIED")
print(f"service={service_path}")
print(f"css={css_path}")
