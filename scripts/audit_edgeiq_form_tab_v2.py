from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
OUT = ROOT / "public" / "data" / "edgeiq_form_tab_v2_audit.csv"


def main() -> None:
    src = SRC.read_text(encoding="utf-8", errors="replace")
    css = CSS.read_text(encoding="utf-8", errors="replace")
    checks = [
        ("oversized_metric_card_layout_removed", "edgeiq-form-clean-summary" not in src and "Expected" not in src[src.find("edgeiq-form-study-v2"):src.find("intelMode === \"RUNNERS\"")]),
        ("last_five_runs_table_exists", "Last Five Runs" in src and all(col in src for col in ["Date", "Track", "Dist", "Class", "Going", "Bar", "Jockey", "Pos", "Margin", "SP", "EPI", "Settled / Run Style"])),
        ("selected_runner_header_exists", "edgeiq-form-study-header" in src and "FORM STUDY" in src),
        ("heatmap_trajectory_strip_exists", "edgeiq-form-trajectory-strip" in src and "epi-heat-cell" in src),
        ("build_compatible_markers", "edgeiq-form-study-v2" in src and "edgeiq-form-study-v2" in css),
    ]
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": "OK" if ok else "missing"} for name, ok in checks]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)
    failures = [row for row in rows if row["status"] == "FAIL"]
    print(f"Form tab v2 audit: PASS={len(rows) - len(failures)} FAIL={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
