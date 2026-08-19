import os
import re
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

DNA_V1_SRC = os.path.join(DATA, "edgeiq_tactical_dna_v1.csv")
RESULTS_SRC = os.path.join(DATA, "edgeiq_racingcom_results_warehouse_v1.csv")
LIVE_SRC = os.path.join(DATA, "edgeiq_live_runner_board_v1.csv")

OUT = os.path.join(DATA, "edgeiq_tactical_dna_v2.csv")
AUDIT = os.path.join(DATA, "edgeiq_tactical_dna_v2_audit.csv")
LIVE_AUDIT = os.path.join(DATA, "edgeiq_tactical_dna_v2_live_coverage_audit.csv")

print("=" * 100)
print("EDGEIQ TACTICAL DNA V2.1 - SECTIONALS PRIMARY + RESULTS FALLBACK")
print("=" * 100)
print(f"DNA_V1_SRC:  {DNA_V1_SRC}")
print(f"RESULTS_SRC: {RESULTS_SRC}")
print(f"LIVE_SRC:    {LIVE_SRC}")

for p in [DNA_V1_SRC, RESULTS_SRC]:
    if not os.path.exists(p):
        raise FileNotFoundError(f"Missing required input: {p}")

def clean_key(x):
    x = str(x).upper().strip()
    x = re.sub(r"\([^)]*\)", "", x)
    x = x.replace("'", "")
    x = x.replace("’", "")
    x = re.sub(r"[^A-Z0-9]+", "", x)
    return x

def num(x):
    s = str(x).strip().replace("$", "").replace(",", "")
    if s == "":
        return np.nan
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else np.nan

def pct_to_prob(x):
    v = num(x)
    if pd.isna(v):
        return 0.0
    if v > 1:
        v = v / 100.0
    return max(0.0, min(1.0, float(v)))

def find_col(cols, options):
    lower = {c.lower(): c for c in cols}
    for opt in options:
        if opt.lower() in lower:
            return lower[opt.lower()]
    return None

def parse_inrun_position(x):
    s = str(x).upper().strip()
    if s == "":
        return np.nan

    nums = re.findall(r"\d+", s)
    if not nums:
        return np.nan

    return float(nums[0])

def classify_position(pos, field_size):
    if pd.isna(pos) or pd.isna(field_size) or field_size <= 0:
        return "UNKNOWN"

    ratio = pos / max(1.0, field_size)

    if pos <= 1.5 or ratio <= 0.16:
        return "Leader"
    if ratio <= 0.38:
        return "On Pace"
    if ratio <= 0.68:
        return "Midfield"
    return "Backmarker"

def confidence_from_runs(sectional_valid, sectional_runs, results_runs):
    sr = 0 if pd.isna(sectional_runs) else int(sectional_runs)
    rr = 0 if pd.isna(results_runs) else int(results_runs)

    if sectional_valid:
        if sr >= 8:
            return "HIGH"
        if sr >= 4:
            return "MEDIUM"
        if sr >= 2:
            return "LOW"
        return "LOW"

    if rr >= 12:
        return "HIGH"
    if rr >= 6:
        return "MEDIUM"
    if rr >= 3:
        return "LOW"
    if rr >= 1:
        return "VERY_LOW"
    return "INSUFFICIENT"

dna1 = pd.read_csv(DNA_V1_SRC, dtype=str).fillna("")
res = pd.read_csv(RESULTS_SRC, dtype=str).fillna("")

dna_key_col = find_col(dna1.columns, ["horse_key", "horseKey"])
if dna_key_col is None:
    raise ValueError("DNA V1 missing horse_key.")

dna1["horse_key"] = dna1[dna_key_col].apply(clean_key)

for c in ["leader_pct", "on_pace_pct", "midfield_pct", "backmarker_pct"]:
    dna1[c] = dna1[c].apply(pct_to_prob) if c in dna1.columns else 0.0

for c in ["avg_early_speed", "avg_late_speed", "runs_with_sectionals"]:
    dna1[c] = dna1[c].apply(num) if c in dna1.columns else np.nan

dna1["sectional_prob_sum"] = dna1[["leader_pct", "on_pace_pct", "midfield_pct", "backmarker_pct"]].sum(axis=1)
dna1["has_sectional_dna"] = dna1["sectional_prob_sum"] > 0

# Normalise V1 sectional probabilities if needed.
for idx in dna1.index:
    total = dna1.at[idx, "sectional_prob_sum"]
    if total > 0:
        for c in ["leader_pct", "on_pace_pct", "midfield_pct", "backmarker_pct"]:
            dna1.at[idx, c] = dna1.at[idx, c] / total

horse_col = find_col(res.columns, ["horseKey", "horse_key", "horseName", "horse"])
inrun_col = find_col(res.columns, ["inRun", "in_run", "inrunning", "settling"])
race_key_col = find_col(res.columns, ["race_key"])
date_col = find_col(res.columns, ["meeting_date", "race_date", "date"])
track_col = find_col(res.columns, ["track", "venue"])
race_no_col = find_col(res.columns, ["race_no", "raceNo", "race_number"])
finish_col = find_col(res.columns, ["finishPosition", "finish", "placing", "position"])

missing = []
if horse_col is None: missing.append("horseKey / horseName")
if inrun_col is None: missing.append("inRun")
if missing:
    raise ValueError(f"Results warehouse missing required columns: {missing}")

res["horse_key"] = res[horse_col].apply(clean_key)
res["inrun_pos"] = res[inrun_col].apply(parse_inrun_position)
res["finish_num"] = res[finish_col].apply(num) if finish_col else np.nan

if race_key_col:
    res["race_key_calc"] = res[race_key_col].astype(str).str.upper().str.strip()
else:
    if date_col is None or track_col is None or race_no_col is None:
        raise ValueError("Results warehouse needs race_key or meeting_date/track/race_no.")
    res["meeting_date_calc"] = pd.to_datetime(res[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
    res["track_calc"] = res[track_col].astype(str).str.upper().str.strip()
    res["race_no_calc"] = res[race_no_col].apply(num)
    res["race_key_calc"] = (
        res["meeting_date_calc"] + "|" +
        res["track_calc"] + "|R" +
        res["race_no_calc"].fillna(-1).astype(int).astype(str)
    )

field_sizes = (
    res[res["finish_num"].notna()]
    .groupby("race_key_calc", as_index=False)
    .agg(field_size=("horse_key", "count"))
)

all_field_sizes = res.groupby("race_key_calc", as_index=False).agg(all_field_size=("horse_key", "count"))
field_sizes = all_field_sizes.merge(field_sizes, on="race_key_calc", how="left")
field_sizes["field_size"] = field_sizes["field_size"].fillna(field_sizes["all_field_size"])
field_sizes = field_sizes[["race_key_calc", "field_size"]]

res = res.merge(field_sizes, on="race_key_calc", how="left")

res = res[
    (res["horse_key"] != "") &
    (res["inrun_pos"].notna()) &
    (res["field_size"].notna()) &
    (res["field_size"] > 0)
].copy()

res["result_bucket"] = res.apply(lambda r: classify_position(r["inrun_pos"], r["field_size"]), axis=1)

res["is_leader"] = (res["result_bucket"] == "Leader").astype(int)
res["is_on_pace"] = (res["result_bucket"] == "On Pace").astype(int)
res["is_midfield"] = (res["result_bucket"] == "Midfield").astype(int)
res["is_backmarker"] = (res["result_bucket"] == "Backmarker").astype(int)

results_dna = res.groupby("horse_key", as_index=False).agg(
    runs_from_results=("race_key_calc", "count"),
    leader_pct_results=("is_leader", "mean"),
    on_pace_pct_results=("is_on_pace", "mean"),
    midfield_pct_results=("is_midfield", "mean"),
    backmarker_pct_results=("is_backmarker", "mean"),
    avg_inrun_position=("inrun_pos", "mean"),
    avg_field_size_results=("field_size", "mean"),
)

all_keys = pd.DataFrame({
    "horse_key": sorted(set(dna1["horse_key"].dropna().astype(str)) | set(results_dna["horse_key"].dropna().astype(str)))
})

v1_keep = [
    "horse_key",
    "leader_pct",
    "on_pace_pct",
    "midfield_pct",
    "backmarker_pct",
    "has_sectional_dna",
    "sectional_prob_sum",
    "runs_with_sectionals",
]

for c in ["avg_early_speed", "avg_late_speed", "tactical_speed_bucket", "dna_confidence", "sectional_archetype"]:
    if c in dna1.columns:
        v1_keep.append(c)

v1 = dna1[v1_keep].drop_duplicates("horse_key")
out = all_keys.merge(v1, on="horse_key", how="left")
out = out.merge(results_dna, on="horse_key", how="left")

for c in ["leader_pct", "on_pace_pct", "midfield_pct", "backmarker_pct"]:
    out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

for c in ["leader_pct_results", "on_pace_pct_results", "midfield_pct_results", "backmarker_pct_results"]:
    out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

out["has_sectional_dna"] = out["has_sectional_dna"].fillna(False).astype(bool)
out["runs_with_sectionals"] = pd.to_numeric(out["runs_with_sectionals"], errors="coerce").fillna(0).astype(int)
out["runs_from_results"] = pd.to_numeric(out["runs_from_results"], errors="coerce").fillna(0).astype(int)

def blend_row(row):
    sr = int(row["runs_with_sectionals"])
    rr = int(row["runs_from_results"])

    has_sec = bool(row["has_sectional_dna"])
    has_res = rr > 0 and (
        row["leader_pct_results"] + row["on_pace_pct_results"] + row["midfield_pct_results"] + row["backmarker_pct_results"]
    ) > 0

    if has_sec and has_res:
        # If V1 has sectional DNA, keep it dominant.
        if sr >= 4:
            sec_w = 0.80
        elif sr >= 2:
            sec_w = 0.72
        else:
            sec_w = 0.65
        res_w = 1.0 - sec_w
        source = "HYBRID"
    elif has_sec:
        sec_w = 1.0
        res_w = 0.0
        source = "SECTIONALS"
    elif has_res:
        sec_w = 0.0
        res_w = 1.0
        source = "RESULTS"
    else:
        sec_w = 0.0
        res_w = 0.0
        source = "UNKNOWN"

    leader = (row["leader_pct"] * sec_w) + (row["leader_pct_results"] * res_w)
    onpace = (row["on_pace_pct"] * sec_w) + (row["on_pace_pct_results"] * res_w)
    midfield = (row["midfield_pct"] * sec_w) + (row["midfield_pct_results"] * res_w)
    backmarker = (row["backmarker_pct"] * sec_w) + (row["backmarker_pct_results"] * res_w)

    total = leader + onpace + midfield + backmarker
    if total > 0:
        leader /= total
        onpace /= total
        midfield /= total
        backmarker /= total

    return pd.Series({
        "leader_pct_v2": round(float(leader), 4),
        "on_pace_pct_v2": round(float(onpace), 4),
        "midfield_pct_v2": round(float(midfield), 4),
        "backmarker_pct_v2": round(float(backmarker), 4),
        "dna_source": source,
        "sectional_weight": round(float(sec_w), 3),
        "results_weight": round(float(res_w), 3),
    })

blend = out.apply(blend_row, axis=1)
out = pd.concat([out, blend], axis=1)

def bucket(row):
    vals = {
        "Leader": row["leader_pct_v2"],
        "On Pace": row["on_pace_pct_v2"],
        "Midfield": row["midfield_pct_v2"],
        "Backmarker": row["backmarker_pct_v2"],
    }
    if sum(vals.values()) <= 0:
        return "Unknown"
    return max(vals, key=vals.get)

out["tactical_speed_bucket_v2"] = out.apply(bucket, axis=1)
out["dna_confidence_v2"] = out.apply(
    lambda r: confidence_from_runs(r["has_sectional_dna"], r["runs_with_sectionals"], r["runs_from_results"]),
    axis=1
)

preferred = [
    "horse_key",
    "leader_pct_v2",
    "on_pace_pct_v2",
    "midfield_pct_v2",
    "backmarker_pct_v2",
    "tactical_speed_bucket_v2",
    "dna_confidence_v2",
    "dna_source",
    "has_sectional_dna",
    "runs_with_sectionals",
    "runs_from_results",
    "sectional_weight",
    "results_weight",
    "leader_pct",
    "on_pace_pct",
    "midfield_pct",
    "backmarker_pct",
    "leader_pct_results",
    "on_pace_pct_results",
    "midfield_pct_results",
    "backmarker_pct_results",
    "avg_inrun_position",
    "avg_field_size_results",
    "avg_early_speed",
    "avg_late_speed",
]

extra = [c for c in out.columns if c not in preferred]
out = out[[c for c in preferred if c in out.columns] + extra]

out.to_csv(OUT, index=False)

live_rows = 0
live_matched_v1 = 0
live_matched_v2 = 0
live_audit = pd.DataFrame()

if os.path.exists(LIVE_SRC):
    live = pd.read_csv(LIVE_SRC, dtype=str).fillna("")
    live_horse_col = find_col(live.columns, ["horse", "horseName", "runner", "runner_name", "name"])
    live_key_col = find_col(live.columns, ["horse_key", "horseKey", "runner_key"])

    if live_horse_col or live_key_col:
        live["horse_display"] = live[live_horse_col] if live_horse_col else live[live_key_col]
        live["horse_key_join"] = live[live_key_col].apply(clean_key) if live_key_col else live["horse_display"].apply(clean_key)
        live["horse_key_from_name"] = live["horse_display"].apply(clean_key)

        v1_keys = set(dna1[dna1["has_sectional_dna"]]["horse_key"])
        v2_keys = set(out[out["dna_source"] != "UNKNOWN"]["horse_key"])

        live["matched_v1"] = live["horse_key_join"].isin(v1_keys) | live["horse_key_from_name"].isin(v1_keys)
        live["matched_v2"] = live["horse_key_join"].isin(v2_keys) | live["horse_key_from_name"].isin(v2_keys)

        live_audit = live[["horse_display", "horse_key_join", "horse_key_from_name", "matched_v1", "matched_v2"]].copy()
        live_audit.to_csv(LIVE_AUDIT, index=False)

        live_rows = len(live)
        live_matched_v1 = int(live["matched_v1"].sum())
        live_matched_v2 = int(live["matched_v2"].sum())

audit = pd.DataFrame([{
    "dna_v1_rows": len(dna1),
    "dna_v1_sectional_valid": int(dna1["has_sectional_dna"].sum()),
    "results_rows_used": len(res),
    "results_dna_horses": len(results_dna),
    "dna_v2_rows": len(out),
    "sectionals_source": int((out["dna_source"] == "SECTIONALS").sum()),
    "results_source": int((out["dna_source"] == "RESULTS").sum()),
    "hybrid_source": int((out["dna_source"] == "HYBRID").sum()),
    "unknown_source": int((out["dna_source"] == "UNKNOWN").sum()),
    "live_rows": live_rows,
    "live_matched_v1": live_matched_v1,
    "live_matched_v2": live_matched_v2,
    "live_match_rate_v1_pct": round(live_matched_v1 / max(1, live_rows) * 100, 2),
    "live_match_rate_v2_pct": round(live_matched_v2 / max(1, live_rows) * 100, 2),
}])

audit.to_csv(AUDIT, index=False)

print("")
print("DONE")
print(f"WROTE: {OUT}")
print(f"WROTE: {AUDIT}")
if os.path.exists(LIVE_SRC):
    print(f"WROTE: {LIVE_AUDIT}")

print("")
print(audit.to_string(index=False))
print("")
print("DNA SOURCE DISTRIBUTION")
print(out["dna_source"].value_counts(dropna=False).to_string())
print("")
print("TACTICAL BUCKET V2 DISTRIBUTION")
print(out["tactical_speed_bucket_v2"].value_counts(dropna=False).to_string())
print("")
print("LIVE COVERAGE SAMPLE - NEWLY MATCHED BY V2")
if len(live_audit):
    improved = live_audit[(live_audit["matched_v1"] == False) & (live_audit["matched_v2"] == True)]
    print(improved.head(100).to_string(index=False))
