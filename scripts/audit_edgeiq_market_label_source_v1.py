from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_market_label_source_v1_audit.csv"


def main() -> None:
    src = SRC.read_text(encoding="utf-8", errors="replace")
    forbidden_visible = ["TAB Price", "TAB reference", "TAB status", "tab market"]
    checks = [
        ("no_customer_facing_tab_labels", not any(token in src for token in forbidden_visible)),
        ("market_label_exists", "MARKET" in src and "Market Feed" in src),
        ("ladbrokes_probe_outputs_exist_if_probe_ran", (DATA / "ladbrokes_market_api_probe_v1.csv").exists() and (DATA / "ladbrokes_market_api_probe_v1_summary.csv").exists()),
        ("racingcom_race_list_fallback_still_referenced", "raceListRows" in src and "FILES.raceList" in src),
        ("product_shell_uses_runner_rows_and_race_list_rows", "productShellRaces" in src and "runnerRows" in src and "raceListRows" in src),
    ]
    rows = [{"check": name, "status": "PASS" if ok else "FAIL", "detail": "OK" if ok else "missing"} for name, ok in checks]
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)
    failures = [row for row in rows if row["status"] == "FAIL"]
    print(f"Market label/source audit: PASS={len(rows) - len(failures)} FAIL={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
