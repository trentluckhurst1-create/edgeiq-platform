from __future__ import annotations

from collections import defaultdict

from edgeiq_results_common_v1 import DATA, numeric_float, read_csv, write_csv


INP = DATA / "edgeiq_pricing_engine_research_v1.csv"
OUT = DATA / "edgeiq_pricing_engine_research_audit_v1.csv"
SUMMARY = DATA / "edgeiq_pricing_engine_research_audit_summary_v1.csv"


def main() -> None:
    groups = defaultdict(list)
    rows = list(read_csv(INP)) if INP.exists() else []
    for row in rows:
        groups[(row["race_date"], row["track"], row["race_no"])].append(row)
    audit_rows = []
    missing_prices = 0
    low_data = 0
    diffs = []
    extremes = []
    for key, race_rows in groups.items():
        prob_sum = sum(numeric_float(row.get("blended_probability", "")) or 0.0 for row in race_rows)
        audit_rows.append(
            {
                "race_date": key[0],
                "track": key[1],
                "race_no": key[2],
                "runners": len(race_rows),
                "probability_sum": round(prob_sum, 6),
                "probability_sum_status": "PASS" if abs(prob_sum - 1.0) <= 0.001 else "CHECK",
            }
        )
        for row in race_rows:
            if not row.get("research_price"):
                missing_prices += 1
            if row.get("pricing_mode") == "LOW_DATA_MARKET_ANCHOR":
                low_data += 1
            delta = numeric_float(row.get("price_delta", ""))
            if delta is not None:
                diffs.append(abs(delta))
                if abs(delta) >= 10:
                    extremes.append(row)
    write_csv(OUT, audit_rows, ["race_date", "track", "race_no", "runners", "probability_sum", "probability_sum_status"])
    summary = {
        "races_priced": len(groups),
        "runners_priced": len(rows),
        "probability_sum_pass_races": sum(1 for r in audit_rows if r["probability_sum_status"] == "PASS"),
        "probability_sum_check_races": sum(1 for r in audit_rows if r["probability_sum_status"] == "CHECK"),
        "missing_prices": missing_prices,
        "low_data_runners": low_data,
        "average_abs_model_vs_production_price_delta": round(sum(diffs) / len(diffs), 4) if diffs else "",
        "extreme_price_examples": len(extremes),
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(audit_rows)} races)")


if __name__ == "__main__":
    main()
