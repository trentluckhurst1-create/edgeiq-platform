from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src" / "edgeiq-os" / "race" / "components"
CHECKPOINT_ROOT = PROJECT_ROOT / "checkpoints"

FILES = {
    "scratchings": SRC / "MeetingScratchingsWorkspace.tsx",
    "track": SRC / "MeetingTrackWorkspace.tsx",
    "results": SRC / "MeetingResultsWorkspace.tsx",
}


def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def checkpoint(files: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = CHECKPOINT_ROOT / f"edgeiq_recent_workspace_regression_fixes_v1_{stamp}"
    dest.mkdir(parents=True, exist_ok=False)
    for source in files:
        target = dest / source.relative_to(PROJECT_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return dest


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one occurrence, found {count}")
    return source.replace(old, new, 1)


def fix_scratchings(source: str) -> str:
    original = source
    source = replace_once(source, "\n      <SummaryStrip model={model} />", "", "remove scratchings summary strip render")
    source = replace_once(source, "\n      <TimelinePanel model={model} />", "", "remove scratchings operational timeline render")
    source = replace_once(source, "\n      <DataStatusPanel model={model} />", "", "remove scratchings data status render")

    export_body = source[source.find("export function MeetingScratchingsWorkspace") :]
    forbidden = ["<SummaryStrip", "<TimelinePanel", "<DataStatusPanel", "DATA FRESHNESS"]
    leaked = [item for item in forbidden if item in export_body]
    if leaked:
        raise RuntimeError(f"scratchings render still exposes forbidden UI: {leaked}")
    if source == original:
        raise RuntimeError("scratchings source was unchanged")
    return source


def fix_track(source: str) -> str:
    original = source
    source = replace_once(source, "\n                <th>SOURCE</th>", "", "remove track pattern source heading")
    source = replace_once(source, "\n                  <td>{valueOrUnavailable(row.source)}</td>", "", "remove track pattern source cell")

    start = source.find("function PatternAnalysis")
    end = source.find("\nfunction historicalMetricLabel", start)
    pattern = source[start:end]
    if "SOURCE" in pattern or "row.source" in pattern:
        raise RuntimeError("track pattern analysis still exposes source data")
    if source == original:
        raise RuntimeError("track source was unchanged")
    return source


def fix_results(source: str) -> str:
    original = source
    source = source.replace('return "â€”";', 'return "-";')
    source = source.replace('return "Ã¢â‚¬â€\x9d";', 'return "-";')
    source = replace_once(
        source,
        '  if (!value) return <span>Pending speed data</span>;',
        '  if (!value) return <span>-</span>;',
        "replace missing sectional pending copy",
    )
    if "Pending speed data" in source:
        raise RuntimeError("results source still contains repeated pending sectional copy")
    if source == original:
        raise RuntimeError("results source was unchanged")
    return source


def main() -> int:
    originals = {name: read(path) for name, path in FILES.items()}
    updated = {
        "scratchings": fix_scratchings(originals["scratchings"]),
        "track": fix_track(originals["track"]),
        "results": fix_results(originals["results"]),
    }

    changed = [FILES[name] for name in updated if updated[name] != originals[name]]
    if not changed:
        raise RuntimeError("No source changes required")

    checkpoint_path = checkpoint(changed)
    for name, content in updated.items():
        if content != originals[name]:
            FILES[name].write_text(content, encoding="utf-8")

    print("EDGEIQ_RECENT_WORKSPACE_REGRESSION_FIXES_V1_APPLIED")
    print(f"checkpoint={checkpoint_path}")
    for path in changed:
        print(f"changed={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
