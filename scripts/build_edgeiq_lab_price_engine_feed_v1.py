from __future__ import annotations

from edgeiq_results_common_v1 import DATA, read_csv, write_csv


PRICING = DATA / "edgeiq_pricing_engine_research_v1.csv"
LPP = DATA / "edgeiq_lengths_per_point_engine_v1.csv"
OUT = DATA / "edgeiq_lab_price_engine_feed_v1.csv"
SUMMARY = DATA / "edgeiq_lab_price_engine_feed_summary_v1.csv"

FIELDS = [
    "race_date",
    "track",
    "race_no",
    "runner",
    "base_rating",
    "editable_rating",
    "rating_point_to_lengths",
    "rating_adjustment_points",
    "rating_adjustment_lengths",
    "base_probability",
    "adjusted_probability",
    "base_price",
    "adjusted_price",
    "data_confidence",
    "market_anchor_weight",
    "pricing_status",
]


def default_lpp() -> str:
    values = []
    for row in read_csv(LPP):
        if row.get("fallback_level") == "DISTANCE" and row.get("rating_point_to_lengths"):
            values.append(float(row["rating_point_to_lengths"]))
    return f"{sum(values) / len(values):.4f}" if values else "0.7500"


def main() -> None:
    lpp = default_lpp()
    rows = []
    for row in read_csv(PRICING):
        rows.append(
            {
                "race_date": row.get("race_date", ""),
                "track": row.get("track", ""),
                "race_no": row.get("race_no", ""),
                "runner": row.get("runner", ""),
                "base_rating": row.get("projected_rating", ""),
                "editable_rating": row.get("user_adjusted_rating", ""),
                "rating_point_to_lengths": lpp,
                "rating_adjustment_points": 0,
                "rating_adjustment_lengths": 0,
                "base_probability": row.get("blended_probability", ""),
                "adjusted_probability": row.get("blended_probability", ""),
                "base_price": row.get("research_price", ""),
                "adjusted_price": row.get("research_price", ""),
                "data_confidence": row.get("data_confidence", ""),
                "market_anchor_weight": row.get("market_confidence_weight", ""),
                "pricing_status": row.get("pricing_status", ""),
            }
        )
    write_csv(OUT, rows, FIELDS)
    summary = {
        "lab_feed_rows": len(rows),
        "races": len({(r["race_date"], r["track"], r["race_no"]) for r in rows}),
        "default_rating_point_to_lengths": lpp,
        "research_only": "YES",
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
