from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
OUT = ROOT / "public" / "data" / "edgeiq_epi_matrix_v2_audit.csv"


def write(rows: list[dict[str, str]]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    tsx = SRC.read_text(encoding="utf-8", errors="replace")
    css = CSS.read_text(encoding="utf-8", errors="replace")
    required_cols = ["NO", "HORSE", "EPI", "CURRENT", "PEAK", "AVG", "LAST", "TREND", "GAP", "L5", "L4", "L3", "L2", "L1", "DIST", "GOING", "CLASS", "PACE"]
    heat_classes = ["epi-heat-cell", "epi-heat-elite", "epi-heat-strong", "epi-heat-positive", "epi-heat-neutral", "epi-heat-risk", "epi-heat-poor"]
    checks = [
        ("epi_matrix_title_exists", "EPI Matrix" in tsx),
        ("heatmap_classes_exist", all(token in css and token in tsx for token in heat_classes)),
        ("l5_l1_columns_exist", all(token in tsx for token in ["L5", "L4", "L3", "L2", "L1"])),
        ("matrix_columns_exist", all(token in tsx for token in required_cols)),
        ("old_giant_metric_card_layout_not_dominant", "edgeiq-heatmap-standard-card" not in tsx and "metric-card-only" not in tsx.lower()),
        ("npm_build_compatible_marker", "edgeiq-epi-matrix-row" in tsx and "edgeiq-epi-matrix-row" in css),
    ]
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": "OK" if ok else "missing"} for name, ok in checks]
    write(rows)
    failures = [row for row in rows if row["status"] == "FAIL"]
    print(f"EPI matrix v2 audit: PASS={len(rows) - len(failures)} FAIL={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
