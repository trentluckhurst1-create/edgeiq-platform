import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE = DATA / "edgeiq_opportunity_score_v1.csv"
OUT = DATA / "edgeiq_opportunity_score_distribution_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_opportunity_score_distribution_summary_v1.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def num(value: object) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return 0.0


def main() -> None:
    rows = read_csv(SOURCE)
    scores = [num(row.get("opportunity_score")) for row in rows]
    sorted_scores = sorted(scores)
    detail = []
    for row in rows:
        score = num(row.get("opportunity_score"))
        pct_rank = 0 if not sorted_scores else sum(1 for value in sorted_scores if value <= score) / len(sorted_scores)
        detail.append(
            {
                **row,
                "percentile_rank": f"{pct_rank:.3f}",
                "distribution_bucket": "TOP_DECILE" if pct_rank >= 0.9 else "TOP_QUARTILE" if pct_rank >= 0.75 else "MID_FIELD" if pct_rank >= 0.25 else "LOW_QUARTILE",
            }
        )
    write_csv(OUT, detail, list(detail[0].keys()) if detail else ["race_date", "track", "race_no"])

    band_counts = Counter(row.get("opportunity_band", "") for row in rows)
    summary = [
        {"metric": "race_rows", "value": len(rows)},
        {"metric": "min_score", "value": f"{min(scores) if scores else 0:.2f}"},
        {"metric": "max_score", "value": f"{max(scores) if scores else 0:.2f}"},
        {"metric": "score_spread", "value": f"{(max(scores) - min(scores)) if scores else 0:.2f}"},
        {"metric": "high_opportunity_races", "value": band_counts.get("HIGH OPPORTUNITY", 0)},
        {"metric": "live_opportunity_races", "value": band_counts.get("LIVE OPPORTUNITY", 0)},
        {"metric": "separation_verdict", "value": "GOOD" if scores and max(scores) - min(scores) >= 5 and band_counts.get("HIGH OPPORTUNITY", 0) else "NEEDS_MORE_SEPARATION"},
    ]
    for band, count in sorted(band_counts.items()):
        summary.append({"metric": f"band::{band}", "value": count})
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT}")
    print(f"Wrote {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
