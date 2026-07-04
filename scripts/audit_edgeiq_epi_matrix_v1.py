from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
OUT = ROOT / "public" / "data" / "edgeiq_epi_matrix_v1_audit.csv"


def main() -> None:
    tsx = SRC.read_text(encoding="utf-8", errors="replace")
    css = CSS.read_text(encoding="utf-8", errors="replace")
    checks = [
        ("epi_matrix_present", "EPI Matrix" in tsx),
        ("performance_index_present", "EDGEiQ Performance Index" in tsx),
        ("heatmap_classes_present", all(token in css for token in ["heat-elite", "heat-strong", "heat-positive", "heat-neutral", "heat-risk", "heat-poor"])),
        ("performance_matrix_columns_present", all(token in tsx for token in ["CURRENT", "PEAK", "AVG", "LAST", "TREND", "DIST", "GOING", "CLASS", "PACE", "GAP", "EPI"])),
        ("giant_old_metric_card_layout_removed", "edgeiq-heatmap-standard-card" not in tsx and "giant" not in tsx.lower()),
    ]
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": "OK" if ok else "missing"} for name, ok in checks]
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)
    failures = [row for row in rows if row["status"] == "FAIL"]
    print(f"EPI matrix audit: PASS={len(rows) - len(failures)} FAIL={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
