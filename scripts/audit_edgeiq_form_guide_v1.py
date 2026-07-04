from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
OUT = ROOT / "public" / "data" / "edgeiq_form_guide_v1_audit.csv"


def main() -> None:
    src = SRC.read_text(encoding="utf-8", errors="replace")
    required_columns = ["NO", "HORSE", "BAR", "WGT", "JOCKEY", "TRAINER", "EPI", "EDGEIQ PRICE", "MARKET", "STATUS"]
    weight_fields = ["weight", "allocated_weight", "handicap_weight", "weight_carried", "runner_weight", "weight_kg", "wgt"]
    checks = [
        ("edgeiq_form_guide_present", "EDGEiQ Form Guide" in src),
        ("required_form_guide_columns_present", all(col in src for col in required_columns)),
        ("row_expansion_logic_present", "edgeiq-form-guide-expansion" in src and "aria-expanded" in src),
        ("last_5_starts_logic_present", "slice(0, 5)" in src and "Last 5 starts" in src),
        ("full_history_modal_present", "Full Career History" in src and "setFullHistoryRunner" in src),
        ("weight_fallback_fields_referenced", all(field in src for field in weight_fields)),
        ("no_invented_form_data_text", "Recent form not available" in src and "invent" not in src.lower()),
    ]
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": "OK" if ok else "missing"} for name, ok in checks]
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)
    failures = [row for row in rows if row["status"] == "FAIL"]
    print(f"Form Guide audit: PASS={len(rows) - len(failures)} FAIL={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
