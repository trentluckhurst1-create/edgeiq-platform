from pathlib import Path
import csv
from edgeiq_pricing_research_common import DATA, ROOT, write_csv, race_key, clean

OUT = DATA / "edgeiq_pricing_replay_source_inventory_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_pricing_replay_source_inventory_summary_v1.csv"
TERMS = ("result", "replay", "rating", "probability", "fair", "price", "market", "sp", "runner_board", "warehouse", "calibration")


def has_any(fields, needles):
    return "YES" if any(any(n in f.lower() for n in needles) for f in fields) else "NO"


def usefulness(fields):
    low = [f.lower() for f in fields]
    if any("finish" in f or f == "won" or "winner" in f for f in low) and any(f in low or "sp" in f for f in ["sp", "market_price"]):
        return "RESULT_SPINE"
    if any("prob" in f for f in low):
        return "PROBABILITY_SOURCE"
    if any("rating" in f for f in low):
        return "RATING_SOURCE"
    if any("fair" in f for f in low):
        return "FAIR_PRICE_SOURCE"
    if any("market" in f or f == "sp" for f in low):
        return "MARKET_SOURCE"
    return "NOT_USEFUL"


def sample_csv(path, limit=5000):
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for idx, row in enumerate(reader):
            if idx >= limit:
                break
            rows.append(row)
        return list(reader.fieldnames or []), rows


def line_count(path):
    try:
        with path.open("rb") as handle:
            return max(0, sum(1 for _ in handle) - 1)
    except OSError:
        return 0


def main():
    files = [p for p in DATA.glob("*.csv") if any(t in p.name.lower() for t in TERMS)]
    out = []
    for p in sorted(files, key=lambda x: x.name.lower()):
        fields, rows = sample_csv(p)
        total_rows = line_count(p)
        dates = [r.get("race_date") or r.get("meeting_date") or r.get("date") for r in rows if r.get("race_date") or r.get("meeting_date") or r.get("date")]
        races = {race_key(r) for r in rows if race_key(r)[0] and race_key(r)[2]}
        runners = {(*race_key(r), clean(r.get("horse"))) for r in rows if race_key(r)[0] and race_key(r)[2] and clean(r.get("horse"))}
        join_quality = "GOOD" if has_any(fields, ["date"]) == "YES" and has_any(fields, ["track"]) == "YES" and has_any(fields, ["race_no", "race_number"]) == "YES" and has_any(fields, ["horse"]) == "YES" else "POOR"
        out.append({
            "file_name": p.name, "rows": total_rows, "date_coverage": f"{min(dates) if dates else ''}..{max(dates) if dates else ''}",
            "race_count": len(races), "runner_count": len(runners),
            "has_result": has_any(fields, ["finish", "result"]), "has_won": has_any(fields, ["won", "winner"]),
            "has_sp": has_any(fields, ["sp"]), "has_market_price": has_any(fields, ["market_price", "closing_price", "fixed_odds"]),
            "has_rating": has_any(fields, ["rating"]), "has_probability": has_any(fields, ["probability", "prob"]),
            "has_fair_price": has_any(fields, ["fair_price", "rated_price"]), "has_field_size": has_any(fields, ["field_size"]),
            "has_track": has_any(fields, ["track"]), "has_race_no": has_any(fields, ["race_no", "race_number"]), "has_horse": has_any(fields, ["horse"]),
            "join_key_quality": join_quality, "usefulness": usefulness(fields),
        })
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    summary = [{"metric": "candidate_files", "value": len(out)}]
    for kind in sorted(set(r["usefulness"] for r in out)):
        summary.append({"metric": f"usefulness::{kind}", "value": sum(1 for r in out if r["usefulness"] == kind)})
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
