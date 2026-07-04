from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
OUT = ROOT / "public" / "data" / "edgeiq_runner_history_modal_v1_audit.csv"


def main() -> None:
    src = SRC.read_text(encoding="utf-8", errors="replace")
    css = CSS.read_text(encoding="utf-8", errors="replace")
    history_cols = ["DATE", "TRACK", "DIST", "CLASS", "GOING", "BAR", "JOCKEY", "POS", "MARGIN", "SP", "EPI", "SETTLED / RUN STYLE"]
    summary_fields = ["Starts", "Wins", "Places", "Win %", "Place %", "Peak EPI", "Average EPI"]
    checks = [
        ("full_history_trigger_exists", "Full History" in src and "Open full career history" in src),
        ("modal_state_exists", "fullHistoryRunner" in src and "setFullHistoryRunner" in src),
        ("close_button_exists", "Close" in src and "setFullHistoryRunner(null)" in src),
        ("career_summary_fields_exist", all(field in src for field in summary_fields)),
        ("full_history_table_columns_exist", all(col in src for col in history_cols)),
        ("fallback_text_exists", "Full career history not available" in src),
        ("scrollable_dark_modal_styling_exists", "edgeiq-career-modal" in css and "overflow: auto" in css),
        ("trainer_jockey_header_exists", all(token in src for token in ["trainer_name", "jockey_name", "rider"])),
    ]
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": "OK" if ok else "missing"} for name, ok in checks]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)
    failures = [row for row in rows if row["status"] == "FAIL"]
    print(f"Runner history modal audit: PASS={len(rows) - len(failures)} FAIL={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
