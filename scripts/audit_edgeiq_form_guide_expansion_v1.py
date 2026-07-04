from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
OUT = ROOT / "public" / "data" / "edgeiq_form_guide_expansion_v1_audit.csv"


def main() -> None:
    src = SRC.read_text(encoding="utf-8", errors="replace")
    required_columns = ["NO", "HORSE", "BAR", "WGT", "JOCKEY", "TRAINER", "EPI", "EDGEIQ PRICE", "MARKET", "STATUS"]
    checks = [
        ("row_expansion_state_exists", "selectedKey" in src and "setSelectedKey" in src),
        ("click_handler_exists", "onClick={() => setSelectedKey(isOpen ? \"\" : rowKey)}" in src and "aria-expanded={isOpen}" in src),
        ("last_five_starts_rendering_exists", "formCardsFor" in src and "slice(0, 5)" in src and "Last 5 starts" in src),
        ("recent_form_unavailable_fallback_exists", "Recent form not available" in src),
        ("form_guide_columns_still_exist", all(col in src for col in required_columns)),
        ("summary_strip_exists", all(label in src for label in ["Current EPI", "Peak EPI", "Average EPI", "Last Start EPI", "Preferred Style"])),
        ("build_compatible_markers", "edgeiq-form-guide-expansion" in src and "edgeiq-form-guide-cards" in src),
    ]
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": "OK" if ok else "missing"} for name, ok in checks]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)
    failures = [row for row in rows if row["status"] == "FAIL"]
    print(f"Form Guide expansion audit: PASS={len(rows) - len(failures)} FAIL={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
