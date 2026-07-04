from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
IDENTITY_V2 = DATA / "edgeiq_sectional_identity_engine_v2.csv"
HORSE_ALIASES = DATA / "edgeiq_horse_alias_engine_v1.csv"
TRACK_ALIASES = DATA / "edgeiq_track_alias_engine_v1.csv"
PHYSICS = DATA / "edgeiq_sectional_physics_validation_v1.csv"
OUT = DATA / "edgeiq_runner_entity_graph_v1.csv"
SUMMARY = DATA / "edgeiq_runner_entity_graph_summary_v1.csv"

FIELDS = [
    "source_lineage", "source_file", "source_row_id", "sectional_runner", "sectional_runner_key",
    "sectional_race_date", "sectional_track", "sectional_race_no", "sectional_distance",
    "edgeiq_runner", "edgeiq_runner_key", "edgeiq_race_date", "edgeiq_track", "edgeiq_race_no",
    "edgeiq_distance", "race_context", "horse_name_confidence", "alias_confidence",
    "track_confidence", "distance_confidence", "race_structure_confidence",
    "field_overlap_confidence", "barrier_confidence", "jockey_confidence", "trainer_confidence",
    "saddlecloth_confidence", "position_confidence", "adjacent_runner_confidence",
    "payload_confidence", "physics_confidence", "runner_entity_confidence",
    "runner_entity_status", "runner_resolution_method", "runner_resolution_reason",
    "candidate_rank", "candidate_count",
]

SUMMARY_FIELDS = ["metric", "value"]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    try:
        with tmp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(path)
    except PermissionError:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


def canon_horse(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\b(NZ|AUS|GB|IRE|USA|FR|JPN|SAF|GER)\b", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def canon_track(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|MRC|VRC|RACING|CLUB)\b", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def race_no(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value).upper().replace("RACE", "").replace("R", ""))
    return str(int(digits)) if digits else ""


def distance(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value))
    return str(int(digits)) if digits else ""


def confidence(value: object) -> int:
    try:
        return max(0, min(100, int(round(float(clean(value))))))
    except ValueError:
        return 0


def delta_confidence(left: object, right: object) -> int:
    try:
        delta = abs(int(distance(left)) - int(distance(right)))
    except ValueError:
        return 0
    if delta == 0:
        return 100
    if delta <= 50:
        return 82
    if delta <= 100:
        return 45
    return 0


def first(row: dict[str, str] | None, names: list[str]) -> str:
    if row is None:
        return ""
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def lineage(row: dict[str, str]) -> str:
    return clean(row.get("source_lineage")) or f"{clean(row.get('source_file'))}#{clean(row.get('source_row_id'))}"


def alias_lookup(path: Path, key_name: str, value_name: str) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in read_csv(path):
        key = clean(row.get(key_name))
        value = clean(row.get(value_name)) or key
        if key and value:
            lookup[key] = value
    return lookup


def horse_alias_confidence(left: object, right: object, aliases: dict[str, str]) -> tuple[int, int]:
    left_key = aliases.get(canon_horse(left), canon_horse(left))
    right_key = aliases.get(canon_horse(right), canon_horse(right))
    if not left_key or not right_key:
        return 0, 0
    if left_key == right_key:
        return 100, 100
    ratio = SequenceMatcher(None, left_key, right_key).ratio()
    return round(ratio * 100), 88 if ratio >= 0.9 else 70 if ratio >= 0.82 else 0


def track_confidence(left: object, right: object, aliases: dict[str, str]) -> int:
    left_key = aliases.get(canon_track(left), canon_track(left))
    right_key = aliases.get(canon_track(right), canon_track(right))
    if not left_key or not right_key:
        return 0
    return 100 if left_key == right_key else round(SequenceMatcher(None, left_key, right_key).ratio() * 70)


def runner_key(row: dict[str, str]) -> str:
    return "|".join([clean(row.get("race_date"))[:10], canon_track(first(row, ["track", "meeting"])), race_no(first(row, ["race_no", "race_number", "race"])), canon_horse(first(row, ["horse_key", "horse", "runner", "horse_name", "runner_name"]))])


def load_indexes() -> tuple[list[dict[str, str]], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    all_rows: list[dict[str, str]] = []
    by_race: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_horse: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_date_track: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(UNIVERSE):
        if not first(row, ["horse", "horse_key", "runner", "runner_name"]):
            continue
        merged = dict(row)
        merged["_runner_key"] = runner_key(row)
        date = clean(row.get("race_date"))[:10]
        track = canon_track(first(row, ["track", "meeting"]))
        rn = race_no(first(row, ["race_no", "race_number", "race"]))
        horse = canon_horse(first(row, ["horse_key", "horse", "runner", "horse_name", "runner_name"]))
        all_rows.append(merged)
        by_race[f"{date}|{track}|{rn}"].append(merged)
        by_date_track[f"{date}|{track}"].append(merged)
        by_horse[horse].append(merged)
    return all_rows, by_race, by_date_track, by_horse


def physics_lookup() -> dict[str, dict[str, str]]:
    return {lineage(row): row for row in read_csv(PHYSICS)}


def race_context(row: dict[str, str]) -> str:
    return "|".join([clean(row.get("matched_race_date")) or clean(row.get("race_date")), canon_track(clean(row.get("matched_track")) or clean(row.get("track"))), race_no(clean(row.get("matched_race_no")) or clean(row.get("race_no")))])


def candidate_pool(row: dict[str, str], by_race: dict[str, list[dict[str, str]]], by_date_track: dict[str, list[dict[str, str]]], by_horse: dict[str, list[dict[str, str]]], horse_aliases: dict[str, str], track_aliases: dict[str, str]) -> list[dict[str, str]]:
    date = (clean(row.get("matched_race_date")) or clean(row.get("race_date")))[:10]
    track = canon_track(clean(row.get("matched_track")) or clean(row.get("track")))
    rn = race_no(clean(row.get("matched_race_no")) or clean(row.get("race_no")))
    horse = horse_aliases.get(canon_horse(clean(row.get("matched_horse")) or clean(row.get("horse"))), canon_horse(clean(row.get("matched_horse")) or clean(row.get("horse"))))
    candidates: dict[str, dict[str, str]] = {}
    for source in [by_race.get(f"{date}|{track}|{rn}", []), by_date_track.get(f"{date}|{track}", []), by_horse.get(horse, [])]:
        for item in source:
            candidates[item["_runner_key"]] = item
    return list(candidates.values())[:30]


def compare(row: dict[str, str], candidate: dict[str, str], physics: dict[str, str], horse_aliases: dict[str, str], track_aliases: dict[str, str]) -> dict[str, object]:
    sectional_runner = clean(row.get("horse")) or clean(row.get("matched_horse"))
    edgeiq_runner = first(candidate, ["horse", "runner", "horse_name", "runner_name"])
    horse_name_conf, alias_conf = horse_alias_confidence(sectional_runner, edgeiq_runner, horse_aliases)
    track_conf = track_confidence(clean(row.get("track")), first(candidate, ["track", "meeting"]), track_aliases)
    dist_conf = delta_confidence(clean(row.get("distance")), first(candidate, ["distance", "race_distance", "dist"]))
    field_conf = confidence(row.get("field_composition_confidence"))
    race_structure_conf = confidence(row.get("race_structure_confidence"))
    barrier_conf = 0
    jockey_conf = 0
    trainer_conf = 0
    saddlecloth_conf = 0
    payload_conf = 100 if clean(physics.get("physics_valid")).upper() == "YES" else 0
    physics_conf = confidence(physics.get("physics_confidence"))
    score = round(horse_name_conf * 0.2 + alias_conf * 0.16 + track_conf * 0.09 + dist_conf * 0.08 + race_structure_conf * 0.08 + field_conf * 0.12 + payload_conf * 0.08 + physics_conf * 0.1)
    reasons = []
    if alias_conf < 90:
        reasons.append("horse alias below trusted threshold")
    if field_conf < 60:
        reasons.append("field overlap weak")
    if payload_conf < 100:
        reasons.append("payload physics invalid")
    if confidence(row.get("identity_v2_confidence")) < 60:
        reasons.append("identity v2 weak")
    if score >= 92 and not reasons:
        status = "TRUSTED"
        method = "EXACT_GRAPH"
    elif score >= 84 and payload_conf == 100 and alias_conf >= 90 and field_conf >= 70:
        status = "LIKELY"
        method = "HYBRID_GRAPH"
    elif score >= 68 and payload_conf == 100:
        status = "PARTIAL"
        method = "PARTIAL_GRAPH"
    elif score >= 45:
        status = "UNSAFE"
        method = "FIELD_GRAPH" if field_conf >= 60 else "ALIAS_GRAPH" if alias_conf >= 80 else "PARTIAL_GRAPH"
    else:
        status = "UNMATCHED"
        method = "PARTIAL_GRAPH"
    return {
        "source_lineage": lineage(row), "source_file": clean(row.get("source_file")), "source_row_id": clean(row.get("source_row_id")),
        "sectional_runner": sectional_runner, "sectional_runner_key": canon_horse(sectional_runner),
        "sectional_race_date": clean(row.get("race_date")), "sectional_track": clean(row.get("track")), "sectional_race_no": clean(row.get("race_no")), "sectional_distance": clean(row.get("distance")),
        "edgeiq_runner": edgeiq_runner, "edgeiq_runner_key": clean(candidate.get("_runner_key")), "edgeiq_race_date": clean(candidate.get("race_date")), "edgeiq_track": first(candidate, ["track", "meeting"]),
        "edgeiq_race_no": first(candidate, ["race_no", "race_number", "race"]), "edgeiq_distance": first(candidate, ["distance", "race_distance", "dist"]), "race_context": race_context(row),
        "horse_name_confidence": horse_name_conf, "alias_confidence": alias_conf, "track_confidence": track_conf, "distance_confidence": dist_conf, "race_structure_confidence": race_structure_conf, "field_overlap_confidence": field_conf,
        "barrier_confidence": barrier_conf, "jockey_confidence": jockey_conf, "trainer_confidence": trainer_conf, "saddlecloth_confidence": saddlecloth_conf, "position_confidence": 0, "adjacent_runner_confidence": 0,
        "payload_confidence": payload_conf, "physics_confidence": physics_conf, "runner_entity_confidence": max(0, min(100, score)), "runner_entity_status": status, "runner_resolution_method": method,
        "runner_resolution_reason": "; ".join(reasons) if reasons else "multi-factor runner graph evidence agrees",
    }


def unmatched_row(row: dict[str, str], physics: dict[str, str]) -> dict[str, object]:
    return {
        "source_lineage": lineage(row), "source_file": clean(row.get("source_file")), "source_row_id": clean(row.get("source_row_id")),
        "sectional_runner": clean(row.get("horse")), "sectional_runner_key": canon_horse(row.get("horse")), "sectional_race_date": clean(row.get("race_date")),
        "sectional_track": clean(row.get("track")), "sectional_race_no": clean(row.get("race_no")), "sectional_distance": clean(row.get("distance")),
        "edgeiq_runner": "", "edgeiq_runner_key": "", "edgeiq_race_date": "", "edgeiq_track": "", "edgeiq_race_no": "", "edgeiq_distance": "", "race_context": race_context(row),
        "horse_name_confidence": 0, "alias_confidence": 0, "track_confidence": 0, "distance_confidence": 0, "race_structure_confidence": confidence(row.get("race_structure_confidence")),
        "field_overlap_confidence": confidence(row.get("field_composition_confidence")), "barrier_confidence": 0, "jockey_confidence": 0, "trainer_confidence": 0, "saddlecloth_confidence": 0,
        "position_confidence": 0, "adjacent_runner_confidence": 0, "payload_confidence": 100 if clean(physics.get("physics_valid")).upper() == "YES" else 0,
        "physics_confidence": confidence(physics.get("physics_confidence")), "runner_entity_confidence": 0, "runner_entity_status": "UNMATCHED", "runner_resolution_method": "PARTIAL_GRAPH",
        "runner_resolution_reason": "no EDGEiQ runner candidate", "candidate_rank": 0, "candidate_count": 0,
    }


def main() -> None:
    _, by_race, by_date_track, by_horse = load_indexes()
    horse_aliases = alias_lookup(HORSE_ALIASES, "alias_key", "horse_key")
    track_aliases = alias_lookup(TRACK_ALIASES, "track_key", "canonical_track")
    physics_by_lineage = physics_lookup()
    rows: list[dict[str, object]] = []
    for identity in read_csv(IDENTITY_V2):
        physics = physics_by_lineage.get(lineage(identity), {})
        candidates = candidate_pool(identity, by_race, by_date_track, by_horse, horse_aliases, track_aliases)
        if not candidates:
            rows.append(unmatched_row(identity, physics))
            continue
        scored = [compare(identity, candidate, physics, horse_aliases, track_aliases) for candidate in candidates]
        scored.sort(key=lambda item: int(item["runner_entity_confidence"]), reverse=True)
        for rank, candidate in enumerate(scored[:3], start=1):
            candidate["candidate_rank"] = rank
            candidate["candidate_count"] = len(scored)
            rows.append(candidate)
    status_counts = Counter(str(row["runner_entity_status"]) for row in rows)
    method_counts = Counter(str(row["runner_resolution_method"]) for row in rows)
    best_by_lineage: dict[str, dict[str, object]] = {}
    for row in rows:
        key = str(row["source_lineage"])
        if key not in best_by_lineage or int(row["runner_entity_confidence"]) > int(best_by_lineage[key]["runner_entity_confidence"]):
            best_by_lineage[key] = row
    best_counts = Counter(str(row["runner_entity_status"]) for row in best_by_lineage.values())
    summary = [
        {"metric": "graph_rows", "value": len(rows)}, {"metric": "source_lineages", "value": len(best_by_lineage)},
        {"metric": "trusted_runners", "value": best_counts.get("TRUSTED", 0)}, {"metric": "likely_runners", "value": best_counts.get("LIKELY", 0)},
        {"metric": "partial_runners", "value": best_counts.get("PARTIAL", 0)}, {"metric": "unsafe_runners", "value": best_counts.get("UNSAFE", 0)},
        {"metric": "ambiguous_runners", "value": 0}, {"metric": "unmatched_runners", "value": best_counts.get("UNMATCHED", 0)},
        {"metric": "graph_match_success_pct", "value": f"{((best_counts.get('TRUSTED', 0) + best_counts.get('LIKELY', 0)) / len(best_by_lineage) * 100) if best_by_lineage else 0:.1f}"},
    ]
    summary.extend({"metric": f"status_{key.lower()}", "value": value} for key, value in sorted(status_counts.items()))
    summary.extend({"metric": f"method_{key.lower()}", "value": value} for key, value in sorted(method_counts.items()))
    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ RUNNER ENTITY GRAPH V1")
    print("=" * 90)
    print("GRAPH ROWS:", len(rows))
    print("TRUSTED:", best_counts.get("TRUSTED", 0))
    print("LIKELY:", best_counts.get("LIKELY", 0))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
