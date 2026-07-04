from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INFILE = DATA / "edgeiq_live_track_intelligence_v1.csv"

OUT = DATA / "edgeiq_track_intelligence_card_v1.csv"
SUMMARY = DATA / "edgeiq_track_intelligence_card_v1_summary.csv"

def safe_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def num(x):
    return pd.to_numeric(x, errors="coerce")

def horse_name(row):
    return safe_str(row.get("horse", row.get("runner", "")))

def join_names(names, limit=5):
    clean = []
    seen = set()
    for n in names:
        n = safe_str(n)
        if not n or n in seen:
            continue
        clean.append(n)
        seen.add(n)
    if not clean:
        return ""
    if len(clean) <= limit:
        return ", ".join(clean)
    return ", ".join(clean[:limit]) + f" +{len(clean)-limit} more"

def top_runner_text(df, band_filter=None, limit=5):
    d = df.copy()
    if band_filter is not None:
        d = d[d["track_fit_band"].isin(band_filter)].copy()
    if d.empty:
        return ""
    d["track_fit_score_num"] = num(d["track_fit_score"]).fillna(0)
    d = d.sort_values(["track_fit_score_num", "horse"], ascending=[False, True])
    vals = []
    seen = set()
    for _, r in d.iterrows():
        h = horse_name(r)
        if not h or h in seen:
            continue
        seen.add(h)
        vals.append(f"{h} ({r['track_fit_score_num']:.0f})")
    return join_names(vals, limit=limit)

def low_runner_text(df, limit=5):
    d = df.copy()
    d = d[d["track_fit_band"].isin(["POOR", "NEGATIVE"])].copy()
    if d.empty:
        return ""
    d["track_fit_score_num"] = num(d["track_fit_score"]).fillna(0)
    d = d.sort_values(["track_fit_score_num", "horse"], ascending=[True, True])
    vals = []
    seen = set()
    for _, r in d.iterrows():
        h = horse_name(r)
        if not h or h in seen:
            continue
        seen.add(h)
        vals.append(f"{h} ({r['track_fit_score_num']:.0f})")
    return join_names(vals, limit=limit)

def mode_value(s):
    vals = [safe_str(x) for x in s if safe_str(x)]
    if not vals:
        return ""
    return pd.Series(vals).mode().iloc[0]

def make_comment(row):
    style = row["track_dna_style"]
    lane = row["track_dna_barrier"]
    level = row["track_dna_level_used"]
    sample = row["track_dna_sample_winners"]
    elite = int(row["elite_fit_count"])
    strong = int(row["strong_fit_count"])
    positive = int(row["positive_fit_count"])
    poor = int(row["poor_fit_count"])
    negative = int(row["negative_fit_count"])

    good_total = elite + strong + positive
    bad_total = poor + negative

    if good_total > bad_total:
        shape = "The race contains more runners who fit the historical track profile than runners who clash with it."
    elif bad_total > good_total:
        shape = "The race contains more runners who clash with the historical track profile than runners who clearly fit it."
    else:
        shape = "The race has a balanced track-fit shape with no clear population advantage."

    return (
        f"Historical Track DNA at this setup favours {style or 'UNKNOWN'} runners from "
        f"{lane or 'UNKNOWN'} lanes. DNA level used: {level or 'UNKNOWN'}"
        f"{f' from {sample} winners' if safe_str(sample) else ''}. "
        f"{shape}"
    )

def advantage_summary(row):
    style = row["track_dna_style"] or "UNKNOWN"
    lane = row["track_dna_barrier"] or "UNKNOWN"
    best = row["best_track_fit_runner"] or "No standout"
    return f"{style} run style + {lane} barrier lane. Best profile match: {best}."

def risk_summary(row):
    poor = int(row["poor_fit_count"])
    neg = int(row["negative_fit_count"])
    risk_names = row["risk_fit_runners"]

    if poor + neg == 0:
        return "No clear poor/negative track-fit runners identified."
    return f"{poor + neg} runners rate negative or poor for this historical track setup: {risk_names}."

def main():
    if not INFILE.exists():
        raise FileNotFoundError(f"Missing input: {INFILE}")

    df = pd.read_csv(INFILE, dtype=str, low_memory=False)
    df.columns = [c.strip() for c in df.columns]

    required = ["race_date", "track", "race_no", "horse", "track_fit_score", "track_fit_band"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing required columns from {INFILE.name}: {missing}")

    df["track_fit_score_num"] = num(df["track_fit_score"]).fillna(0)

    group_cols = ["race_date", "track", "race_no"]
    rows = []

    for keys, g in df.groupby(group_cols, dropna=False):
        race_date, track, race_no = keys
        g = g.copy()

        g_unique = g.drop_duplicates(subset=["horse"], keep="first").copy()

        best = g_unique.sort_values(["track_fit_score_num", "horse"], ascending=[False, True]).iloc[0]

        row = {
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "runners": len(g_unique),

            "track_dna_level_used": mode_value(g_unique.get("track_dna_level_used", pd.Series(dtype=str))),
            "track_dna_style": mode_value(g_unique.get("track_dna_dominant_run_style", pd.Series(dtype=str))),
            "track_dna_barrier": mode_value(g_unique.get("track_dna_dominant_barrier_lane", pd.Series(dtype=str))),
            "track_dna_movement": mode_value(g_unique.get("track_dna_dominant_movement_profile", pd.Series(dtype=str))),
            "track_dna_confidence": mode_value(g_unique.get("track_dna_profile_confidence", pd.Series(dtype=str))),
            "track_dna_sample_winners": mode_value(g_unique.get("track_dna_sample_winners", pd.Series(dtype=str))),

            "best_track_fit_runner": horse_name(best),
            "best_track_fit_score": round(float(best["track_fit_score_num"]), 1),
            "best_track_fit_band": safe_str(best.get("track_fit_band", "")),

            "elite_fit_count": int((g_unique["track_fit_band"] == "ELITE").sum()),
            "strong_fit_count": int((g_unique["track_fit_band"] == "STRONG").sum()),
            "positive_fit_count": int((g_unique["track_fit_band"] == "POSITIVE").sum()),
            "neutral_fit_count": int((g_unique["track_fit_band"] == "NEUTRAL").sum()),
            "negative_fit_count": int((g_unique["track_fit_band"] == "NEGATIVE").sum()),
            "poor_fit_count": int((g_unique["track_fit_band"] == "POOR").sum()),

            "elite_fit_runners": top_runner_text(g_unique, ["ELITE"], limit=5),
            "strong_fit_runners": top_runner_text(g_unique, ["ELITE", "STRONG"], limit=6),
            "positive_fit_runners": top_runner_text(g_unique, ["ELITE", "STRONG", "POSITIVE"], limit=8),
            "risk_fit_runners": low_runner_text(g_unique, limit=8),
        }

        row["track_advantage_summary"] = advantage_summary(row)
        row["track_risk_summary"] = risk_summary(row)
        row["track_intelligence_comment"] = make_comment(row)

        rows.append(row)

    out = pd.DataFrame(rows)

    out["race_no_num"] = pd.to_numeric(out["race_no"], errors="coerce")
    out = out.sort_values(["race_date", "track", "race_no_num"], ascending=[True, True, True]).drop(columns=["race_no_num"])

    out.to_csv(OUT, index=False)

    summary_rows = [
        ("status", "COMPLETE"),
        ("input_rows", len(df)),
        ("race_cards", len(out)),
        ("tracks", out["track"].nunique()),
        ("races_with_elite_fit", int((out["elite_fit_count"] > 0).sum())),
        ("races_with_strong_or_elite_fit", int(((out["elite_fit_count"] + out["strong_fit_count"]) > 0).sum())),
        ("races_with_poor_fit", int((out["poor_fit_count"] > 0).sum())),
    ]

    for k, v in out["track_dna_level_used"].value_counts(dropna=False).to_dict().items():
        summary_rows.append((f"track_dna_level_used_{k}", v))

    for k, v in out["track_dna_style"].value_counts(dropna=False).to_dict().items():
        summary_rows.append((f"track_dna_style_{k}", v))

    pd.DataFrame(summary_rows, columns=["metric", "value"]).to_csv(SUMMARY, index=False)

    print("[TRACK_INTELLIGENCE_CARD_V1] COMPLETE")
    print(f"input_rows={len(df)}")
    print(f"race_cards={len(out)}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
