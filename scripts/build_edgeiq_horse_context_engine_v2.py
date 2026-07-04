import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_context_warehouse_v1.csv"

OUT = DATA / "edgeiq_horse_context_engine_v2.csv"
SUMMARY = DATA / "edgeiq_horse_context_engine_v2_summary.csv"

def clean(v):
    return (v or "").strip()

rows = []

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

horse_rows = [
    r for r in rows
    if clean(r.get("entity_type")) == "HORSE"
]

groups = defaultdict(list)

for r in horse_rows:

    horse = clean(r.get("entity_name"))

    if not horse:
        continue

    groups[horse].append(r)

out_rows = []

for horse, rr in groups.items():

    track_profiles = []
    distance_profiles = []
    condition_profiles = []
    class_profiles = []
    market_profiles = []
    caution_profiles = []

    for r in rr:

        context_type = clean(r.get("context_type"))
        context_value = clean(r.get("context_value"))
        signal = clean(r.get("signal"))

        profile = f"{context_type}: {context_value}"

        if signal == "POSITIVE_PROFILE":

            if context_type == "TRACK":
                track_profiles.append(profile)

            elif context_type == "DISTANCE":
                distance_profiles.append(profile)

            elif context_type == "CONDITION":
                condition_profiles.append(profile)

            elif context_type == "CLASS":
                class_profiles.append(profile)

            elif context_type == "SP":
                market_profiles.append(profile)

        elif signal == "CAUTION_PROFILE":

            caution_profiles.append(profile)

    out_rows.append({

        "horse": horse,

        "track_profile_count": len(track_profiles),
        "distance_profile_count": len(distance_profiles),
        "condition_profile_count": len(condition_profiles),
        "class_profile_count": len(class_profiles),
        "market_profile_count": len(market_profiles),
        "caution_profile_count": len(caution_profiles),

        "track_profile_1": track_profiles[0] if len(track_profiles) > 0 else "",
        "track_profile_2": track_profiles[1] if len(track_profiles) > 1 else "",

        "distance_profile_1": distance_profiles[0] if len(distance_profiles) > 0 else "",
        "distance_profile_2": distance_profiles[1] if len(distance_profiles) > 1 else "",

        "condition_profile_1": condition_profiles[0] if len(condition_profiles) > 0 else "",
        "condition_profile_2": condition_profiles[1] if len(condition_profiles) > 1 else "",

        "class_profile_1": class_profiles[0] if len(class_profiles) > 0 else "",

        "market_profile_1": market_profiles[0] if len(market_profiles) > 0 else "",

        "caution_profile_1": caution_profiles[0] if len(caution_profiles) > 0 else "",
        "caution_profile_2": caution_profiles[1] if len(caution_profiles) > 1 else "",

        "horse_context_view":
            (
                "Multiple positive historical horse profiles detected."
                if (
                    len(track_profiles) +
                    len(distance_profiles) +
                    len(condition_profiles) +
                    len(class_profiles) +
                    len(market_profiles)
                ) >= 3
                else
                "Limited horse-specific context detected."
            ),

        "built_at": datetime.now().isoformat(),
    })

out_rows.sort(
    key=lambda r: (
        -(
            r["track_profile_count"] +
            r["distance_profile_count"] +
            r["condition_profile_count"] +
            r["class_profile_count"] +
            r["market_profile_count"]
        ),
        r["horse"]
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(out_rows[0].keys())
    )

    writer.writeheader()
    writer.writerows(out_rows)

summary = [

    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"horse_context_rows","value":len(out_rows)},

    {
        "metric":"horses_with_track_profiles",
        "value":sum(
            1 for r in out_rows
            if int(r["track_profile_count"]) > 0
        )
    },

    {
        "metric":"horses_with_distance_profiles",
        "value":sum(
            1 for r in out_rows
            if int(r["distance_profile_count"]) > 0
        )
    },

    {
        "metric":"horses_with_condition_profiles",
        "value":sum(
            1 for r in out_rows
            if int(r["condition_profile_count"]) > 0
        )
    },

    {
        "metric":"horses_with_cautions",
        "value":sum(
            1 for r in out_rows
            if int(r["caution_profile_count"]) > 0
        )
    },

    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=["metric","value"]
    )

    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_HORSE_CONTEXT_ENGINE_V2] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
