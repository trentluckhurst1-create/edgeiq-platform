from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
INPUT_DNA = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
INPUT_BET_QUALITY = DATA / "edgeiq_live_bet_quality_v1_1.csv"

OUT = DATA / "edgeiq_confidence_breakdown_v1.csv"
SUMMARY = DATA / "edgeiq_confidence_breakdown_v1_summary.csv"


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def upper(v):
    return clean(v).upper()


def to_float(v, default=None):
    try:
        txt = clean(v)
        if txt == "":
            return default
        return float(txt)
    except Exception:
        return default


def csv_rows(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def norm_track(row):
    return upper(row.get("track")) or upper(row.get("_track"))


def norm_race_no(row):
    return clean(row.get("race_no")) or clean(row.get("_race"))


def norm_race_date(row):
    return clean(row.get("race_date")) or clean(row.get("_date"))


def horse_name(row):
    return clean(row.get("horse")) or clean(row.get("_horse"))


def horse_key(row):
    return upper(row.get("horse_key")) or upper(row.get("horse_canon")) or upper(horse_name(row))


def join_key(row):
    return (norm_race_date(row), norm_track(row), norm_race_no(row), horse_key(row))


def is_scratched(row):
    vals = [
        upper(row.get("is_scratched")),
        upper(row.get("scratch_status")),
        upper(row.get("runner_status")),
    ]
    return any(v in {"TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHING"} for v in vals)


def first_float(row, cols, default=None):
    for c in cols:
        v = to_float(row.get(c), None)
        if v is not None:
            return v
    return default


def first_clean(row, cols, default=""):
    for c in cols:
        v = clean(row.get(c))
        if v:
            return v
    return default


def clamp(v, low=0, high=100):
    try:
        return max(low, min(high, float(v)))
    except Exception:
        return 0


def populated(row, cols):
    return sum(1 for c in cols if clean(row.get(c)) != "")


def merge_sources(board_rows, dna_rows, bet_rows):
    dna_index = {join_key(r): r for r in dna_rows}
    bet_index = {join_key(r): r for r in bet_rows}

    merged = []
    for r in board_rows:
        key = join_key(r)
        nr = dict(r)

        for source_row in [dna_index.get(key, {}), bet_index.get(key, {})]:
            for k, v in source_row.items():
                if k not in nr or clean(nr.get(k)) == "":
                    nr[k] = v

        merged.append(nr)

    return merged


def projection_confidence(row):
    direct = first_float(row, ["projection_confidence_v5_2", "projection_confidence_V6_1_RESEARCH"], None)
    gap = first_float(row, ["projection_gap_V6_1_RESEARCH", "projection_gap_v5_2"], None)
    rating = first_float(row, ["projected_rating_V6_1_RESEARCH", "projected_rating_v5_2"], None)

    if direct is not None:
        if direct <= 1:
            direct *= 100
        return round(clamp(direct), 2)

    score = 45
    if rating is not None:
        score += 20
    if gap is not None:
        score += min(25, abs(gap) * 3)
    return round(clamp(score), 2)


def profile_confidence(row):
    dna = first_float(row, ["dna_confidence", "dna_v6_2_score", "dna_score"], None)
    fit_count = populated(row, ["distance_fit_score", "condition_fit_score", "class_fit_score"])
    profile_count = populated(row, ["dna_v6_2_band", "profile_score", "form_score", "rating_score", "sectional_score"])

    if dna is not None:
        base = dna if dna > 1 else dna * 100
    else:
        base = 35

    base += fit_count * 7
    base += profile_count * 4
    return round(clamp(base), 2)


def market_confidence(row):
    live = first_float(row, ["live_price", "display_live_price", "tab_fixed_win", "tab_tote_win"], None)
    source = first_clean(row, ["live_price_source", "tab_live_price_source", "bookmaker", "market_source_status"])
    market_state = upper(first_clean(row, ["market_state", "tab_fixed_betting_status", "tab_tote_betting_status"]))
    age = first_float(row, ["market_source_age_seconds"], None)
    rows = first_float(row, ["market_source_rows"], None)

    score = 35
    if live is not None and live > 1:
        score += 30
    if source:
        score += 10
    if any(x in market_state for x in ["OPEN", "BETTING", "READY", "NORMAL"]):
        score += 10
    if rows is not None and rows > 0:
        score += 5
    if age is not None:
        if age <= 300:
            score += 10
        elif age <= 900:
            score += 5
        elif age > 3600:
            score -= 15

    return round(clamp(score), 2)


def data_quality_score(row):
    key_cols = [
        "race_date", "track", "race_no", "horse", "horse_key",
        "fair_price", "win_pct", "V6_1_RESEARCH_probability",
        "projected_rating_V6_1_RESEARCH", "projection_gap_V6_1_RESEARCH",
        "settling_band", "run_style", "barrier", "jockey", "trainer",
    ]
    have = populated(row, key_cols)
    score = (have / len(key_cols)) * 100
    return round(clamp(score), 2)


def connection_confidence(row):
    score = 30

    if clean(row.get("trainer")):
        score += 15
    if clean(row.get("jockey")):
        score += 15

    for col in ["strongest_factor_v6_2", "weakest_factor_v6_2", "positive_1_factor", "negative_1_factor"]:
        if clean(row.get(col)):
            score += 5

    for col in ["distance_fit_score", "condition_fit_score", "class_fit_score"]:
        v = first_float(row, [col], None)
        if v is not None:
            score += 5

    return round(clamp(score), 2)


def final_confidence(row, parts):
    direct = first_float(row, ["confidence_score"], None)
    if direct is not None:
        if direct <= 1:
            direct *= 100
        return round(clamp(direct), 2)

    weighted = (
        parts["projection"] * 0.30 +
        parts["profile"] * 0.25 +
        parts["market"] * 0.20 +
        parts["data"] * 0.15 +
        parts["connection"] * 0.10
    )
    return round(clamp(weighted), 2)


def confidence_band(score):
    if score >= 80:
        return "HIGH"
    if score >= 65:
        return "SOLID"
    if score >= 50:
        return "MODERATE"
    if score >= 35:
        return "LOW"
    return "WEAK"


def explanation(parts, final, band):
    weakest = min(parts.items(), key=lambda x: x[1])
    strongest = max(parts.items(), key=lambda x: x[1])
    return (
        f"{band} confidence. Strongest component is {strongest[0]} {round(strongest[1], 1)}. "
        f"Weakest component is {weakest[0]} {round(weakest[1], 1)}. "
        f"Final confidence {round(final, 1)} uses existing confidence where available; otherwise explanatory decomposition."
    )


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    board_rows = csv_rows(INPUT_BOARD)
    dna_rows = csv_rows(INPUT_DNA)
    bet_rows = csv_rows(INPUT_BET_QUALITY)

    merged_rows = merge_sources(board_rows, dna_rows, bet_rows)
    active_rows = [r for r in merged_rows if not is_scratched(r)]

    out_rows = []
    band_counts = {}

    for r in active_rows:
        parts = {
            "projection": projection_confidence(r),
            "profile": profile_confidence(r),
            "market": market_confidence(r),
            "data": data_quality_score(r),
            "connection": connection_confidence(r),
        }

        final = final_confidence(r, parts)
        band = confidence_band(final)
        band_counts[band] = band_counts.get(band, 0) + 1

        out_rows.append({
            "race_date": norm_race_date(r),
            "track": norm_track(r),
            "race_no": norm_race_no(r),
            "horse": horse_name(r),
            "horse_key": horse_key(r),
            "projection_confidence_score": parts["projection"],
            "profile_confidence_score": parts["profile"],
            "market_confidence_score": parts["market"],
            "data_quality_score": parts["data"],
            "connection_confidence_score": parts["connection"],
            "final_confidence_score": final,
            "confidence_band": band,
            "confidence_explanation": explanation(parts, final, band),
            "source_method": "EXPLANATORY_DECOMPOSITION_NOT_MODEL_INPUT",
            "built_at": built_at,
        })

    fields = [
        "race_date", "track", "race_no", "horse", "horse_key",
        "projection_confidence_score", "profile_confidence_score",
        "market_confidence_score",
        "data_quality_score", "connection_confidence_score",
        "final_confidence_score", "confidence_band", "confidence_explanation",
        "source_method", "built_at",
    ]

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    summary_rows = [
        {"metric": "status", "value": "CONFIDENCE_BREAKDOWN_V1_BUILT"},
        {"metric": "input_board_rows", "value": len(board_rows)},
        {"metric": "input_dna_rows", "value": len(dna_rows)},
        {"metric": "input_bet_quality_rows", "value": len(bet_rows)},
        {"metric": "active_runner_rows", "value": len(active_rows)},
        {"metric": "output_rows", "value": len(out_rows)},
        {"metric": "built_at", "value": built_at},
    ]

    for k, v in sorted(band_counts.items()):
        summary_rows.append({"metric": f"band_{k}", "value": v})

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary_rows)

    print("[CONFIDENCE_BREAKDOWN_V1] COMPLETE")
    print(f"rows={len(out_rows)}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
