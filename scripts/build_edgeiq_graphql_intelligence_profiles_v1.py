from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_q1_apr_2025_MASTER_v1.csv"

TRAINER_TRACK_OUT = DATA / "edgeiq_trainer_track_profiles_graphql_v1.csv"
JOCKEY_TRACK_OUT = DATA / "edgeiq_jockey_track_profiles_graphql_v1.csv"
COMBO_OUT = DATA / "edgeiq_stable_rider_relationship_profiles_graphql_v1.csv"
SP_OUT = DATA / "edgeiq_sp_performance_profiles_graphql_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_graphql_intelligence_profiles_v1_summary.csv"


def clean(v):
    return "" if v is None else str(v).strip()


def key(v):
    return re.sub(r"[^A-Z0-9]+", "", clean(v).upper())


def to_float(v):
    txt = clean(v).replace("$", "").replace(",", "")
    try:
        return float(txt)
    except Exception:
        return None


def finish_status(r):
    raw = clean(r.get("finish") or r.get("finish_raw") or r.get("finish_position"))
    scratched = clean(r.get("scratched")).lower()
    if raw == "109" or scratched == "true":
        return "SCR"
    if raw == "100":
        return "DNF"
    if raw.isdigit() and int(raw) >= 1:
        return "FINISHED"
    return "UNKNOWN"


def finish_pos(r):
    raw = clean(r.get("finish") or r.get("finish_raw") or r.get("finish_position"))
    if raw.isdigit() and 1 <= int(raw) <= 99:
        return int(raw)
    return None


def sp_band(sp):
    if sp is None:
        return "NO_SP"
    if sp < 3:
        return "SP_LT_3"
    if sp < 6:
        return "SP_3_6"
    if sp < 10:
        return "SP_6_10"
    if sp < 20:
        return "SP_10_20"
    return "SP_20_PLUS"


def safe_pct(a, b):
    return round((a / b) * 100, 2) if b else 0.0


def safe_roi(winner_returns, starts):
    return round(((winner_returns - starts) / starts) * 100, 2) if starts else 0.0


def read_rows():
    with SRC.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def summarise_group(rows, group_fields):
    buckets = defaultdict(list)
    for r in rows:
        if finish_status(r) == "SCR":
            continue
        k_tuple = tuple(clean(r.get(f)) for f in group_fields)
        if any(not x for x in k_tuple):
            continue
        buckets[k_tuple].append(r)

    out = []
    for k_tuple, xs in buckets.items():
        starts = len(xs)
        wins = sum(1 for r in xs if finish_pos(r) == 1)
        places = sum(1 for r in xs if (finish_pos(r) or 999) <= 3)
        winner_returns = 0.0
        sp_count = 0

        for r in xs:
            sp = to_float(r.get("starting_price") or r.get("sp"))
            if sp is not None:
                sp_count += 1
            if finish_pos(r) == 1 and sp is not None:
                winner_returns += sp

        row = {group_fields[i]: k_tuple[i] for i in range(len(group_fields))}
        row.update({
            "starts": starts,
            "wins": wins,
            "places": places,
            "win_pct": safe_pct(wins, starts),
            "place_pct": safe_pct(places, starts),
            "sp_rows": sp_count,
            "sp_roi_pct": safe_roi(winner_returns, starts),
            "first_date": min(clean(r.get("race_date")) for r in xs),
            "last_date": max(clean(r.get("race_date")) for r in xs),
        })
        out.append(row)

    return sorted(out, key=lambda x: (x["wins"], x["starts"]), reverse=True)


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def build_sp_profiles(rows):
    buckets = defaultdict(list)

    for r in rows:
        if finish_status(r) == "SCR":
            continue

        trainer = clean(r.get("trainer"))
        jockey = clean(r.get("jockey"))
        combo = f"{trainer} + {jockey}" if trainer and jockey else ""
        sp = to_float(r.get("starting_price") or r.get("sp"))
        band = sp_band(sp)

        candidates = [
            ("TRAINER", trainer, band),
            ("JOCKEY", jockey, band),
            ("STABLE_RIDER", combo, band),
        ]

        for entity_type, entity, b in candidates:
            if entity:
                buckets[(entity_type, entity, b)].append(r)

    out = []
    for (entity_type, entity, band), xs in buckets.items():
        starts = len(xs)
        wins = sum(1 for r in xs if finish_pos(r) == 1)
        places = sum(1 for r in xs if (finish_pos(r) or 999) <= 3)
        winner_returns = 0.0

        for r in xs:
            sp = to_float(r.get("starting_price") or r.get("sp"))
            if finish_pos(r) == 1 and sp is not None:
                winner_returns += sp

        out.append({
            "entity_type": entity_type,
            "entity": entity,
            "sp_band": band,
            "starts": starts,
            "wins": wins,
            "places": places,
            "win_pct": safe_pct(wins, starts),
            "place_pct": safe_pct(places, starts),
            "sp_roi_pct": safe_roi(winner_returns, starts),
        })

    return sorted(out, key=lambda x: (x["entity_type"], x["sp_band"], -x["wins"], -x["starts"]))


def main():
    built_at = datetime.now(timezone.utc).isoformat()
    rows = read_rows()

    trainer_track = summarise_group(rows, ["trainer", "track"])
    jockey_track = summarise_group(rows, ["jockey", "track"])
    combo = summarise_group(rows, ["trainer", "jockey"])
    sp_profiles = build_sp_profiles(rows)

    for r in trainer_track + jockey_track + combo + sp_profiles:
        r["built_at"] = built_at

    write_csv(TRAINER_TRACK_OUT, trainer_track)
    write_csv(JOCKEY_TRACK_OUT, jockey_track)
    write_csv(COMBO_OUT, combo)
    write_csv(SP_OUT, sp_profiles)

    summary = [
        {"metric": "status", "value": "EDGEIQ_GRAPHQL_INTELLIGENCE_PROFILES_V1_BUILT"},
        {"metric": "source", "value": str(SRC)},
        {"metric": "source_rows", "value": len(rows)},
        {"metric": "trainer_track_rows", "value": len(trainer_track)},
        {"metric": "jockey_track_rows", "value": len(jockey_track)},
        {"metric": "stable_rider_combo_rows", "value": len(combo)},
        {"metric": "sp_profile_rows", "value": len(sp_profiles)},
        {"metric": "built_at", "value": built_at},
    ]

    write_csv(SUMMARY_OUT, summary)

    print("[EDGEIQ_GRAPHQL_INTELLIGENCE_PROFILES_V1] COMPLETE")
    print(f"source_rows={len(rows)}")
    print(f"trainer_track_rows={len(trainer_track)}")
    print(f"jockey_track_rows={len(jockey_track)}")
    print(f"stable_rider_combo_rows={len(combo)}")
    print(f"sp_profile_rows={len(sp_profiles)}")


if __name__ == "__main__":
    main()
