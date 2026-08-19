from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BOARDS = [
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_runner_board_governed_v1.csv",
]

V8 = DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv"
REL = DATA / "edgeiq_live_race_reliability_v1_feed.csv"

def s(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon_track(x):
    return re.sub(r"[^A-Z0-9]", "", s(x).upper())

def canon_horse(x):
    x = re.sub(r"\([^)]*\)", "", s(x).upper())
    return re.sub(r"[^A-Z0-9]", "", x)

def race_key(x):
    return re.sub(r"[^0-9]", "", s(x))

def first(row, names):
    for n in names:
        if n in row and s(row[n]):
            return s(row[n])
    return ""

def make_key(df):
    return df.apply(lambda r: "|".join([
        canon_track(first(r, ["track","meeting","meeting_name"])),
        race_key(first(r, ["race_no","race_number","race"])),
        canon_horse(first(r, ["horse","runner","runner_name","horse_name"])),
    ]), axis=1)

v8_lookup = {}
if V8.exists():
    v8 = pd.read_csv(V8, dtype=str).fillna("")
    v8["_k"] = make_key(v8)
    for _, r in v8.drop_duplicates("_k", keep="last").iterrows():
        v8_lookup[r["_k"]] = {
            "v8_fair_price": first(r, ["v8_fair_price","v8_fair","fair_price_v8","candidate_fair_price_v8","brc_fair_price_v8"]),
            "v8_conf": first(r, ["v8_confidence","v8_conf","brc_match_level_v8","match_level_v8"]),
        }

rel_lookup = {}
if REL.exists():
    rel = pd.read_csv(REL, dtype=str).fillna("")
    rel["_k"] = make_key(rel)
    for _, r in rel.drop_duplicates("_k", keep="last").iterrows():
        rel_lookup[r["_k"]] = {
            "reliability": first(r, ["race_reliability_band_v1","reliability_band","reliability","race_reliability_score_v1","reliability_score"]),
        }

summary = []

for path in BOARDS:
    df = pd.read_csv(path, dtype=str).fillna("")
    df["_k"] = make_key(df)

    for col in ["v8_fair_price","v8_conf","reliability"]:
        if col not in df.columns:
            df[col] = ""

    v8_hits = 0
    rel_hits = 0

    for i, r in df.iterrows():
        k = r["_k"]

        if k in v8_lookup:
            if v8_lookup[k]["v8_fair_price"]:
                df.at[i, "v8_fair_price"] = v8_lookup[k]["v8_fair_price"]
            if v8_lookup[k]["v8_conf"]:
                df.at[i, "v8_conf"] = v8_lookup[k]["v8_conf"]
            v8_hits += 1

        if k in rel_lookup:
            if rel_lookup[k]["reliability"]:
                df.at[i, "reliability"] = rel_lookup[k]["reliability"]
            rel_hits += 1

    df = df.drop(columns=["_k"], errors="ignore")
    df.to_csv(path, index=False)
    summary.append((path.name, len(df), v8_hits, rel_hits))

pd.DataFrame(summary, columns=["file","rows","v8_matched","reliability_matched"]).to_csv(
    DATA / "edgeiq_merge_v8_reliability_into_runner_board_v1_summary.csv",
    index=False
)

print("[MERGE_V8_RELIABILITY_INTO_RUNNER_BOARD] COMPLETE")
for row in summary:
    print(row)
