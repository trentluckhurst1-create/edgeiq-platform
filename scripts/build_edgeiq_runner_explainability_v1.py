from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
INPUT_DNA = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
INPUT_BET_QUALITY = DATA / "edgeiq_live_bet_quality_v1_1.csv"

OUT = DATA / "edgeiq_runner_explainability_v1.csv"
SUMMARY = DATA / "edgeiq_runner_explainability_v1_summary.csv"


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


def to_int(v, default=None):
    try:
        txt = clean(v)
        if txt == "":
            return default
        return int(float(txt))
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


def first_float(row, cols, default=""):
    for c in cols:
        v = to_float(row.get(c), None)
        if v is not None:
            return v
    return default


def first_clean(row, cols, default=""):
    for c in cols:
        v = clean(row.get(c))
        if v != "":
            return v
    return default


def model_rank(row):
    for col in ["V6_1_RESEARCH_price_rank", "fair_rank", "edge_rank", "live_rank"]:
        val = to_int(row.get(col), None)
        if val is not None:
            return val
    return ""


def fair_price(row):
    return first_float(row, ["fair_price", "display_fair_price", "ui_fair_price", "V6_1_RESEARCH_fair_price"], "")


def live_price(row):
    return first_float(row, ["live_price", "display_live_price", "tab_fixed_win", "tab_tote_win"], "")


def win_pct(row):
    val = first_float(row, ["win_pct", "V6_1_RESEARCH_probability", "v3_probability"], "")
    if val == "":
        return ""
    if val <= 1:
        return round(val * 100, 2)
    return round(val, 2)


def edge_pct(row):
    val = first_float(row, ["edge_pct", "display_edge_pct", "ui_edge_pct", "bet_quality_overlay_pct_v1_1"], "")
    if val == "":
        return ""
    return round(val, 2)


def score_strength_factor(label, value, neutral=50, high_good=True, suffix=""):
    if value == "":
        return None
    try:
        v = float(value)
    except Exception:
        return None

    if high_good:
        strength = v - neutral
    else:
        strength = neutral - v

    return {
        "label": label,
        "value": f"{round(v, 2)}{suffix}",
        "score": strength,
        "raw": v,
    }


def gap_factor(row):
    v = first_float(row, ["projection_gap_V6_1_RESEARCH", "projection_gap_v5_2"], "")
    if v == "":
        return None
    return {
        "label": "Projection Gap",
        "value": f"{round(v, 2)}",
        "score": float(v) * 5,
        "raw": float(v),
    }


def edge_factor(row):
    v = edge_pct(row)
    if v == "":
        return None
    return {
        "label": "Value Edge",
        "value": f"{round(float(v), 2)}%",
        "score": float(v),
        "raw": float(v),
    }


def dna_named_factor(row, prefix, idx, positive=True):
    factor = clean(row.get(f"{prefix}_{idx}_factor"))
    impact = clean(row.get(f"{prefix}_{idx}_impact"))
    if not factor:
        return None
    score = 8 if positive else -8
    return {
        "label": factor,
        "value": impact,
        "score": score,
        "raw": score,
    }


def build_factor_lists(row):
    positives = []
    risks = []

    possible_positive = [
        gap_factor(row),
        edge_factor(row),
        score_strength_factor("Runner Profile DNA", first_float(row, ["dna_v6_2_score", "dna_score"], ""), 50),
        score_strength_factor("Distance Fit", first_float(row, ["distance_fit_score"], ""), 50),
        score_strength_factor("Condition Fit", first_float(row, ["condition_fit_score"], ""), 50),
        score_strength_factor("Class Fit", first_float(row, ["class_fit_score"], ""), 50),
        score_strength_factor("Sectionals", first_float(row, ["sectional_weapon_score", "sectional_score_component_v1_1", "sectional_score"], ""), 50),
        score_strength_factor("Late Power", first_float(row, ["late_power_index"], ""), 50),
        score_strength_factor("Projected Speed", first_float(row, ["projected_spd", "early_speed_rating"], ""), 50),
        score_strength_factor("Bet Quality", first_float(row, ["bet_quality_score_v1_1"], ""), 50),
        score_strength_factor("Confidence", first_float(row, ["confidence_score", "projection_confidence_v5_2"], ""), 50),
        dna_named_factor(row, "positive", 1, True),
        dna_named_factor(row, "positive", 2, True),
        dna_named_factor(row, "positive", 3, True),
    ]

    for f in possible_positive:
        if not f:
            continue
        if f["score"] > 0:
            positives.append(f)
        elif f["score"] < 0:
            risks.append({
                "label": f["label"],
                "value": f["value"],
                "score": abs(f["score"]),
                "raw": f["raw"],
            })

    possible_risks = [
        dna_named_factor(row, "negative", 1, False),
        dna_named_factor(row, "negative", 2, False),
        dna_named_factor(row, "negative", 3, False),
    ]

    for f in possible_risks:
        if not f:
            continue
        risks.append({
            "label": f["label"],
            "value": f["value"],
            "score": abs(f["score"]),
            "raw": f["raw"],
        })

    positives.sort(key=lambda x: x["score"], reverse=True)
    risks.sort(key=lambda x: x["score"], reverse=True)

    return positives[:3], risks[:3]


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


def why_text(row, positives, risks):
    rank = model_rank(row)
    rank_txt = f"Rank #{rank}" if rank != "" else "Rank unavailable"

    pos_txt = ", ".join([f"{p['label']} {p['value']}" for p in positives]) if positives else "limited positive evidence"
    risk_txt = ", ".join([f"{r['label']} {r['value']}" for r in risks]) if risks else "no major surfaced risk"

    return f"{rank_txt}: strongest supports are {pos_txt}. Main risks are {risk_txt}."


def profile_summary(row):
    band = first_clean(row, ["dna_v6_2_band", "dna_band", "projection_band_V6_1_RESEARCH", "projection_band_v5_2"])
    style = first_clean(row, ["settling_band", "run_style", "archetype"])
    action = first_clean(row, ["execution_action_final", "execution_action", "display_decision"])
    edge = edge_pct(row)

    bits = []
    if band:
        bits.append(f"Profile {band}")
    if style:
        bits.append(f"Map {style}")
    if edge != "":
        bits.append(f"Edge {edge}%")
    if action:
        bits.append(f"Action {action}")
    return " | ".join(bits)


def blank_factor(prefix):
    return {
        f"{prefix}_1": "",
        f"{prefix}_1_value": "",
        f"{prefix}_2": "",
        f"{prefix}_2_value": "",
        f"{prefix}_3": "",
        f"{prefix}_3_value": "",
    }


def apply_factor_slots(out_row, prefix, factors):
    for i in range(1, 4):
        if len(factors) >= i:
            out_row[f"{prefix}_{i}"] = factors[i - 1]["label"]
            out_row[f"{prefix}_{i}_value"] = factors[i - 1]["value"]
        else:
            out_row[f"{prefix}_{i}"] = ""
            out_row[f"{prefix}_{i}_value"] = ""


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    board_rows = csv_rows(INPUT_BOARD)
    dna_rows = csv_rows(INPUT_DNA)
    bet_rows = csv_rows(INPUT_BET_QUALITY)

    merged_rows = merge_sources(board_rows, dna_rows, bet_rows)
    active_rows = [r for r in merged_rows if not is_scratched(r)]

    out_rows = []
    with_positives = 0
    with_risks = 0

    for r in active_rows:
        positives, risks = build_factor_lists(r)

        if positives:
            with_positives += 1
        if risks:
            with_risks += 1

        out_row = {
            "race_date": norm_race_date(r),
            "track": norm_track(r),
            "race_no": norm_race_no(r),
            "horse": horse_name(r),
            "horse_key": horse_key(r),
            "model_rank": model_rank(r),
            "win_pct": win_pct(r),
            "fair_price": fair_price(r),
            "live_price": live_price(r),
            "edge_pct": edge_pct(r),
            "positive_1": "",
            "positive_1_value": "",
            "positive_2": "",
            "positive_2_value": "",
            "positive_3": "",
            "positive_3_value": "",
            "risk_1": "",
            "risk_1_value": "",
            "risk_2": "",
            "risk_2_value": "",
            "risk_3": "",
            "risk_3_value": "",
            "why_ranked_here": "",
            "runner_profile_summary": "",
            "built_at": built_at,
        }

        apply_factor_slots(out_row, "positive", positives)
        apply_factor_slots(out_row, "risk", risks)

        out_row["why_ranked_here"] = why_text(r, positives, risks)
        out_row["runner_profile_summary"] = profile_summary(r)

        out_rows.append(out_row)

    fields = [
        "race_date", "track", "race_no", "horse", "horse_key",
        "model_rank", "win_pct", "fair_price", "live_price", "edge_pct",
        "positive_1", "positive_1_value", "positive_2", "positive_2_value",
        "positive_3", "positive_3_value",
        "risk_1", "risk_1_value", "risk_2", "risk_2_value",
        "risk_3", "risk_3_value",
        "why_ranked_here", "runner_profile_summary", "built_at",
    ]

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    summary_rows = [
        {"metric": "status", "value": "RUNNER_EXPLAINABILITY_V1_BUILT"},
        {"metric": "input_board_rows", "value": len(board_rows)},
        {"metric": "input_dna_rows", "value": len(dna_rows)},
        {"metric": "input_bet_quality_rows", "value": len(bet_rows)},
        {"metric": "active_runner_rows", "value": len(active_rows)},
        {"metric": "output_rows", "value": len(out_rows)},
        {"metric": "rows_with_positive_factors", "value": with_positives},
        {"metric": "rows_with_risk_factors", "value": with_risks},
        {"metric": "built_at", "value": built_at},
    ]

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary_rows)

    print("[RUNNER_EXPLAINABILITY_V1] COMPLETE")
    print(f"rows={len(out_rows)}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
