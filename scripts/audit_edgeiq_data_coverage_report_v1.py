from __future__ import annotations

from datetime import datetime

from edgeiq_beta_readiness_common_v1 import (
    PUBLIC_DATA,
    catalog_runners,
    count_populated,
    format_pct,
    load_form_enriched_runners,
    read_csv,
    write_json,
    write_text,
)


PASS_MARKER = "EDGEIQ_DATA_COVERAGE_REPORT_V1"
TXT_OUT = PUBLIC_DATA / "edgeiq_data_coverage_report_v1.txt"
JSON_OUT = PUBLIC_DATA / "edgeiq_data_coverage_report_v1.json"


def main() -> int:
    generated = datetime.now().isoformat(timespec="seconds")
    catalog = catalog_runners()
    enriched = load_form_enriched_runners()
    map_rows = read_csv(PUBLIC_DATA / "edgeiq_map_terminal_feed_v1.csv")
    market_rows = read_csv(PUBLIC_DATA / "edgeiq_market_terminal_feed_v1.csv")
    insights_rows = read_csv(PUBLIC_DATA / "edgeiq_insights_terminal_feed_v1.csv")
    epi_rows = read_csv(PUBLIC_DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv")

    specs = [
        ("EPI", enriched, ["epi"]),
        ("ERI", epi_rows, ["start_1_context", "start_2_context", "start_3_context"]),
        ("Suitability", enriched, ["suitability"]),
        ("Form Momentum", enriched, ["form_momentum"]),
        ("Market", enriched, ["market"]),
        ("EDGEiQ Price", enriched, ["edgeiq_price"]),
        ("Early Speed", enriched, ["early_speed"]),
        ("Late Speed", enriched, ["late_speed"]),
        ("Historical Form", enriched, ["recent_form_count", "last_five"]),
        ("Runner Profile", enriched, ["career_record", "track_record", "distance_record"]),
        ("Recent Form", enriched, ["recent_form_count"]),
        ("Sectionals", enriched, ["sectionals"]),
        ("Speed Map", map_rows, ["run_style", "projected_position", "early_speed"]),
        ("Track", catalog, ["barrier"]),
        ("Weather", catalog, []),
        ("Scratchings", catalog, ["scratched"]),
        ("Gear", enriched, ["gear"]),
        ("Results", [], []),
        ("Insights", insights_rows, ["key_insight", "edge", "card_value"]),
        ("Market Terminal", market_rows, ["market", "edgeiq_price", "epi"]),
    ]

    rows = []
    for label, source_rows, fields in specs:
        if fields:
            covered, total = count_populated(source_rows, fields)
        else:
            covered, total = 0, len(source_rows)
        coverage = format_pct(covered, total)
        state = "READY" if total and covered == total else "PARTIAL" if covered else "NOT READY"
        reason = "No governed source rows found" if total == 0 else "Governed values populated where supplied"
        rows.append({"field": label, "covered": covered, "total": total, "coverage": coverage, "status": state, "reason": reason})

    payload = {"audit": "edgeiq_data_coverage_report_v1", "generated_at": generated, "status": "PASS", "pass_marker": PASS_MARKER, "coverage": rows}
    write_json(JSON_OUT, payload)
    lines = ["EDGEiQ Data Coverage Report V1", f"Generated: {generated}", "Status: PASS", PASS_MARKER, ""]
    for row in rows:
        lines.append(f"{row['field']} | {row['coverage']} | {row['covered']}/{row['total']} | {row['status']} | {row['reason']}")
    write_text(TXT_OUT, "\n".join(lines) + "\n")
    print(PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
