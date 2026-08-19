import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

V2_FILE = DATA / "edgeiq_connection_intelligence_v2.csv"
ACTIVE_FILE = DATA / "edgeiq_live_runner_board_v1.csv"
HISTORY_FILE = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"

OPTIONAL_SOURCES = {
    "trainer_track": DATA / "edgeiq_trainer_track_profiles_graphql_v1.csv",
    "jockey_track": DATA / "edgeiq_jockey_track_profiles_graphql_v1.csv",
    "trainer_prep": DATA / "edgeiq_trainer_stage_of_prep_engine_v2_graphql.csv",
    "trainer_jockey_prep": DATA / "edgeiq_trainer_jockey_prep_engine_v2_graphql.csv",
    "sp_profile": DATA / "edgeiq_sp_performance_profiles_graphql_v1.csv",
    "connection_view": DATA / "edgeiq_connection_view_engine_v1.csv",
}

OUT_AUDIT = DATA / "edgeiq_connection_v2_coverage_gap_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_connection_v2_coverage_gap_summary_v1.csv"


AUDIT_FIELDS = [
    "current_race_date",
    "track",
    "race_no",
    "horse",
    "trainer_name",
    "jockey_name",
    "trainer_name_exists",
    "jockey_name_exists",
    "trainer_history_exact",
    "trainer_history_loose",
    "jockey_history_exact",
    "jockey_history_loose",
    "combo_history_exact",
    "combo_history_loose",
    "trainer_history_starts",
    "jockey_history_starts",
    "combo_history_starts",
    "trainer_track_profile_available",
    "jockey_track_profile_available",
    "track_profile_availability",
    "trainer_distance_profile_available",
    "jockey_distance_profile_available",
    "distance_profile_availability",
    "sp_market_profile_available",
    "prep_stage_profile_available",
    "optional_source_match",
    "root_cause",
    "coverage_can_improve",
    "recommended_v21_source",
    "customer_facing_evidence",
]


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def text(value):
    return str(value or "").strip()


def clean_key(value):
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def name_tokens(value):
    raw = text(value).upper().replace("&", " ")
    tokens = []
    for part in raw.replace(".", " ").replace(",", " ").replace("-", " ").split():
        if part in {"AND", "THE", "STABLE", "RACING"}:
            continue
        tokens.append(part)
    return tokens


def initials_key(value):
    tokens = name_tokens(value)
    if not tokens:
        return ""
    compressed = "".join(token[0] if len(token) > 1 else token for token in tokens)
    suffix = "".join(token for token in tokens if len(token) > 1 and token not in {"BEN", "WILL", "TROY", "LEON"})
    return compressed + suffix


def loose_keys(value):
    keys = {clean_key(value), initials_key(value)}
    tokens = name_tokens(value)
    if len(tokens) >= 2:
        keys.add(tokens[-1])
        keys.add("".join(token[0] for token in tokens[:-1]) + tokens[-1])
    return {key for key in keys if key}


def bool_text(value):
    return "YES" if value else "NO"


def has_real_name(value):
    normalized = text(value).upper()
    return bool(normalized) and normalized not in {"NOT NOTIFIED", "TBA", "TBC", "NO RIDER", "UNKNOWN"}


def number(value):
    raw = text(value).replace("$", "").replace(",", "").replace("m", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def distance_bucket(value):
    distance = number(value)
    if distance is None:
        return "UNKNOWN"
    if distance < 1200:
        return "SPRINT"
    if distance < 1400:
        return "SHORT"
    if distance < 1600:
        return "MILE"
    if distance < 2000:
        return "MIDDLE"
    return "STAYING"


def row_value(row, candidates):
    for candidate in candidates:
        value = text(row.get(candidate))
        if value:
            return value
    return ""


def index_optional_source(rows, entity_cols, track_cols=None, distance_cols=None):
    entity_keys = set()
    track_keys = set()
    distance_keys = set()
    for row in rows:
        entity = row_value(row, entity_cols)
        if not entity:
            continue
        for entity_key in loose_keys(entity):
            entity_keys.add(entity_key)
            track = row_value(row, track_cols or [])
            if track:
                track_keys.add((entity_key, clean_key(track)))
            distance = row_value(row, distance_cols or [])
            if distance:
                distance_keys.add((entity_key, distance_bucket(distance)))
    return entity_keys, track_keys, distance_keys


def main():
    built_at = datetime.now(timezone.utc).isoformat()
    v2_rows = read_csv(V2_FILE)
    no_connection_rows = [
        row for row in v2_rows
        if text(row.get("connection_evidence_status")) == "NO_CONNECTION"
        or text(row.get("connection_band")) == "NO_EVIDENCE"
    ]
    active_rows = read_csv(ACTIVE_FILE)
    history_rows = read_csv(HISTORY_FILE)

    trainer_exact = Counter()
    jockey_exact = Counter()
    combo_exact = Counter()
    trainer_loose = Counter()
    jockey_loose = Counter()
    combo_loose = Counter()
    trainer_track = Counter()
    jockey_track = Counter()
    trainer_distance = Counter()
    jockey_distance = Counter()
    trainer_sp = Counter()
    jockey_sp = Counter()
    combo_sp = Counter()

    for row in history_rows:
        if text(row.get("scratched")).lower() in {"true", "1", "yes"}:
            continue
        trainer = row_value(row, ["trainer", "trainer_name"])
        jockey = row_value(row, ["jockey", "jockey_name"])
        if not trainer and not jockey:
            continue
        trainer_key = clean_key(trainer)
        jockey_key = clean_key(jockey)
        track_key = clean_key(row_value(row, ["track", "venue_name"]))
        dist_key = distance_bucket(row_value(row, ["distance", "race_distance"]))
        sp_available = number(row_value(row, ["starting_price_decimal", "starting_price", "sp"])) is not None

        if trainer_key:
            trainer_exact[trainer_key] += 1
            for loose in loose_keys(trainer):
                trainer_loose[loose] += 1
            if track_key:
                trainer_track[(trainer_key, track_key)] += 1
            if dist_key != "UNKNOWN":
                trainer_distance[(trainer_key, dist_key)] += 1
            if sp_available:
                trainer_sp[trainer_key] += 1
        if jockey_key:
            jockey_exact[jockey_key] += 1
            for loose in loose_keys(jockey):
                jockey_loose[loose] += 1
            if track_key:
                jockey_track[(jockey_key, track_key)] += 1
            if dist_key != "UNKNOWN":
                jockey_distance[(jockey_key, dist_key)] += 1
            if sp_available:
                jockey_sp[jockey_key] += 1
        if trainer_key and jockey_key:
            combo_exact[(trainer_key, jockey_key)] += 1
            for trainer_loose_key in loose_keys(trainer):
                for jockey_loose_key in loose_keys(jockey):
                    combo_loose[(trainer_loose_key, jockey_loose_key)] += 1
            if sp_available:
                combo_sp[(trainer_key, jockey_key)] += 1

    optional = {name: read_csv(path) for name, path in OPTIONAL_SOURCES.items() if path.exists()}
    optional_source_status = {name: ("FOUND" if rows else "EMPTY") for name, rows in optional.items()}
    for name, path in OPTIONAL_SOURCES.items():
        optional_source_status.setdefault(name, "MISSING")

    opt_trainer_track_entities, opt_trainer_track, _ = index_optional_source(
        optional.get("trainer_track", []),
        ["trainer", "trainer_name", "entity_name"],
        ["track", "venue", "track_name"],
    )
    opt_jockey_track_entities, opt_jockey_track, _ = index_optional_source(
        optional.get("jockey_track", []),
        ["jockey", "jockey_name", "entity_name"],
        ["track", "venue", "track_name"],
    )
    opt_sp_entities, _, _ = index_optional_source(
        optional.get("sp_profile", []),
        ["trainer", "trainer_name", "jockey", "jockey_name", "entity_name"],
    )
    opt_trainer_prep_entities, _, _ = index_optional_source(
        optional.get("trainer_prep", []),
        ["trainer", "trainer_name", "entity_name"],
    )
    opt_combo_prep_rows = optional.get("trainer_jockey_prep", [])
    opt_combo_prep = set()
    for row in opt_combo_prep_rows:
        trainer = row_value(row, ["trainer", "trainer_name"])
        jockey = row_value(row, ["jockey", "jockey_name"])
        for trainer_key in loose_keys(trainer):
            for jockey_key in loose_keys(jockey):
                opt_combo_prep.add((trainer_key, jockey_key))

    audit_rows = []
    for row in no_connection_rows:
        trainer_name = text(row.get("trainer_name"))
        jockey_name = text(row.get("jockey_name"))
        trainer_key = clean_key(trainer_name)
        jockey_key = clean_key(jockey_name)
        trainer_lkeys = loose_keys(trainer_name)
        jockey_lkeys = loose_keys(jockey_name)
        track_key = clean_key(row.get("track"))
        dist_key = "UNKNOWN"
        active_match = next(
            (
                active for active in active_rows
                if text(active.get("race_date")) == text(row.get("current_race_date"))
                and clean_key(active.get("track")) == track_key
                and text(active.get("race_no")) == text(row.get("race_no"))
                and clean_key(active.get("horse")) == clean_key(row.get("horse"))
            ),
            {},
        )
        if active_match:
            dist_key = distance_bucket(active_match.get("distance"))

        trainer_history_exact = trainer_exact[trainer_key] > 0
        jockey_history_exact = jockey_exact[jockey_key] > 0
        combo_history_exact = combo_exact[(trainer_key, jockey_key)] > 0
        trainer_history_loose_count = max((trainer_loose[key] for key in trainer_lkeys), default=0)
        jockey_history_loose_count = max((jockey_loose[key] for key in jockey_lkeys), default=0)
        combo_history_loose_count = max(
            (combo_loose[(tk, jk)] for tk in trainer_lkeys for jk in jockey_lkeys),
            default=0,
        )

        trainer_track_count = trainer_track[(trainer_key, track_key)]
        jockey_track_count = jockey_track[(jockey_key, track_key)]
        trainer_distance_count = trainer_distance[(trainer_key, dist_key)]
        jockey_distance_count = jockey_distance[(jockey_key, dist_key)]
        sp_count = max(
            trainer_sp[trainer_key],
            jockey_sp[jockey_key],
            combo_sp[(trainer_key, jockey_key)],
        )

        optional_track = any((tk, track_key) in opt_trainer_track for tk in trainer_lkeys) or any((jk, track_key) in opt_jockey_track for jk in jockey_lkeys)
        optional_sp = bool(opt_sp_entities.intersection(trainer_lkeys) or opt_sp_entities.intersection(jockey_lkeys))
        optional_prep = bool(opt_trainer_prep_entities.intersection(trainer_lkeys) or any((tk, jk) in opt_combo_prep for tk in trainer_lkeys for jk in jockey_lkeys))
        optional_match = optional_track or optional_sp or optional_prep

        track_available = trainer_track_count > 0 or jockey_track_count > 0 or optional_track
        distance_available = trainer_distance_count > 0 or jockey_distance_count > 0
        market_available = sp_count > 0 or optional_sp

        exact_missing_but_loose_exists = (
            (not trainer_history_exact and trainer_history_loose_count > 0)
            or (not jockey_history_exact and jockey_history_loose_count > 0)
            or (not combo_history_exact and combo_history_loose_count > 0)
        )
        source_not_used = optional_match or (
            (trainer_track_count > 0 or jockey_track_count > 0 or trainer_distance_count > 0 or jockey_distance_count > 0 or sp_count > 0)
            and not combo_history_exact
        )

        trainer_name_real = has_real_name(trainer_name)
        jockey_name_real = has_real_name(jockey_name)

        if not trainer_name_real:
            root_cause = "MISSING_TRAINER"
        elif not jockey_name_real:
            root_cause = "MISSING_JOCKEY"
        elif exact_missing_but_loose_exists:
            root_cause = "JOIN_KEY_ISSUE"
        elif not trainer_history_exact and trainer_history_loose_count == 0:
            root_cause = "TRAINER_NO_HISTORY"
        elif not jockey_history_exact and jockey_history_loose_count == 0:
            root_cause = "JOCKEY_NO_HISTORY"
        elif not combo_history_exact and combo_history_loose_count == 0:
            root_cause = "COMBO_NO_HISTORY"
        elif source_not_used:
            root_cause = "SOURCE_NOT_USED"
        else:
            root_cause = "TRUE_NO_EVIDENCE"

        can_improve = root_cause in {"JOIN_KEY_ISSUE", "SOURCE_NOT_USED", "COMBO_NO_HISTORY"}
        recommended_source = []
        if exact_missing_but_loose_exists:
            recommended_source.append("name canonicalisation bridge")
        if track_available:
            recommended_source.append("track profile")
        if distance_available:
            recommended_source.append("distance profile")
        if market_available:
            recommended_source.append("SP/market profile")
        if optional_prep:
            recommended_source.append("prep-stage profile")

        customer_evidence = []
        if track_available:
            customer_evidence.append("track")
        if distance_available:
            customer_evidence.append("distance")
        if market_available:
            customer_evidence.append("market outperformance")
        if combo_history_exact or combo_history_loose_count > 0:
            customer_evidence.append("trainer/jockey combination")

        audit_rows.append({
            "current_race_date": text(row.get("current_race_date")),
            "track": text(row.get("track")),
            "race_no": text(row.get("race_no")),
            "horse": text(row.get("horse")),
            "trainer_name": trainer_name,
            "jockey_name": jockey_name,
            "trainer_name_exists": bool_text(trainer_name_real),
            "jockey_name_exists": bool_text(jockey_name_real),
            "trainer_history_exact": bool_text(trainer_history_exact),
            "trainer_history_loose": bool_text(trainer_history_loose_count > 0),
            "jockey_history_exact": bool_text(jockey_history_exact),
            "jockey_history_loose": bool_text(jockey_history_loose_count > 0),
            "combo_history_exact": bool_text(combo_history_exact),
            "combo_history_loose": bool_text(combo_history_loose_count > 0),
            "trainer_history_starts": str(trainer_exact[trainer_key] or trainer_history_loose_count),
            "jockey_history_starts": str(jockey_exact[jockey_key] or jockey_history_loose_count),
            "combo_history_starts": str(combo_exact[(trainer_key, jockey_key)] or combo_history_loose_count),
            "trainer_track_profile_available": bool_text(trainer_track_count > 0 or any((tk, track_key) in opt_trainer_track for tk in trainer_lkeys)),
            "jockey_track_profile_available": bool_text(jockey_track_count > 0 or any((jk, track_key) in opt_jockey_track for jk in jockey_lkeys)),
            "track_profile_availability": bool_text(track_available),
            "trainer_distance_profile_available": bool_text(trainer_distance_count > 0),
            "jockey_distance_profile_available": bool_text(jockey_distance_count > 0),
            "distance_profile_availability": bool_text(distance_available),
            "sp_market_profile_available": bool_text(market_available),
            "prep_stage_profile_available": bool_text(optional_prep),
            "optional_source_match": bool_text(optional_match),
            "root_cause": root_cause,
            "coverage_can_improve": bool_text(can_improve),
            "recommended_v21_source": " | ".join(recommended_source) or "none",
            "customer_facing_evidence": " | ".join(customer_evidence) or "none",
        })

    root_counts = Counter(row["root_cause"] for row in audit_rows)
    improve_count = sum(1 for row in audit_rows if row["coverage_can_improve"] == "YES")
    track_count = sum(1 for row in audit_rows if row["track_profile_availability"] == "YES")
    distance_count = sum(1 for row in audit_rows if row["distance_profile_availability"] == "YES")
    market_count = sum(1 for row in audit_rows if row["sp_market_profile_available"] == "YES")
    prep_count = sum(1 for row in audit_rows if row["prep_stage_profile_available"] == "YES")

    customer_meaningful_additional = len({
        (row["current_race_date"], row["track"], row["race_no"], row["horse"])
        for row in audit_rows
        if row["track_profile_availability"] == "YES"
        or row["distance_profile_availability"] == "YES"
        or row["sp_market_profile_available"] == "YES"
        or row["combo_history_loose"] == "YES"
    })
    realistic_additional = customer_meaningful_additional
    current_non_no = len(v2_rows) - len(no_connection_rows)
    target_realistic = current_non_no + realistic_additional
    if improve_count >= 80:
        v21_recommendation = "BUILD_V2_1"
    elif improve_count >= 25:
        v21_recommendation = "BUILD_V2_1_TARGETED"
    else:
        v21_recommendation = "HOLD_V2_1"

    safest_sources = []
    if track_count:
        safest_sources.append("trainer/jockey track profiles")
    if distance_count:
        safest_sources.append("historical trainer/jockey distance profiles")
    if market_count:
        safest_sources.append("SP market outperformance profiles")
    if prep_count:
        safest_sources.append("prep-stage profile sources")
    if root_counts.get("JOIN_KEY_ISSUE", 0):
        safest_sources.insert(0, "trainer/jockey canonicalisation bridge")

    summary_rows = [
        {"metric": "built_at", "value": built_at},
        {"metric": "input_no_connection_rows", "value": str(len(no_connection_rows))},
        {"metric": "root_cause_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(root_counts.items()))},
        {"metric": "coverage_can_truthfully_improve_rows", "value": str(improve_count)},
        {"metric": "customer_meaningful_improvement_rows", "value": str(customer_meaningful_additional)},
        {"metric": "track_profile_available_rows", "value": str(track_count)},
        {"metric": "distance_profile_available_rows", "value": str(distance_count)},
        {"metric": "sp_market_profile_available_rows", "value": str(market_count)},
        {"metric": "prep_stage_profile_available_rows", "value": str(prep_count)},
        {"metric": "safest_additional_sources", "value": " | ".join(safest_sources) or "none"},
        {"metric": "v2_1_recommendation", "value": v21_recommendation},
        {"metric": "target_realistic_coverage_rows", "value": f"{target_realistic}/370"},
        {"metric": "target_realistic_coverage_pct", "value": f"{target_realistic / 370 * 100:.1f}%"},
        {"metric": "customer_facing_evidence_recommendation", "value": "Show only track/distance/market-outperformance/combo reads with named sample support; keep missing/source diagnostics hidden."},
        {"metric": "optional_source_status", "value": "; ".join(f"{k}={v}" for k, v in sorted(optional_source_status.items()))},
    ]

    write_csv(OUT_AUDIT, audit_rows, AUDIT_FIELDS)
    write_csv(OUT_SUMMARY, summary_rows, ["metric", "value"])
    print(f"audited_no_connection={len(no_connection_rows)} improve_candidates={improve_count} recommendation={v21_recommendation}")


if __name__ == "__main__":
    main()
