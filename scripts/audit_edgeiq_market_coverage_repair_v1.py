from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
APPLY = DATA / "edgeiq_market_coverage_repair_v1_apply.json"
MARKET_TERMINAL = DATA / "edgeiq_market_terminal_feed_v1.csv"
OUT_JSON = DATA / "edgeiq_market_coverage_repair_v1_audit.json"
OUT_TXT = DATA / "edgeiq_market_coverage_repair_v1_audit.txt"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    if not APPLY.exists():
        raise FileNotFoundError(APPLY)
    if not MARKET_TERMINAL.exists():
        raise FileNotFoundError(MARKET_TERMINAL)

    apply_report = json.loads(APPLY.read_text(encoding="utf-8"))
    rows = read_csv(MARKET_TERMINAL)
    terminal_rows = len(rows)
    market_rows = sum(1 for row in rows if (row.get("market") or "").strip())
    edgeiq_price_rows = sum(1 for row in rows if (row.get("edgeiq_price") or "").strip())
    open_rows = sum(1 for row in rows if (row.get("open") or "").strip())
    move_rows = sum(1 for row in rows if (row.get("move") or "").strip())
    failures: list[str] = []

    if terminal_rows != int(apply_report.get("terminal_rows", -1)):
        failures.append("TERMINAL_ROW_COUNT_CHANGED_AFTER_APPLY")
    if terminal_rows > 10000:
        failures.append("TERMINAL_FEED_OVER_FRONTEND_LIMIT")
    if market_rows != int(apply_report.get("after_market_rows", -1)):
        failures.append("MARKET_COVERAGE_MISMATCH")
    if edgeiq_price_rows != int(apply_report.get("after_edgeiq_price_rows", -1)):
        failures.append("EDGEIQ_PRICE_COVERAGE_MISMATCH")
    if apply_report.get("action") == "NO_FEED_CHANGE" and int(apply_report.get("recovered_rows", -1)) != 0:
        failures.append("NO_FEED_CHANGE_WITH_RECOVERED_ROWS")

    marker = "EDGEIQ_MARKET_COVERAGE_REPAIR_V1_AUDIT_PASS" if not failures else "EDGEIQ_MARKET_COVERAGE_REPAIR_V1_AUDIT_FAIL"
    audit = {
        "marker": marker,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "terminal_rows": terminal_rows,
        "market_rows": market_rows,
        "edgeiq_price_rows": edgeiq_price_rows,
        "open_rows": open_rows,
        "move_rows": move_rows,
        "action": apply_report.get("action"),
        "reason": apply_report.get("reason"),
        "source_state": {
            "sportsbet_dates": apply_report.get("sportsbet_source", {}).get("dates", []),
            "sportsbet_runner_matches": apply_report.get("sportsbet_source", {}).get("runner_matches", 0),
            "tab_dates": apply_report.get("tab_source", {}).get("dates", []),
            "tab_runner_matches": apply_report.get("tab_source", {}).get("runner_matches", 0),
            "form_enriched_dates": apply_report.get("form_enriched_source", {}).get("dates", []),
            "form_enriched_runner_matches": apply_report.get("form_enriched_source", {}).get("runner_matches", 0),
        },
        "unavailable_reasons": apply_report.get("unavailable_reasons", {}),
    }

    OUT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                marker,
                f"status={audit['status']}",
                f"terminal_rows={terminal_rows}",
                f"market_rows={market_rows}",
                f"edgeiq_price_rows={edgeiq_price_rows}",
                f"open_rows={open_rows}",
                f"move_rows={move_rows}",
                f"action={audit['action']}",
                f"reason={audit['reason']}",
                f"failures={','.join(failures) if failures else 'none'}",
            ]
        ),
        encoding="utf-8",
    )
    print(marker)
    if failures:
        raise SystemExit("; ".join(failures))


if __name__ == "__main__":
    main()
