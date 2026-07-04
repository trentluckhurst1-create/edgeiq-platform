from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

GOV_BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"
NO_HIST = DATA / "edgeiq_no_history_governance_v1.csv"
STYLE = DATA / "edgeiq_live_runner_style_v1.csv"
TJ = DATA / "edgeiq_live_trainer_jockey_factor_feed_v3.csv"
PRICE_TRUTH = DATA / "edgeiq_price_truth_v1.csv"

OUT = DATA / "edgeiq_live_governance_clean_audit_v1.csv"
SUMMARY = DATA / "edgeiq_live_governance_clean_audit_v1_summary.csv"

def safe(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def num(x):
    return pd.to_numeric(x, errors="coerce")

def canon_horse(x):
    s = safe(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^A-Z0-9]", "", s)

def key(df):
    out = df.copy()
    out["_track"] = out["track"].astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    out["_race"] = out["race_no"].astype(str).str.replace(r"[^0-9]", "", regex=True)
    out["_horse"] = out["horse"].map(canon_horse)
    return out

def pretty(x):
    s = safe(x)
    if not s:
        return ""
    mapping = {
        "ON_PACE": "On Pace",
        "BACKMARKER": "Backmarker",
        "MIDFIELD": "Midfield",
        "LEADER": "Leader",
        "HOLDS_POSITION": "Holds Position",
        "BIG_IMPROVER": "Strong Finisher",
        "IMPROVER": "Improves Late",
        "FADER": "Fades Late",
        "NO_HISTORY_NO_LIVE": "No History / No Live Market",
        "NO_HISTORY_REVIEW": "No History / Review",
        "NO_HISTORY_LONGSHOT": "No History / Longshot",
        "NO_HISTORY_MARKET_CONFLICT_SHORT": "No History / Market Conflict - Short",
        "NO_HISTORY_MARKET_CONFLICT_MID": "No History / Market Conflict - Mid",
        "UNKNOWN_REVIEW": "Unknown / Review",
        "UNKNOWN_LONGSHOT": "Unknown / Longshot",
        "NO_LIVE_UNKNOWN": "No Live / Unknown",
    }
    if s in mapping:
        return mapping[s]
    return s.replace("_", " ").title()

def guide_price_band(row):
    no_hist = safe(row.get("no_history_flag")) == "True"
    live = num(row.get("live_price"))
    band = safe(row.get("no_history_governance_band"))

    if not no_hist:
        return safe(row.get("fair_price_display"))

    if pd.isna(live) or live <= 0:
        return "UNKNOWN"

    if band == "NO_HISTORY_MARKET_CONFLICT_SHORT":
        return f"MARKET GUIDE ${live:.2f} / MODEL UNKNOWN"
    if band == "NO_HISTORY_MARKET_CONFLICT_MID":
        return f"MARKET GUIDE ${live:.2f} / MODEL UNKNOWN"
    if band == "NO_HISTORY_LONGSHOT":
        return f"LONGSHOT GUIDE ${live:.2f} / MODEL UNKNOWN"

    return f"MARKET GUIDE ${live:.2f} / MODEL UNKNOWN"

def tj_comment(row):
    no_hist = safe(row.get("no_history_flag")) == "True"
    trainer = safe(row.get("trainer_edge_band_v3"))
    jockey = safe(row.get("jockey_edge_band_v3"))
    combo = safe(row.get("combo_edge_band_v3"))

    parts = []
    if trainer:
        parts.append(f"Trainer {pretty(trainer)}")
    if jockey:
        parts.append(f"Jockey {pretty(jockey)}")
    if combo:
        parts.append(f"Combo {pretty(combo)}")

    if not parts:
        return "Trainer/jockey guide unavailable."

    if no_hist:
        return "No-history runner: use trainer/jockey only as a guide, not a model price. " + "; ".join(parts) + "."

    return "Trainer/jockey context: " + "; ".join(parts) + "."

def governance_comment(row):
    no_hist = safe(row.get("no_history_flag")) == "True"
    if no_hist:
        return safe(row.get("no_history_governance_comment")) or "No-history runner. Model fair price hidden."
    return "Runner has projection/history. Governed model price retained."

def recommended_display_action(row):
    no_hist = safe(row.get("no_history_flag")) == "True"
    band = safe(row.get("no_history_governance_band"))
    live = num(row.get("live_price"))

    if not no_hist:
        return safe(row.get("execution_action_governed"))

    if band == "NO_HISTORY_MARKET_CONFLICT_SHORT":
        return "REVIEW_MARKET_RESPECT"
    if band == "NO_HISTORY_MARKET_CONFLICT_MID":
        return "REVIEW_MARKET_GUIDE"
    if band == "NO_HISTORY_LONGSHOT":
        return "UNKNOWN_LONGSHOT"
    if pd.isna(live) or live <= 0:
        return "NO_LIVE_UNKNOWN"

    return "UNKNOWN_REVIEW"

def main():
    if not GOV_BOARD.exists():
        raise FileNotFoundError(f"Missing {GOV_BOARD}")

    board = key(pd.read_csv(GOV_BOARD, dtype=str, low_memory=False))
    board.columns = [c.strip() for c in board.columns]

    out = board.copy()

    if STYLE.exists():
        style = key(pd.read_csv(STYLE, dtype=str, low_memory=False))
        style.columns = [c.strip() for c in style.columns]
        keep = [
            "_track","_race","_horse",
            "dominant_run_style","movement_profile","style_confidence",
            "leader_pct","onpace_pct","midfield_pct","backmarker_pct"
        ]
        keep = [c for c in keep if c in style.columns]
        out = out.merge(
            style[keep].drop_duplicates(["_track","_race","_horse"]),
            on=["_track","_race","_horse"],
            how="left",
            suffixes=("", "_style")
        )

    if TJ.exists():
        tj = key(pd.read_csv(TJ, dtype=str, low_memory=False))
        tj.columns = [c.strip() for c in tj.columns]
        keep = [
            "_track","_race","_horse",
            "trainer_edge_band_v3","jockey_edge_band_v3","combo_edge_band_v3",
            "trainer_match_status_v3","jockey_match_status_v3","combo_match_status_v3"
        ]
        keep = [c for c in keep if c in tj.columns]
        out = out.merge(
            tj[keep].drop_duplicates(["_track","_race","_horse"]),
            on=["_track","_race","_horse"],
            how="left",
            suffixes=("", "_tj")
        )

    out["run_style_display"] = out.get("dominant_run_style", "").map(pretty) if "dominant_run_style" in out.columns else ""
    out["movement_profile_display"] = out.get("movement_profile", "").map(pretty) if "movement_profile" in out.columns else ""
    out["no_history_governance_display"] = out.get("no_history_governance_band", "").map(pretty)
    out["execution_action_display"] = out.get("execution_action_governed", "").map(pretty)

    out["guide_price_display"] = out.apply(guide_price_band, axis=1)
    out["recommended_display_action"] = out.apply(recommended_display_action, axis=1)
    out["trainer_jockey_guide_comment"] = out.apply(tj_comment, axis=1)
    out["clean_governance_comment"] = out.apply(governance_comment, axis=1)

    out["first_starter_or_no_history_guide_rule"] = np.where(
        out["no_history_flag"].eq("True"),
        "Do not generate an official model price. Display UNKNOWN. Use market, trainer, jockey and combo only as guide/context.",
        "Use official governed model price."
    )

    out["price_display_quality"] = np.select(
        [
            out["no_history_flag"].eq("True") & out["live_price"].astype(str).str.len().eq(0),
            out["no_history_flag"].eq("True"),
            out["fair_price_display"].astype(str).eq("UNKNOWN"),
        ],
        [
            "UNKNOWN_NO_MARKET",
            "UNKNOWN_MARKET_GUIDE_ONLY",
            "UNKNOWN_REVIEW",
        ],
        default="MODEL_PRICE_AVAILABLE"
    )

    final_cols = [
        "race_date","track","race_no","horse_no","horse","barrier","jockey","trainer",
        "live_price","fair_price_raw","fair_price_display","guide_price_display",
        "edge_pct_raw","edge_pct_display",
        "execution_action_raw","execution_action_governed","execution_action_display","recommended_display_action",
        "no_history_flag","no_projection_flag","no_history_governance_band","no_history_governance_display",
        "run_style_display","movement_profile_display","style_confidence",
        "trainer_edge_band_v3","jockey_edge_band_v3","combo_edge_band_v3",
        "trainer_jockey_guide_comment",
        "price_display_quality",
        "clean_governance_comment",
        "first_starter_or_no_history_guide_rule",
    ]
    final_cols = [c for c in final_cols if c in out.columns]

    final = out[final_cols].copy()
    final.to_csv(OUT, index=False)

    summary = [
        ("status", "COMPLETE"),
        ("rows", len(final)),
        ("no_history_rows", int(final["no_history_flag"].eq("True").sum())),
        ("hidden_unknown_prices", int(final["fair_price_display"].eq("UNKNOWN").sum())),
        ("model_price_available", int(final["price_display_quality"].eq("MODEL_PRICE_AVAILABLE").sum())),
        ("market_guide_only", int(final["price_display_quality"].eq("UNKNOWN_MARKET_GUIDE_ONLY").sum())),
        ("unknown_no_market", int(final["price_display_quality"].eq("UNKNOWN_NO_MARKET").sum())),
    ]

    for k, v in final["recommended_display_action"].value_counts(dropna=False).to_dict().items():
        summary.append((f"recommended_display_action_{k}", v))

    for k, v in final["price_display_quality"].value_counts(dropna=False).to_dict().items():
        summary.append((f"price_display_quality_{k}", v))

    pd.DataFrame(summary, columns=["metric","value"]).to_csv(SUMMARY, index=False)

    print("[LIVE_GOVERNANCE_CLEAN_AUDIT_V1] COMPLETE")
    print(f"rows={len(final)}")
    print(f"no_history_rows={int(final['no_history_flag'].eq('True').sum())}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
