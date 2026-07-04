from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJECTION = DATA / "edgeiq_current_field_projection_v5_2.csv"
FORENSIC = DATA / "edgeiq_no_history_forensic_audit_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_all_v1.csv"
RUN_STYLE = DATA / "edgeiq_historical_run_style_v1.csv"
PROFILE = DATA / "edgeiq_runner_style_profile_v1.csv"

OUT = DATA / "edgeiq_projection_join_audit_v1.csv"
SUMMARY = DATA / "edgeiq_projection_join_audit_v1_summary.csv"

def safe(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon(x):
    s = safe(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^A-Z0-9]", "", s)

def loose(x):
    s = canon(x)
    for suffix in ["NZ", "IRE", "GB", "USA", "FR", "JPN", "GER"]:
        if s.endswith(suffix) and len(s) > len(suffix) + 2:
            return s[:-len(suffix)]
    return s

def key_df(df, horse_col="horse"):
    df = df.copy()
    df["_horse_canon"] = df[horse_col].map(canon)
    df["_horse_loose"] = df[horse_col].map(loose)
    return df

def find_horse_col(df):
    for c in ["horse", "runner", "horse_name", "runner_name"]:
        if c in df.columns:
            return c
    return None

def verdict(row):
    if row["starts_found_v5_2_num"] > 0:
        return "PROJECTION_HAS_HISTORY"

    if row["profile_exact_rows"] > 0:
        return "JOIN_FAILURE_PROFILE_EXACT_EXISTS"

    if row["run_style_exact_runs"] > 0:
        return "JOIN_FAILURE_RUN_STYLE_EXACT_EXISTS"

    if row["results_exact_runs"] > 0:
        return "JOIN_FAILURE_RESULTS_EXACT_EXISTS"

    if row["profile_loose_rows"] > 0:
        return "JOIN_FAILURE_PROFILE_LOOSE_EXISTS"

    if row["run_style_loose_runs"] > 0:
        return "JOIN_FAILURE_RUN_STYLE_LOOSE_EXISTS"

    if row["results_loose_runs"] > 0:
        return "JOIN_FAILURE_RESULTS_LOOSE_EXISTS"

    if row["possible_word_match_count"] > 0:
        return "POSSIBLE_NAME_MATCH_REVIEW"

    return "GENUINE_FIRST_STARTER_OR_UNSEEN"

def main():
    if not PROJECTION.exists():
        raise FileNotFoundError(f"Missing {PROJECTION}")

    proj = pd.read_csv(PROJECTION, dtype=str, low_memory=False)
    proj.columns = [c.strip() for c in proj.columns]
    proj = key_df(proj, "horse")

    no_proj = proj[proj.get("projection_band_v5_2", "").astype(str).eq("NO_PROJECTION")].copy()

    forensic = pd.read_csv(FORENSIC, dtype=str, low_memory=False) if FORENSIC.exists() else pd.DataFrame()
    if not forensic.empty:
        forensic.columns = [c.strip() for c in forensic.columns]
        forensic = key_df(forensic, "horse")

    def source_counts(path):
        if not path.exists():
            return {}, {}
        df = pd.read_csv(path, dtype=str, low_memory=False)
        df.columns = [c.strip() for c in df.columns]
        hcol = find_horse_col(df)
        if not hcol:
            return {}, {}
        df = key_df(df, hcol)
        return df["_horse_canon"].value_counts().to_dict(), df["_horse_loose"].value_counts().to_dict()

    results_exact, results_loose = source_counts(RESULTS)
    run_exact, run_loose = source_counts(RUN_STYLE)
    profile_exact, profile_loose = source_counts(PROFILE)

    rows = []

    for _, r in no_proj.iterrows():
        hc = r["_horse_canon"]
        hl = r["_horse_loose"]

        frow = {}
        if not forensic.empty:
            m = forensic[forensic["_horse_canon"].eq(hc)]
            if not m.empty:
                frow = m.iloc[0].to_dict()

        starts = pd.to_numeric(r.get("starts_found_v5_2", ""), errors="coerce")
        starts = 0 if pd.isna(starts) else int(starts)

        row = {
            "race_date": safe(r.get("race_date")),
            "track": safe(r.get("track")),
            "race_no": safe(r.get("race_no")),
            "horse": safe(r.get("horse")),
            "horse_key": safe(r.get("horse_key")),
            "horse_canon_projection": hc,
            "horse_loose_projection": hl,
            "starts_found_v5_2": safe(r.get("starts_found_v5_2")),
            "starts_found_v5_2_num": starts,
            "projection_band_v5_2": safe(r.get("projection_band_v5_2")),
            "projection_confidence_v5_2": safe(r.get("projection_confidence_v5_2")),
            "projection_gap_v5_2": safe(r.get("projection_gap_v5_2")),
            "class_par_v5_2": safe(r.get("class_par_v5_2")),
            "distance_par_v5_1": safe(r.get("distance_par_v5_1")),
            "condition_par_v5_1": safe(r.get("condition_par_v5_1")),
            "results_exact_runs": int(results_exact.get(hc, 0)),
            "results_loose_runs": int(results_loose.get(hl, 0)),
            "run_style_exact_runs": int(run_exact.get(hc, 0)),
            "run_style_loose_runs": int(run_loose.get(hl, 0)),
            "profile_exact_rows": int(profile_exact.get(hc, 0)),
            "profile_loose_rows": int(profile_loose.get(hl, 0)),
            "forensic_verdict": safe(frow.get("forensic_verdict")),
            "possible_word_match_count": int(pd.to_numeric(frow.get("possible_word_match_count", 0), errors="coerce") if frow else 0),
            "market_price": safe(frow.get("market_price")),
            "no_history_governance_band": safe(frow.get("no_history_governance_band")),
        }

        row["projection_join_verdict"] = verdict(row)

        if row["projection_join_verdict"].startswith("JOIN_FAILURE"):
            row["recommended_fix"] = "FIX_PROJECTION_HISTORY_JOIN"
        elif row["projection_join_verdict"] == "POSSIBLE_NAME_MATCH_REVIEW":
            row["recommended_fix"] = "MANUAL_NAME_MATCH_REVIEW"
        else:
            row["recommended_fix"] = "FIRST_STARTER_INTELLIGENCE_MODEL"

        rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    summary = [
        ("status", "COMPLETE"),
        ("projection_rows", len(proj)),
        ("no_projection_rows", len(out)),
        ("join_failure_rows", int(out["projection_join_verdict"].astype(str).str.startswith("JOIN_FAILURE").sum())),
        ("genuine_first_starter_or_unseen_rows", int(out["projection_join_verdict"].eq("GENUINE_FIRST_STARTER_OR_UNSEEN").sum())),
        ("possible_name_review_rows", int(out["projection_join_verdict"].eq("POSSIBLE_NAME_MATCH_REVIEW").sum())),
    ]

    for k, v in out["projection_join_verdict"].value_counts(dropna=False).to_dict().items():
        summary.append((f"verdict_{k}", v))

    for k, v in out["recommended_fix"].value_counts(dropna=False).to_dict().items():
        summary.append((f"recommended_fix_{k}", v))

    pd.DataFrame(summary, columns=["metric","value"]).to_csv(SUMMARY, index=False)

    print("[PROJECTION_JOIN_AUDIT_V1] COMPLETE")
    print(f"projection_rows={len(proj)}")
    print(f"no_projection_rows={len(out)}")
    print(f"join_failure_rows={int(out['projection_join_verdict'].astype(str).str.startswith('JOIN_FAILURE').sum())}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
