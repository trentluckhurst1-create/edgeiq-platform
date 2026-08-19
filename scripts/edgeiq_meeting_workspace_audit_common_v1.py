from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEETING = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
WEATHER = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWeatherWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
PUBLIC_DATA = ROOT / "public" / "data"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def run_audit(name: str, required_status: str, checks: dict[str, bool], report_stem: str) -> None:
    PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    lines = [required_status if all(checks.values()) else f"{name}_AUDIT_FAIL", ""]
    for key, passed in checks.items():
        lines.append(f"{key}: {'PASS' if passed else 'FAIL'}")

    txt = PUBLIC_DATA / f"{report_stem}.txt"
    js = PUBLIC_DATA / f"{report_stem}.json"
    txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    js.write_text(
        json.dumps(
            {
                "audit": name,
                "status": required_status if all(checks.values()) else "FAIL",
                "checks": checks,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(required_status if all(checks.values()) else f"{name}_AUDIT_FAIL")
    if not all(checks.values()):
        raise SystemExit(1)
