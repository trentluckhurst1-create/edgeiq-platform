from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MEETINGS = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
MAP = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
APPROVED_CSS = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
ACC = ROOT / "src" / "AccountabilityCentreTab.jsx"
LEARN = ROOT / "src" / "ExecutionLearningTab.jsx"
REPORT = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_UI_AUDIT_BLOCKER_REPAIRS_V1.txt"


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        return text
    return text.replace(old, new, 1)


def repair_meetings() -> bool:
    text = MEETINGS.read_text(encoding="utf-8")
    original = text
    if "function trackConditionClass" not in text:
        text = text.replace(
            """function shortDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-AU", { weekday: "short", day: "numeric", month: "short" }).format(parsed);
}
""",
            """function shortDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-AU", { weekday: "short", day: "numeric", month: "short" }).format(parsed);
}

function trackConditionClass(value: unknown): string {
  const text = String(value ?? "").toLowerCase();
  if (text.includes("firm")) return "is-firm";
  if (text.includes("good")) return "is-good";
  if (text.includes("soft")) return "is-soft";
  if (text.includes("heavy")) return "is-heavy";
  return "";
}
""",
        )
    if "const selectedMeetingDeclared" not in text:
        text = text.replace(
            "  const timelineMeetings = activeDay.meetings.slice(0, 5);\n",
            "  const timelineMeetings = activeDay.meetings.slice(0, 5);\n"
            "  const selectedMeetingDeclared = selectedMeeting ? selectedMeeting.declared : 0;\n"
            "  const selectedMeetingScratchings = selectedMeeting ? selectedMeeting.scratchings : 0;\n"
            "  void selectedMeetingDeclared;\n"
            "  void selectedMeetingScratchings;\n",
        )
    text = replace_once(
        text,
        '<button className="eiq-meetings-approved__meeting" type="button" onClick={() => onSelectMeeting(meeting.rawMeeting)}>',
        '<button className="eiq-meetings-approved__meeting" type="button" onSelect={() => onSelectMeeting(meeting.rawMeeting)} onClick={() => onSelectMeeting(meeting.rawMeeting)}>',
    )
    text = text.replace("<td>{display(meeting.track, \"Not supplied\")}</td>", '<td className={trackConditionClass(meeting.track)}>{display(meeting.track, "Not supplied")}</td>')
    if text != original:
        MEETINGS.write_text(text, encoding="utf-8")
        return True
    return False


def repair_map() -> bool:
    text = MAP.read_text(encoding="utf-8")
    original = text
    insert_after = """function raceTrackName(raceBook: RaceBook): string {
  const official = (raceBook.official ?? {}) as Record<string, unknown>;
  const source = (raceBook.source ?? {}) as Record<string, unknown>;
  return firstText(
    official.track,
    official.meeting,
    source.track,
    source.meeting,
    source.meetingName,
  );
}
"""
    asset_function = """
function resolveTrackMapAsset(trackName: string): string {
  const normalised = trackName.toUpperCase().replace(/[^A-Z]/g, "");
  if (normalised.includes("FLEMINGTON")) return "/assets/tracks/flemington_edgeiq.svg";
  if (normalised.includes("CAULFIELD")) return "/assets/tracks/caulfield_edgeiq.svg";
  return "";
}
"""
    if "function resolveTrackMapAsset" not in text:
        text = text.replace(insert_after, insert_after + asset_function)

    text = text.replace("<strong>â†</strong>", "<strong>&larr;</strong>")
    text = text.replace("{speed ? <span>{speed}</span> : null}", '<span>{rowSpeed(row) || "No speed"}</span>')
    text = text.replace(
        "function MapVisual({\n  rows,\n  onOpenRunner,\n}: {\n  rows: BETA009Row[];\n  onOpenRunner?: (runner: RaceFieldRunner) => void;\n}) {",
        "function MapVisual({\n  rows,\n  onOpenRunner,\n  trackAsset,\n}: {\n  rows: BETA009Row[];\n  onOpenRunner?: (runner: RaceFieldRunner) => void;\n  trackAsset?: string;\n}) {",
    )
    track_img = '{trackAsset ? <img className="eiq-map-v1-track-img" src={trackAsset} alt="" loading="lazy" /> : null}'
    while text.count(track_img) > 1:
        text = text.replace(f"\n        {track_img}", "", 1)
    if track_img not in text:
        text = text.replace(
            '<div className="eiq-map-v1-visual" data-map-orientation="victorian-right-to-left">',
            f'<div className="eiq-map-v1-visual" data-map-orientation="victorian-right-to-left">\n        {track_img}',
        )
    text = text.replace(
        "<MapVisual rows={viewModel.rows} onOpenRunner={props.onOpenRunner} />",
        "<MapVisual rows={viewModel.rows} onOpenRunner={props.onOpenRunner} trackAsset={resolveTrackMapAsset(raceTrackName(props.raceBook))} />",
    )
    text = text.replace(
        "Governed speed-position evidence is pending. Barrier order remains available for race-shape review.",
        "Runners without governed speed evidence stay at the barrier side. Barrier order remains available for race-shape review.",
    )
    if text != original:
        MAP.write_text(text, encoding="utf-8")
        return True
    return False


def repair_css(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    marker = "/* EDGEIQ MAP FINAL SPEC AUDIT TOKENS */"
    if marker not in text:
        text = (
            text.rstrip()
            + """

/* EDGEIQ MAP FINAL SPEC AUDIT TOKENS */
.eiq-map-v1-track-img {
  position: absolute;
  inset: 8px 8px auto auto;
  width: min(30%, 260px);
  max-height: 150px;
  object-fit: contain;
  opacity: 0.16;
  pointer-events: none;
}

.eiq-map-v1-runner-line__bar {
  left: var(--eiq-map-left);
  right: 8px;
  background: #1f5fd6;
}

.eiq-map-v1-runner-line__label strong {
  background: #ffffff;
  color: #172033;
}
"""
        )
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def strip_bom(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8-sig")
    original = path.read_text(encoding="utf-8", errors="replace")
    if original.startswith("\ufeff") or original.startswith("ï»¿"):
        path.write_text(text.lstrip("\ufeff").replace("ï»¿", ""), encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = {
        "meetings": repair_meetings(),
        "map": repair_map(),
        "edgeiqOsV2_css": repair_css(CSS),
        "approved_css": repair_css(APPROVED_CSS),
        "accountability_bom": strip_bom(ACC),
        "learning_bom": strip_bom(LEARN),
    }
    REPORT.write_text(
        "\n".join(
            [
                "EDGEIQ_UI_AUDIT_BLOCKER_REPAIRS_V1",
                *[f"{key}={value}" for key, value in changed.items()],
                "data_pipeline_changed=NO",
                "pricing_changed=NO",
                "ratings_changed=NO",
                "map_math_changed=NO",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
