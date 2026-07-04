from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

DATA = Path.cwd() / "public" / "data"

src = DATA / "edgeiq_race_day_intelligence_card_v1.csv"
out = DATA / "edgeiq_race_day_intelligence_card_v1_1.csv"
summary = DATA / "edgeiq_race_day_intelligence_card_v1_1_summary.csv"

df = pd.read_csv(src, dtype=str).fillna("")

def clean_tempo(x):
    x = str(x).strip()
    if not x or x.upper() in ["NOT ASSESSED", "N/A", "--"]:
        return "Map-based read"
    return x.replace("_", " ").title()

def clean_rail(x):
    x = str(x).strip()
    return x if x else "Rail not published"

def clean_track_profile(x):
    x = str(x).strip().replace("_", " ")
    if not x:
        return "No strong pattern"
    return x.title()

def clean_conf(x):
    x = str(x).strip()
    return x.upper() if x else "LOW"

def make_read(r):
    condition = r["track_condition"] or "Track condition not listed"
    rail = r["rail_clean"]
    pressure = r["map_pressure"]
    profile = r["track_profile_clean"]
    conf = r["track_confidence_clean"]

    bits = []
    bits.append(f"Track is listed as {condition}.")
    bits.append(f"{rail}.")
    bits.append(f"Race map suggests {pressure.lower()}.")
    if profile and profile != "No Strong Pattern":
        bits.append(f"Historical track profile leans toward {profile.lower()} runners.")
    bits.append(f"Track-pattern confidence is {conf.lower()}.")

    return " ".join(bits)

df["tempo_clean"] = df["expected_tempo"].apply(clean_tempo)
df["rail_clean"] = df["rail"].apply(clean_rail)
df["track_profile_clean"] = df["track_profile"].apply(clean_track_profile)
df["track_confidence_clean"] = df["track_confidence"].apply(clean_conf)

df["race_day_read_clean"] = df.apply(make_read, axis=1)

df["customer_summary_clean"] = (
    df["track_condition"].replace("", "Track condition not listed")
    + " | "
    + df["rail_clean"]
    + " | "
    + df["tempo_clean"]
    + " | "
    + df["map_pressure"]
)

df.to_csv(out, index=False)

pd.DataFrame([{
    "status": "EDGEIQ_RACE_DAY_INTELLIGENCE_CARD_V1_1_BUILT",
    "rows": len(df),
    "rail_not_published": int((df["rail_clean"] == "Rail not published").sum()),
    "map_based_read": int((df["tempo_clean"] == "Map-based read").sum()),
    "with_clean_read": int((df["race_day_read_clean"].astype(str).str.len() > 0).sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}]).to_csv(summary, index=False)

print("[EDGEIQ_RACE_DAY_INTELLIGENCE_CARD_V1_1] COMPLETE")
print(out)
print(summary)
