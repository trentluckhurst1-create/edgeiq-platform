import csv
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
SRC = DATA / "edgeiq_live_runner_board_governed_v1.csv"
MEETINGS = DATA / "edgeiq_product_shell_meetings_v1.csv"
RACES = DATA / "edgeiq_product_shell_races_v1.csv"
SUMMARY = DATA / "edgeiq_product_shell_feed_v1_summary.csv"
REPORT = DATA / "edgeiq_product_shell_feed_v1_report.txt"

def clean(v):
    return str(v or "").strip()

def first(row, keys, default=""):
    for key in keys:
        value = clean(row.get(key, ""))
        if value:
            return value
    return default

def num(v):
    try:
        text = clean(v).replace("$", "").replace(",", "")
        return float(text) if text != "" else None
    except Exception:
        return None

def race_no_sort(v):
    n = num(v)
    return int(n) if n is not None else 999

def most_common(values, default=""):
    vals = [clean(v) for v in values if clean(v)]
    if not vals:
        return default
    return Counter(vals).most_common(1)[0][0]

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

race_groups = defaultdict(list)
meeting_groups = defaultdict(list)
for row in rows:
    date = first(row, ["meeting_date", "race_date", "_date"])
    track = first(row, ["track", "_track"]).upper()
    race_no = first(row, ["race_no", "_race"])
    meeting_key = first(row, ["meeting_key"], f"{date}_{track}") or f"{date}_{track}"
    race_key = first(row, ["race_key"], f"{meeting_key}_R{race_no}") or f"{meeting_key}_R{race_no}"
    race_groups[(date, track, race_no, meeting_key, race_key)].append(row)
    meeting_groups[(date, track, meeting_key)].append(row)

race_records = []
for (date, track, rno, meeting_key, race_key), group in sorted(race_groups.items(), key=lambda kv: (kv[0][0], kv[0][1], race_no_sort(kv[0][2]))):
    active_rows = [r for r in group if first(r, ["is_scratched"]).lower() not in ("true", "yes", "1") and first(r, ["runner_status"]).upper() != "SCRATCHED"]
    market_values = [first(r, ["market_state", "tab_fixed_betting_status", "market_source_status"]) for r in group]
    price_count = sum(1 for r in group if num(first(r, ["edgeiq_active_display_fair_price", "edgeiq_v7_2g2_guarded_display_fair_price", "fair_price"])) is not None)
    rating_values = [first(r, ["projected_rating_V6_1_RESEARCH", "projected_rating_v5_2", "total_rating_points"]) for r in group]
    race_records.append({
        "meeting_date": date,
        "track": track,
        "meeting_key": meeting_key,
        "race_key": race_key,
        "race_no": rno,
        "race_time": most_common([first(r, ["race_time", "jump_time", "start_time"]) for r in group], "TIME TBC"),
        "race_title": most_common([first(r, ["race_title", "race_name"]) for r in group], f"{track} R{rno}"),
        "distance": most_common([first(r, ["distance", "race_distance", "distance_m"]) for r in group], "—"),
        "race_class": most_common([first(r, ["race_class", "class", "race_type"]) for r in group], "—"),
        "track_condition": most_common([first(r, ["track_condition", "condition", "going"]) for r in group], "—"),
        "rail_position": most_common([first(r, ["rail_position", "rail", "rail_clean"]) for r in group], "—"),
        "field_size": len(group),
        "active_field_size": len(active_rows),
        "market_state": most_common(market_values, "PENDING"),
        "rating_reference": "V6.1 RESEARCH" if any(clean(v) for v in rating_values) else "RATING PENDING",
        "price_reference": "V7.2G2 DISPLAY" if price_count else "PRICE PENDING",
        "data_quality_status": "READY" if len(group) else "NO_RUNNERS",
    })

meeting_records = []
for (date, track, meeting_key), group in sorted(meeting_groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    meeting_races = [r for r in race_records if r["meeting_key"] == meeting_key]
    times = [r["race_time"] for r in meeting_races if r["race_time"] and r["race_time"] != "TIME TBC"]
    day_label = most_common([first(r, ["day_bucket"]) for r in group], "UPCOMING").replace("DAY+2", "DAY+2")
    statuses = [first(r, ["meeting_status", "dashboard_ready", "ui_status"]) for r in group]
    market_states = Counter([r["market_state"] for r in meeting_races if r["market_state"]])
    meeting_records.append({
        "meeting_date": date,
        "day_label": day_label or "UPCOMING",
        "track": track,
        "meeting_key": meeting_key,
        "meeting_status": most_common(statuses, "FIELDS_READY"),
        "race_count": len(meeting_races),
        "first_race_time": min(times) if times else "TIME TBC",
        "last_race_time": max(times) if times else "TIME TBC",
        "track_condition_latest": most_common([r["track_condition"] for r in meeting_races], "—"),
        "rail_position_latest": most_common([r["rail_position"] for r in meeting_races], "—"),
        "market_status_summary": "; ".join(f"{k}:{v}" for k, v in market_states.most_common()) or "PENDING",
        "state": most_common([first(r, ["state", "region"]) for r in group], "VIC"),
        "region": most_common([first(r, ["region", "state"]) for r in group], "VIC"),
        "data_quality_status": "READY" if len(meeting_races) else "NO_RACES",
    })

for path, records in [(MEETINGS, meeting_records), (RACES, race_records)]:
    fields = list(records[0].keys()) if records else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(records)

summary = [
    {"metric": "source", "value": SRC.name},
    {"metric": "governed_runner_rows", "value": len(rows)},
    {"metric": "meeting_count", "value": len(meeting_records)},
    {"metric": "race_count", "value": len(race_records)},
    {"metric": "duplicate_races", "value": len(race_records) - len({r["race_key"] for r in race_records})},
    {"metric": "v7_2g2_on_live_wired_rows", "value": sum(1 for r in rows if first(r, ["edgeiq_v7_2g2_feature_flag"]).upper() == "ON" and first(r, ["edgeiq_v7_2g2_live_wired_flag"]).upper().startswith("YES"))},
    {"metric": "pricing_maths_changed", "value": "NO"},
    {"metric": "v6_1_changed", "value": "NO"},
    {"metric": "v7_2g2_changed", "value": "NO"},
    {"metric": "status", "value": "PRODUCT_SHELL_FEED_BUILT" if len(rows) == 383 and len(race_records) == 25 else "PRODUCT_SHELL_FEED_REVIEW_REQUIRED"},
]
with SUMMARY.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
    writer.writeheader(); writer.writerows(summary)
REPORT.write_text("EDGEiQ PRODUCT SHELL FEED V1\n" + "\n".join(f"{s['metric']}={s['value']}" for s in summary) + "\n", encoding="utf-8")
print(REPORT)
