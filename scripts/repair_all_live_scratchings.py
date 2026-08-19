import pandas as pd
import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"

SCRATCH_FILES = [
    DATA / "scratchings.csv",
    DATA / "scratchings_gear.csv",
    DATA / "edgeiq_vic_scratchings_diagnostics.csv",
]

def norm(x):
    if pd.isna(x):
        return ""
    x = str(x).upper()
    x = re.sub(r"\(.*?\)", "", x)
    x = re.sub(r"[^A-Z0-9]", "", x)
    return x.strip()

def clean_track(x):
    return str(x or "").upper().strip()

def clean_race_no(x):
    s = str(x or "").strip().upper()
    s = s.replace(".0", "")
    m = re.search(r"R?(\d+)", s)
    return m.group(1) if m else s

live = pd.read_csv(LIVE)
live["_horse_norm"] = live["horse"].apply(norm)
live["_track_norm"] = live["track"].apply(clean_track)
live["_race_no_norm"] = live["race_no"].apply(clean_race_no)

scratch_rows = []

for path in SCRATCH_FILES:
    if not path.exists():
        continue

    df = pd.read_csv(path)
    if df.empty:
        continue

    cols = list(df.columns)
    lower = {c.lower(): c for c in cols}

    horse_col = next((c for c in cols if "horse" in c.lower() or "runner" in c.lower()), None)
    track_col = next((c for c in cols if c.lower() in ["track", "meeting", "venue", "track_name"]), None)
    race_col = next((c for c in cols if "race_no" in c.lower() or "race_number" in c.lower() or c.lower() == "race"), None)
    status_col = next((c for c in cols if "status" in c.lower() or "scratch" in c.lower()), None)

    if not horse_col:
        continue

    temp = pd.DataFrame()
    temp["source_file"] = path.name
    temp["horse"] = df[horse_col].astype(str)
    temp["_horse_norm"] = df[horse_col].apply(norm)

    if track_col:
        temp["_track_norm"] = df[track_col].apply(clean_track)
    else:
        temp["_track_norm"] = ""

    if race_col:
        temp["_race_no_norm"] = df[race_col].apply(clean_race_no)
    else:
        temp["_race_no_norm"] = ""

    if status_col:
        temp["_status"] = df[status_col].astype(str).str.upper()
    else:
        temp["_status"] = "SCRATCHED"

    # Keep rows that explicitly look scratched OR files that are scratch-only lists.
    temp = temp[
        (temp["_status"].str.contains("SCR", na=False)) |
        (path.name.lower() in ["scratchings.csv", "scratchings_gear.csv"])
    ]

    scratch_rows.append(temp)

if scratch_rows:
    scratches = pd.concat(scratch_rows, ignore_index=True)
    scratches = scratches[scratches["_horse_norm"] != ""].drop_duplicates(
        ["_track_norm", "_race_no_norm", "_horse_norm"]
    )
else:
    scratches = pd.DataFrame(columns=["_track_norm", "_race_no_norm", "_horse_norm", "source_file"])

# Match priority:
# 1 exact track + race + horse
# 2 exact track + horse
# 3 horse-only fallback only if unique in today's live feed
live["is_scratched"] = False
live["scratch_status"] = ""
live["runner_status"] = "ACTIVE"
live["scratch_source"] = ""

exact = set(
    tuple(x)
    for x in scratches[["_track_norm", "_race_no_norm", "_horse_norm"]].dropna().values.tolist()
    if x[0] and x[1] and x[2]
)

track_horse = set(
    tuple(x)
    for x in scratches[["_track_norm", "_horse_norm"]].dropna().values.tolist()
    if x[0] and x[1]
)

horse_counts = live["_horse_norm"].value_counts().to_dict()
horse_only = set(
    scratches["_horse_norm"].dropna().astype(str)
)

def is_scratched(row):
    key_exact = (row["_track_norm"], row["_race_no_norm"], row["_horse_norm"])
    key_track = (row["_track_norm"], row["_horse_norm"])

    if key_exact in exact:
        return True

    if key_track in track_horse:
        return True

    if row["_horse_norm"] in horse_only and horse_counts.get(row["_horse_norm"], 0) == 1:
        return True

    return False

live["is_scratched"] = live.apply(is_scratched, axis=1)
live["scratch_status"] = live["is_scratched"].map(lambda x: "SCRATCHED" if x else "")
live["runner_status"] = live["is_scratched"].map(lambda x: "SCRATCHED" if x else "ACTIVE")

live = live.drop(columns=["_horse_norm", "_track_norm", "_race_no_norm"], errors="ignore")
live.to_csv(LIVE, index=False)

print("=" * 80)
print("EDGEIQ FULL SCRATCHINGS REPAIR COMPLETE")
print("=" * 80)
print("scratch source rows:", len(scratches))
print("live rows:", len(live))
print("scratched live rows:", int((live["runner_status"] == "SCRATCHED").sum()))
print("=" * 80)
print(
    live.loc[
        live["runner_status"] == "SCRATCHED",
        ["race_key", "horse_no", "horse", "runner_status"]
    ].to_string(index=False)
)
print("=" * 80)
