from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJECTION = DATA / "edgeiq_current_field_projection_v5_2.csv"
RECOVER = DATA / "edgeiq_projection_recoverable_history_v1.csv"
PROFILE = DATA / "edgeiq_runner_style_profile_v1.csv"

OUT = DATA / "edgeiq_current_field_projection_v5_2_recovered_overlay_v1.csv"
SUMMARY = DATA / "edgeiq_current_field_projection_v5_2_recovered_overlay_v1_summary.csv"

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

def key(df):
    out = df.copy()
    out["_track"] = out["track"].astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    out["_race"] = out["race_no"].astype(str).str.replace(r"[^0-9]", "", regex=True)
    out["_horse"] = out["horse"].map(canon)
    return out

def profile_score(row):
    starts = num(row.get("recovered_starts"))
    style = safe(row.get("recovered_run_style")).upper()
    conf = safe(row.get("recovered_style_confidence")).upper()
    src = safe(row.get("recovery_source")).upper()

    if pd.isna(starts):
        starts = 0

    score = 50.0

    if starts >= 20:
        score += 8
    elif starts >= 10:
        score += 5
    elif starts >= 5:
        score += 3
    elif starts >= 2:
        score += 1
    else:
        score -= 3

    if style in {"LEADER", "ON_PACE"}:
        score += 2
    elif style == "MIDFIELD":
        score += 1
    elif style == "BACKMARKER":
        score -= 1

    if conf == "HIGH":
        score += 4
    elif conf == "MEDIUM":
        score += 2
    elif conf in {"LOW", "VERY_LOW"}:
        score -= 2
    elif conf == "RESULTS_ONLY":
        score -= 8

    if src == "RESULTS_WAREHOUSE":
        score -= 8

    return round(max(35.0, min(65.0, score)), 2)

def band(score):
    if score >= 60:
        return "POSITIVE_RECOVERED"
    if score >= 53:
        return "NEUTRAL_RECOVERED"
    if score >= 45:
        return "LOW_CONFIDENCE_RECOVERED"
    return "RESULTS_ONLY_RECOVERED"

def main():
    proj = key(pd.read_csv(PROJECTION, dtype=str, low_memory=False))
    rec = key(pd.read_csv(RECOVER, dtype=str, low_memory=False))

    rec["recovered_projection_score_v1"] = rec.apply(profile_score, axis=1)
    rec["recovered_projection_band_v1"] = rec["recovered_projection_score_v1"].map(band)
    rec["recovered_projection_source_v1"] = rec["recovery_source"]
    rec["recovered_projection_comment_v1"] = rec.apply(
        lambda r: f"Recovered from {safe(r.get('recovery_source'))}: {safe(r.get('recovered_starts'))} starts, style {safe(r.get('recovered_run_style')) or 'unknown'}.",
        axis=1
    )

    keep = [
        "_track","_race","_horse",
        "recovery_source","recovered_starts","recovered_run_style",
        "recovered_movement_profile","recovered_style_confidence",
        "fix_confidence","fix_action",
        "recovered_projection_score_v1","recovered_projection_band_v1",
        "recovered_projection_source_v1","recovered_projection_comment_v1"
    ]
    keep = [c for c in keep if c in rec.columns]

    out = proj.merge(
        rec[keep].drop_duplicates(["_track","_race","_horse"]),
        on=["_track","_race","_horse"],
        how="left"
    )

    out["projection_band_v5_2_original"] = out.get("projection_band_v5_2", "")
    out["starts_found_v5_2_original"] = out.get("starts_found_v5_2", "")

    recovered = out["recovered_projection_score_v1"].notna()

    out["projection_recovered_flag_v1"] = recovered.map(lambda x: "YES" if x else "NO")
    out["starts_found_governed_v1"] = np.where(
        recovered,
        out["recovered_starts"],
        out.get("starts_found_v5_2", "")
    )

    out["projection_band_governed_v1"] = np.where(
        recovered,
        out["recovered_projection_band_v1"],
        out.get("projection_band_v5_2", "")
    )

    out["projection_status_governed_v1"] = np.where(
        recovered,
        "RECOVERED_HISTORY",
        np.where(out.get("projection_band_v5_2", "").astype(str).eq("NO_PROJECTION"), "NO_PROJECTION", "ORIGINAL_PROJECTION")
    )

    out["projection_score_governed_v1"] = np.where(
        recovered,
        out["recovered_projection_score_v1"],
        out.get("projected_rating_v5_2", "")
    )

    out = out.drop(columns=["_track","_race","_horse"], errors="ignore")
    out.to_csv(OUT, index=False)

    summary = [
        ("status", "COMPLETE"),
        ("input_projection_rows", len(proj)),
        ("recovered_rows", int(recovered.sum())),
        ("original_no_projection_rows", int(proj.get("projection_band_v5_2", "").astype(str).eq("NO_PROJECTION").sum())),
        ("governed_no_projection_rows", int(out["projection_status_governed_v1"].eq("NO_PROJECTION").sum())),
    ]

    for k, v in out["projection_status_governed_v1"].value_counts(dropna=False).to_dict().items():
        summary.append((f"status_{k}", v))

    for k, v in out["projection_band_governed_v1"].value_counts(dropna=False).to_dict().items():
        summary.append((f"band_{k}", v))

    pd.DataFrame(summary, columns=["metric","value"]).to_csv(SUMMARY, index=False)

    print("[PROJECTION_RECOVERED_OVERLAY_V1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"recovered_rows={int(recovered.sum())}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
