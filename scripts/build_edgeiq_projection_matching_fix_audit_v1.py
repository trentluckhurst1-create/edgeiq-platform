from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

JOIN_AUDIT = DATA / "edgeiq_projection_join_audit_v1.csv"
PROJECTION = DATA / "edgeiq_current_field_projection_v5_2.csv"
PROFILE = DATA / "edgeiq_runner_style_profile_v1.csv"
RUN_STYLE = DATA / "edgeiq_historical_run_style_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_all_v1.csv"

OUT = DATA / "edgeiq_projection_matching_fix_audit_v1.csv"
SUMMARY = DATA / "edgeiq_projection_matching_fix_audit_v1_summary.csv"
RECOVER = DATA / "edgeiq_projection_recoverable_history_v1.csv"

def safe(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def num(x):
    return pd.to_numeric(x, errors="coerce")

def canon(x):
    s = safe(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^A-Z0-9]", "", s)

def key(df, horse_col="horse"):
    df = df.copy()
    df["_horse_canon"] = df[horse_col].map(canon)
    return df

def find_horse_col(df):
    for c in ["horse", "runner", "horse_name", "runner_name"]:
        if c in df.columns:
            return c
    return None

def best_profile_source(horse, profile, run_style, results):
    hc = canon(horse)

    prof = profile[profile["_horse_canon"].eq(hc)] if not profile.empty else pd.DataFrame()
    rs = run_style[run_style["_horse_canon"].eq(hc)] if not run_style.empty else pd.DataFrame()
    res = results[results["_horse_canon"].eq(hc)] if not results.empty else pd.DataFrame()

    if not prof.empty:
        r = prof.iloc[0].to_dict()
        return {
            "recovery_source": "RUNNER_STYLE_PROFILE",
            "recovered_starts": int(len(rs)) if not rs.empty else int(num(r.get("starts")).fillna(0) if hasattr(num(r.get("starts")), "fillna") else 0),
            "recovered_run_style": safe(r.get("dominant_run_style")),
            "recovered_movement_profile": safe(r.get("movement_profile")),
            "recovered_style_confidence": safe(r.get("style_confidence")),
            "source_rows": len(prof),
        }

    if not rs.empty:
        style_col = "run_style_v1" if "run_style_v1" in rs.columns else "run_style"
        move_col = "movement_profile_v1" if "movement_profile_v1" in rs.columns else "movement_profile"
        return {
            "recovery_source": "HISTORICAL_RUN_STYLE",
            "recovered_starts": len(rs),
            "recovered_run_style": safe(rs[style_col].mode().iloc[0]) if style_col in rs.columns and not rs[style_col].dropna().empty else "",
            "recovered_movement_profile": safe(rs[move_col].mode().iloc[0]) if move_col in rs.columns and not rs[move_col].dropna().empty else "",
            "recovered_style_confidence": "RECOVERED_FROM_RUN_STYLE",
            "source_rows": len(rs),
        }

    if not res.empty:
        return {
            "recovery_source": "RESULTS_WAREHOUSE",
            "recovered_starts": len(res),
            "recovered_run_style": "",
            "recovered_movement_profile": "",
            "recovered_style_confidence": "RESULTS_ONLY",
            "source_rows": len(res),
        }

    return {
        "recovery_source": "NONE",
        "recovered_starts": 0,
        "recovered_run_style": "",
        "recovered_movement_profile": "",
        "recovered_style_confidence": "",
        "source_rows": 0,
    }

def main():
    join = pd.read_csv(JOIN_AUDIT, dtype=str, low_memory=False)
    join.columns = [c.strip() for c in join.columns]

    proj = pd.read_csv(PROJECTION, dtype=str, low_memory=False)
    proj.columns = [c.strip() for c in proj.columns]
    proj = key(proj)

    def load_source(path):
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_csv(path, dtype=str, low_memory=False)
        df.columns = [c.strip() for c in df.columns]
        hcol = find_horse_col(df)
        if not hcol:
            return pd.DataFrame()
        return key(df, hcol)

    profile = load_source(PROFILE)
    run_style = load_source(RUN_STYLE)
    results = load_source(RESULTS)

    fix = join[join["recommended_fix"].eq("FIX_PROJECTION_HISTORY_JOIN")].copy()

    rows = []
    for _, r in fix.iterrows():
        horse = safe(r.get("horse"))
        rec = best_profile_source(horse, profile, run_style, results)

        row = r.to_dict()
        row.update(rec)

        if rec["recovery_source"] == "RUNNER_STYLE_PROFILE":
            row["fix_confidence"] = "HIGH"
            row["fix_action"] = "RECOVER_HISTORY_FROM_PROFILE"
        elif rec["recovery_source"] == "HISTORICAL_RUN_STYLE":
            row["fix_confidence"] = "MEDIUM"
            row["fix_action"] = "RECOVER_HISTORY_FROM_RUN_STYLE"
        elif rec["recovery_source"] == "RESULTS_WAREHOUSE":
            row["fix_confidence"] = "LOW"
            row["fix_action"] = "RECOVER_RESULTS_ONLY_REVIEW"
        else:
            row["fix_confidence"] = "NONE"
            row["fix_action"] = "NO_RECOVERY_AVAILABLE"

        rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    recover_cols = [
        "race_date","track","race_no","horse","horse_key",
        "projection_join_verdict","recommended_fix",
        "recovery_source","recovered_starts","recovered_run_style",
        "recovered_movement_profile","recovered_style_confidence",
        "fix_confidence","fix_action"
    ]
    recover_cols = [c for c in recover_cols if c in out.columns]
    out[recover_cols].to_csv(RECOVER, index=False)

    summary = [
        ("status", "COMPLETE"),
        ("fix_rows", len(out)),
        ("recoverable_rows", int(out["recovery_source"].ne("NONE").sum()) if len(out) else 0),
        ("high_confidence_recoveries", int(out["fix_confidence"].eq("HIGH").sum()) if len(out) else 0),
        ("medium_confidence_recoveries", int(out["fix_confidence"].eq("MEDIUM").sum()) if len(out) else 0),
        ("low_confidence_recoveries", int(out["fix_confidence"].eq("LOW").sum()) if len(out) else 0),
    ]

    if len(out):
        for k, v in out["recovery_source"].value_counts(dropna=False).to_dict().items():
            summary.append((f"recovery_source_{k}", v))
        for k, v in out["fix_action"].value_counts(dropna=False).to_dict().items():
            summary.append((f"fix_action_{k}", v))

    pd.DataFrame(summary, columns=["metric","value"]).to_csv(SUMMARY, index=False)

    print("[PROJECTION_MATCHING_FIX_AUDIT_V1] COMPLETE")
    print(f"fix_rows={len(out)}")
    print(f"recoverable_rows={int(out['recovery_source'].ne('NONE').sum()) if len(out) else 0}")
    print(f"wrote={OUT}")
    print(f"recover={RECOVER}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
