from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
INPUT_DNA = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
INPUT_BET_QUALITY = DATA / "edgeiq_live_bet_quality_v1_1.csv"

OUT = DATA / "edgeiq_runner_explainability_v1_1.csv"
SUMMARY = DATA / "edgeiq_runner_explainability_v1_1_summary.csv"


def clean(v):
    return "" if v is None else str(v).strip()


def upper(v):
    return clean(v).upper()


def to_float(v, default=None):
    try:
        txt = clean(v).replace("%", "")
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


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def race_date(row):
    return clean(row.get("race_date")) or clean(row.get("_date"))


def track(row):
    return upper(row.get("track")) or upper(row.get("_track"))


def race_no(row):
    return clean(row.get("race_no")) or clean(row.get("_race"))


def horse(row):
    return clean(row.get("horse")) or clean(row.get("_horse"))


def horse_key(row):
    return upper(row.get("horse_key")) or upper(row.get("horse_canon")) or upper(horse(row))


def runner_key(row):
    return (race_date(row), track(row), race_no(row), horse_key(row))


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
    for c in ["V6_1_RESEARCH_price_rank", "fair_rank", "edge_rank", "live_rank"]:
        v = to_int(row.get(c), None)
        if v is not None:
            return v
    return ""


def fair_price(row):
    return first_float(row, ["fair_price", "display_fair_price", "ui_fair_price", "V6_1_RESEARCH_fair_price"], "")


def live_price(row):
    return first_float(row, ["live_price", "display_live_price", "tab_fixed_win", "tab_tote_win"], "")


def win_pct(row):
    v = first_float(row, ["win_pct", "V6_1_RESEARCH_probability", "v3_probability"], "")
    if v == "":
        return ""
    if v <= 1:
        v *= 100
    return round(v, 2)


def edge_pct(row):
    v = first_float(row, ["edge_pct", "display_edge_pct", "ui_edge_pct", "bet_quality_overlay_pct_v1_1"], "")
    if v == "":
        return ""
    return round(v, 2)


def add_positive(factors, label, value, score, display=None):
    if value == "" or value is None:
        return
    if score <= 0:
        return
    factors.append({
        "label": label,
        "value": display if display is not None else str(round(float(value), 2)),
        "score": float(score),
    })


def add_risk(factors, label, value, score, display=None):
    if value == "" or value is None:
        return
    if score <= 0:
        return
    factors.append({
        "label": label,
        "value": display if display is not None else str(round(float(value), 2)),
        "score": float(score),
    })


def score_above_neutral(row, col, label, neutral=50):
    v = first_float(row, [col], "")
    if v == "":
        return None
    return label, v, v - neutral


def fit_factor(row, cols, label, neutral=50):
    v = first_float(row, cols, "")
    if v == "":
        return None
    return label, v, v - neutral


def build_factors(row):
    positives = []
    risks = []

    gap = first_float(row, ["projection_gap_V6_1_RESEARCH", "projection_gap_v5_2"], "")
    if gap != "":
        if gap > 0:
            add_positive(positives, "Projection Gap", gap, gap * 5, f"+{round(gap, 2)}")
        elif gap < 0:
            add_risk(risks, "Projection Gap", gap, abs(gap) * 5, str(round(gap, 2)))

    edge = edge_pct(row)
    if edge != "":
        if edge > 0:
            add_positive(positives, "Value Edge", edge, edge, f"+{round(edge, 1)}%")
        elif edge < 0:
            add_risk(risks, "Market Underlay", edge, abs(edge), f"{round(edge, 1)}%")

    numeric_specs = [
        (["dna_v6_2_score", "dna_score"], "Runner Profile DNA", 50),
        (["distance_fit_score"], "Distance Fit", 50),
        (["condition_fit_score"], "Condition Fit", 50),
        (["class_fit_score"], "Class Fit", 50),
        (["sectional_weapon_score", "sectional_score_component_v1_1", "sectional_score"], "Sectionals", 50),
        (["late_power_index"], "Late Power", 50),
        (["projected_spd", "early_speed_rating"], "Projected Speed", 50),
        (["bet_quality_score_v1_1"], "Bet Quality", 50),
        (["confidence_score", "projection_confidence_v5_2"], "Confidence", 50),
    ]

    for cols, label, neutral in numeric_specs:
        v = first_float(row, cols, "")
        if v == "":
            continue
        delta = v - neutral
        if delta >= 5:
            add_positive(positives, label, v, delta, str(round(v, 1)))
        elif delta <= -5:
            add_risk(risks, label, v, abs(delta), str(round(v, 1)))

    # Existing DNA positive/negative text is only used as LOW-WEIGHT fallback when it does not contain a negative-looking impact.
    for i in range(1, 4):
        label = clean(row.get(f"positive_{i}_factor"))
        impact = clean(row.get(f"positive_{i}_impact"))
        impact_num = to_float(impact, None)
        if label and impact_num is not None and impact_num > 0:
            add_positive(positives, label.title(), impact_num, min(8, impact_num * 2), f"+{round(impact_num, 2)}")

    for i in range(1, 4):
        label = clean(row.get(f"negative_{i}_factor"))
        impact = clean(row.get(f"negative_{i}_impact"))
        impact_num = to_float(impact, None)
        if label and impact_num is not None:
            add_risk(risks, label.title(), impact_num, min(8, abs(impact_num) * 2 if impact_num != 0 else 1), str(round(impact_num, 2)))

    positives.sort(key=lambda x: x["score"], reverse=True)
    risks.sort(key=lambda x: x["score"], reverse=True)

    return positives[:3], risks[:3]


def merge_sources(board_rows, dna_rows, bet_rows):
    dna_index = {runner_key(r): r for r in dna_rows}
    bet_index = {runner_key(r): r for r in bet_rows}

    merged = []
    for r in board_rows:
        key = runner_key(r)
        nr = dict(r)

        for src in [dna_index.get(key, {}), bet_index.get(key, {})]:
            for k, v in src.items():
                if k not in nr or clean(nr.get(k)) == "":
                    nr[k] = v

        merged.append(nr)

    return merged


def apply_slots(out, prefix, factors):
    for i in range(1, 4):
        if len(factors) >= i:
            out[f"{prefix}_{i}"] = factors[i - 1]["label"]
            out[f"{prefix}_{i}_value"] = factors[i - 1]["value"]
        else:
            out[f"{prefix}_{i}"] = ""
            out[f"{prefix}_{i}_value"] = ""


def why_text(row, positives, risks):
    rank = model_rank(row)
    rank_txt = f"Rank #{rank}" if rank != "" else "Rank unavailable"
    pos_txt = ", ".join(f"{p['label']} {p['value']}" for p in positives) if positives else "limited positive evidence"
    risk_txt = ", ".join(f"{r['label']} {r['value']}" for r in risks) if risks else "no major surfaced risk"
    return f"{rank_txt}: strongest supports are {pos_txt}. Main risks are {risk_txt}."


def profile_summary(row):
    bits = []
    band = first_clean(row, ["dna_v6_2_band", "dna_band", "projection_band_V6_1_RESEARCH", "projection_band_v5_2"])
    style = first_clean(row, ["settling_band", "run_style", "archetype"])
    action = first_clean(row, ["execution_action_final", "execution_action", "display_decision"])
    edge = edge_pct(row)

    if band:
        bits.append(f"Profile {band}")
    if style:
        bits.append(f"Map {style}")
    if edge != "":
        bits.append(f"Edge {round(edge, 1)}%")
    if action:
        bits.append(f"Action {action}")

    return " | ".join(bits)


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    board_rows = read_csv(INPUT_BOARD)
    dna_rows = read_csv(INPUT_DNA)
    bet_rows = read_csv(INPUT_BET_QUALITY)

    merged = merge_sources(board_rows, dna_rows, bet_rows)
    active = [r for r in merged if not is_scratched(r)]

    out_rows = []
    pos_rows = 0
    risk_rows = 0

    for r in active:
        positives, risks = build_factors(r)
        if positives:
            pos_rows += 1
        if risks:
            risk_rows += 1

        out = {
            "race_date": race_date(r),
            "track": track(r),
            "race_no": race_no(r),
            "horse": horse(r),
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
            "factor_source_method": "RAW_SCORED_FIELDS_FIRST_DNA_TEXT_FALLBACK",
            "built_at": built_at,
        }

        apply_slots(out, "positive", positives)
        apply_slots(out, "risk", risks)

        out["why_ranked_here"] = why_text(r, positives, risks)
        out["runner_profile_summary"] = profile_summary(r)

        out_rows.append(out)

    fields = [
        "race_date", "track", "race_no", "horse", "horse_key",
        "model_rank", "win_pct", "fair_price", "live_price", "edge_pct",
        "positive_1", "positive_1_value", "positive_2", "positive_2_value", "positive_3", "positive_3_value",
        "risk_1", "risk_1_value", "risk_2", "risk_2_value", "risk_3", "risk_3_value",
        "why_ranked_here", "runner_profile_summary", "factor_source_method", "built_at",
    ]

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    summary_rows = [
        {"metric": "status", "value": "RUNNER_EXPLAINABILITY_V1_1_BUILT"},
        {"metric": "input_board_rows", "value": len(board_rows)},
        {"metric": "input_dna_rows", "value": len(dna_rows)},
        {"metric": "input_bet_quality_rows", "value": len(bet_rows)},
        {"metric": "active_runner_rows", "value": len(active)},
        {"metric": "output_rows", "value": len(out_rows)},
        {"metric": "rows_with_positive_factors", "value": pos_rows},
        {"metric": "rows_with_risk_factors", "value": risk_rows},
        {"metric": "built_at", "value": built_at},
    ]

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary_rows)

    print("[RUNNER_EXPLAINABILITY_V1_1] COMPLETE")
    print(f"rows={len(out_rows)}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
