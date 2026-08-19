import pandas as pd
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INFILE = DATA / "edgeiq_live_runner_style_v1.csv"
OUTFILE = DATA / "edgeiq_runner_dna_status_v1.csv"
SUMMARY = DATA / "edgeiq_runner_dna_status_v1_summary.csv"

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def is_import(horse):
    h = clean(horse).upper()
    return any(tag in h for tag in ["(NZ)", "(IRE)", "(GB)", "(FR)", "(USA)", "(JPN)", "(SAF)"])

def dna_status(r):
    starts = clean(r.get("starts", ""))
    style = clean(r.get("dominant_run_style", ""))
    conf = clean(r.get("style_confidence", ""))

    if style and starts:
        return "HISTORICAL_PROFILE"

    if is_import(r.get("horse", "")):
        return "IMPORT_NO_LOCAL_DNA"

    return "INSUFFICIENT_HISTORY"

def dna_comment(r):
    status = r.get("runner_dna_status", "")

    if status == "HISTORICAL_PROFILE":
        return (
            f"Historical Runner DNA available. {r.get('horse','')} profiles as "
            f"{r.get('dominant_run_style','UNKNOWN')} with a {r.get('movement_profile','UNKNOWN')} "
            f"movement pattern from {r.get('starts','')} historical runs. "
            f"Confidence: {r.get('style_confidence','UNKNOWN')}."
        )

    if status == "IMPORT_NO_LOCAL_DNA":
        return (
            f"No reliable local Runner DNA available for {r.get('horse','')}. "
            f"This runner appears to be an import or overseas-bred runner. "
            f"Use Track DNA and market intelligence more heavily until local history builds."
        )

    return (
        f"No reliable Runner DNA available for {r.get('horse','')}. "
        f"Historical run-style profile has not been established yet. "
        f"Use Track DNA, race shape, market behaviour, and exposed form manually."
    )

def main():
    df = pd.read_csv(INFILE, dtype=str).fillna("")

    df["runner_dna_status"] = df.apply(dna_status, axis=1)
    df["runner_dna_comment"] = df.apply(dna_comment, axis=1)

    keep = [
        "race_date","track","race_no","horse_no","horse","horse_canon","horse_key",
        "barrier","distance","jockey","trainer","live_price","fair_price","edge_pct",
        "starts","dominant_run_style","movement_profile","style_confidence",
        "leader_pct","onpace_pct","midfield_pct","backmarker_pct",
        "avg_pos800","avg_pos400","avg_gain_800_400",
        "improver_pct","fader_pct","holds_position_pct",
        "runner_style_match_status","runner_style_comment",
        "runner_dna_status","runner_dna_comment"
    ]

    keep = [c for c in keep if c in df.columns]
    out = df[keep].copy()

    out.to_csv(OUTFILE, index=False)

    summary = pd.DataFrame([
        ["status", "COMPLETE"],
        ["rows", len(out)],
        ["historical_profile_rows", int((out["runner_dna_status"] == "HISTORICAL_PROFILE").sum())],
        ["import_no_local_dna_rows", int((out["runner_dna_status"] == "IMPORT_NO_LOCAL_DNA").sum())],
        ["insufficient_history_rows", int((out["runner_dna_status"] == "INSUFFICIENT_HISTORY").sum())],
        ["output", OUTFILE.name],
    ], columns=["metric", "value"])

    summary.to_csv(SUMMARY, index=False)

    print("[RUNNER_DNA_STATUS_V1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"historical={(out['runner_dna_status'] == 'HISTORICAL_PROFILE').sum()}")
    print(f"imports={(out['runner_dna_status'] == 'IMPORT_NO_LOCAL_DNA').sum()}")
    print(f"insufficient={(out['runner_dna_status'] == 'INSUFFICIENT_HISTORY').sum()}")
    print(f"wrote={OUTFILE}")

if __name__ == "__main__":
    main()
