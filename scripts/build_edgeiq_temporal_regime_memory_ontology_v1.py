from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_COMPACT = DATA / "edgeiq_telemetry_ontology_compact_v1.csv"
IN_ENVIRONMENT = DATA / "edgeiq_telemetry_ontology_environment_summary_v1.csv"
IN_SIGNAL = DATA / "edgeiq_telemetry_ontology_signal_summary_v1.csv"
IN_COMPRESSION = DATA / "edgeiq_telemetry_ontology_compression_summary_v1.csv"

OUT_MEMORY = DATA / "edgeiq_temporal_regime_memory_ontology_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_temporal_regime_memory_summary_v1.csv"
OUT_DICTIONARY = DATA / "edgeiq_regime_archetype_dictionary_v1.csv"
OUT_WATCHLIST = DATA / "edgeiq_regime_memory_watchlist_v1.csv"

MEMORY_FIELDS = [
    "jurisdiction",
    "track",
    "regime_archetype",
    "signal_family",
    "dominant_state",
    "dominant_phase",
    "dominant_movement",
    "dominant_pressure",
    "ontology_rows",
    "unique_races",
    "unique_horses",
    "safe_cross_research_rows",
    "safe_shadow_research_rows",
    "avg_telemetry_confidence",
    "avg_lineage_confidence",
    "avg_ontology_confidence",
    "regime_persistence_score",
    "regime_stability_grade",
    "regime_research_status",
    "recommended_action",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

DICTIONARY_FIELDS = [
    "regime_archetype",
    "definition",
    "source_signal_family",
    "source_states",
    "source_movements",
    "source_pressures",
    "research_use",
    "promotion_status",
    "notes",
]

WATCHLIST_FIELDS = [
    "watch_type",
    "jurisdiction",
    "track",
    "regime_archetype",
    "issue",
    "severity",
    "affected_rows",
    "recommended_repair",
    "notes",
]

OFFLINE_NOTES = "Temporal regime memory ontology only. No predictions, overlays, ratings, live modelling, execution, or raw jurisdiction merge."


ARCHETYPE_DICTIONARY = [
    {
        "regime_archetype": "LEADER_DOMINANCE_REGIME",
        "definition": "Telemetry clusters where leader state or front-running rank persists as the dominant race-state memory.",
        "source_signal_family": "POSITIONAL_RACE_STATE",
        "source_states": "LEADER_STATE,HIGH_TRUST_STATE",
        "source_movements": "STABLE_POSITION,UNKNOWN_MOVEMENT",
        "source_pressures": "FRONT_PRESSURE",
        "research_use": "Study repeated leader control environments and front-end persistence.",
        "promotion_status": "RESEARCH_ONLY",
        "notes": OFFLINE_NOTES,
    },
    {
        "regime_archetype": "FRONT_PRESSURE_REGIME",
        "definition": "Telemetry clusters where pressure/on-pace states and pace-pressure indicators dominate.",
        "source_signal_family": "POSITIONAL_RACE_STATE",
        "source_states": "PRESSURE_STATE,LEADER_STATE",
        "source_movements": "UNKNOWN_MOVEMENT,STABLE_POSITION",
        "source_pressures": "PACE_PRESSURE,FRONT_PRESSURE",
        "research_use": "Study early pressure and on-speed contest environments.",
        "promotion_status": "RESEARCH_ONLY",
        "notes": OFFLINE_NOTES,
    },
    {
        "regime_archetype": "PACK_COMPRESSION_REGIME",
        "definition": "Telemetry clusters dominated by pack pressure or midfield grouping signals.",
        "source_signal_family": "POSITIONAL_RACE_STATE",
        "source_states": "MIDFIELD_STATE,PRESSURE_STATE",
        "source_movements": "UNKNOWN_MOVEMENT,STABLE_POSITION",
        "source_pressures": "PACK_PRESSURE,PACE_PRESSURE",
        "research_use": "Study compressed-field race-state environments.",
        "promotion_status": "RESEARCH_ONLY",
        "notes": OFFLINE_NOTES,
    },
    {
        "regime_archetype": "MIDFIELD_STABILITY_REGIME",
        "definition": "Telemetry clusters where midfield state and stable movement dominate.",
        "source_signal_family": "POSITIONAL_RACE_STATE",
        "source_states": "MIDFIELD_STATE",
        "source_movements": "STABLE_POSITION,UNKNOWN_MOVEMENT",
        "source_pressures": "PACK_PRESSURE,UNKNOWN_PRESSURE",
        "research_use": "Study stable midfield transit and positional persistence.",
        "promotion_status": "RESEARCH_ONLY",
        "notes": OFFLINE_NOTES,
    },
    {
        "regime_archetype": "LATE_ACCELERATION_REGIME",
        "definition": "Telemetry clusters containing late-phase or advancing movement state memory.",
        "source_signal_family": "TEMPORAL_PHASE,GENERAL_TELEMETRY",
        "source_states": "UNCLASSIFIED_STATE",
        "source_movements": "ADVANCING",
        "source_pressures": "UNKNOWN_PRESSURE",
        "research_use": "Study late acceleration and positive phase-transition environments.",
        "promotion_status": "RESEARCH_ONLY",
        "notes": OFFLINE_NOTES,
    },
    {
        "regime_archetype": "FADING_PRESSURE_REGIME",
        "definition": "Telemetry clusters where fading movement or decay pressure dominates.",
        "source_signal_family": "GENERAL_TELEMETRY,TEMPORAL_PHASE",
        "source_states": "UNCLASSIFIED_STATE",
        "source_movements": "FADING",
        "source_pressures": "PACE_PRESSURE,PACK_PRESSURE,UNKNOWN_PRESSURE",
        "research_use": "Study runner and environment decay patterns.",
        "promotion_status": "RESEARCH_ONLY",
        "notes": OFFLINE_NOTES,
    },
    {
        "regime_archetype": "DECAYING_TELEMETRY_REGIME",
        "definition": "Telemetry-health clusters with drift, degradation, or decay-like states.",
        "source_signal_family": "TELEMETRY_HEALTH,LINEAGE_PROVENANCE",
        "source_states": "DEGRADED_STATE,UNCLASSIFIED_STATE",
        "source_movements": "UNKNOWN_MOVEMENT",
        "source_pressures": "UNKNOWN_PRESSURE",
        "research_use": "Monitor weakening telemetry payload or lineage quality.",
        "promotion_status": "RESEARCH_ONLY",
        "notes": OFFLINE_NOTES,
    },
    {
        "regime_archetype": "HIGH_TRUST_TELEMETRY_REGIME",
        "definition": "Telemetry clusters with high confidence, high trust, or stable lineage states.",
        "source_signal_family": "GENERAL_TELEMETRY,LINEAGE_PROVENANCE,SPEED_GPS_TELEMETRY",
        "source_states": "HIGH_TRUST_STATE,UNCLASSIFIED_STATE",
        "source_movements": "UNKNOWN_MOVEMENT",
        "source_pressures": "UNKNOWN_PRESSURE",
        "research_use": "Use as a trust/reference layer for telemetry infrastructure research.",
        "promotion_status": "RESEARCH_ONLY",
        "notes": OFFLINE_NOTES,
    },
    {
        "regime_archetype": "LOW_CONFIDENCE_NOISE_REGIME",
        "definition": "Low confidence or low shadow-safe telemetry clusters requiring repair before deeper research.",
        "source_signal_family": "ANY",
        "source_states": "ANY",
        "source_movements": "ANY",
        "source_pressures": "ANY",
        "research_use": "Backlog and quality-control detection.",
        "promotion_status": "BLOCKED",
        "notes": OFFLINE_NOTES,
    },
    {
        "regime_archetype": "GENERAL_UNCLASSIFIED_REGIME",
        "definition": "Compressed ontology states that are useful as descriptive memory but do not yet resolve to a behavioural archetype.",
        "source_signal_family": "ANY",
        "source_states": "UNCLASSIFIED_STATE,UNKNOWN_STATE",
        "source_movements": "UNKNOWN_MOVEMENT",
        "source_pressures": "UNKNOWN_PRESSURE",
        "research_use": "Descriptive telemetry memory and future ontology refinement.",
        "promotion_status": "RESEARCH_ONLY",
        "notes": OFFLINE_NOTES,
    },
]


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_int(value: object) -> int:
    try:
        return int(float(clean(value).replace(",", "") or 0))
    except ValueError:
        return 0


def parse_float(value: object) -> float:
    try:
        return float(clean(value).replace(",", "") or 0)
    except ValueError:
        return 0.0


def classify_archetype(row: dict[str, str]) -> str:
    family = upper(row.get("universal_signal_family"))
    state = upper(row.get("universal_state"))
    phase = upper(row.get("universal_phase"))
    movement = upper(row.get("universal_movement"))
    pressure = upper(row.get("universal_pressure"))
    raw_signal = upper(row.get("dominant_raw_signal"))
    rows = parse_int(row.get("rows"))
    avg_ontology = parse_float(row.get("avg_ontology_confidence"))
    safe_shadow = parse_int(row.get("safe_shadow_research_yes"))

    if avg_ontology < 55 or (rows >= 100 and safe_shadow == 0 and family not in {"TEMPORAL_PHASE", "SPEED_GPS_TELEMETRY", "POSITIONAL_RACE_STATE"}):
        return "LOW_CONFIDENCE_NOISE_REGIME"
    if "DRIFT" in raw_signal or "DEGRAD" in state or "DECAY" in raw_signal:
        return "DECAYING_TELEMETRY_REGIME"
    if "LEADER" in state or pressure == "FRONT_PRESSURE":
        return "LEADER_DOMINANCE_REGIME"
    if "PRESSURE" in state or pressure == "PACE_PRESSURE":
        return "FRONT_PRESSURE_REGIME"
    if pressure == "PACK_PRESSURE":
        return "PACK_COMPRESSION_REGIME"
    if "MIDFIELD" in state:
        return "MIDFIELD_STABILITY_REGIME"
    if movement == "ADVANCING" or phase == "LATE_PHASE":
        return "LATE_ACCELERATION_REGIME"
    if movement == "FADING":
        return "FADING_PRESSURE_REGIME"
    if avg_ontology >= 85 and family in {"SPEED_GPS_TELEMETRY", "TEMPORAL_PHASE", "LINEAGE_PROVENANCE", "GENERAL_TELEMETRY"}:
        return "HIGH_TRUST_TELEMETRY_REGIME"
    return "GENERAL_UNCLASSIFIED_REGIME"


def persistence_score(rows: int, unique_races: int, unique_horses: int, safe_cross: int, safe_shadow: int, avg_ontology: float) -> float:
    row_component = min(30.0, rows / 1000 * 30.0)
    race_component = min(20.0, unique_races / 50 * 20.0)
    horse_component = min(15.0, unique_horses / 250 * 15.0)
    cross_component = min(15.0, (safe_cross / rows * 15.0) if rows else 0.0)
    shadow_component = min(10.0, (safe_shadow / rows * 10.0) if rows else 0.0)
    confidence_component = min(10.0, avg_ontology / 100 * 10.0)
    return round(row_component + race_component + horse_component + cross_component + shadow_component + confidence_component, 2)


def stability_grade(rows: int, unique_races: int, safe_shadow: int, avg_ontology: float, persistence: float, archetype: str) -> tuple[str, str]:
    if archetype == "LOW_CONFIDENCE_NOISE_REGIME" or rows <= 0:
        return "F", "BLOCKED_REGIME"
    if rows >= 5000 and unique_races >= 20 and safe_shadow >= 100 and avg_ontology >= 80 and persistence >= 70:
        return "A", "HIGH_TRUST_REPEATING_REGIME"
    if rows >= 1000 and unique_races >= 10 and avg_ontology >= 70 and persistence >= 50:
        return "B", "USABLE_REPEATING_REGIME"
    if rows >= 50 and avg_ontology >= 55:
        return "C", "DESCRIPTIVE_REGIME"
    if rows > 0:
        return "D", "LOW_SAMPLE_OR_NOISY_REGIME"
    return "F", "BLOCKED_REGIME"


def recommended_action(grade: str, archetype: str, safe_shadow: int) -> str:
    if grade == "A":
        return "Maintain offline longitudinal memory and monitor cross-jurisdiction recurrence."
    if grade == "B":
        return "Keep in offline shadow research memory; validate persistence before any future review."
    if grade == "C":
        return "Use descriptively; improve ontology specificity and repeat-race density."
    if archetype == "LOW_CONFIDENCE_NOISE_REGIME":
        return "Repair source confidence, lineage, or signal classification before research use."
    if safe_shadow == 0:
        return "Accumulate shadow-safe rows before stability interpretation."
    return "Accumulate more observations before behavioural interpretation."


def build_memory_rows(compact_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    memory: list[dict[str, object]] = []
    for row in compact_rows:
        rows = parse_int(row.get("rows"))
        unique_races = parse_int(row.get("unique_races"))
        unique_horses = parse_int(row.get("unique_horses"))
        safe_cross = parse_int(row.get("safe_cross_research_yes"))
        safe_shadow = parse_int(row.get("safe_shadow_research_yes"))
        avg_tel = parse_float(row.get("avg_telemetry_confidence"))
        avg_lineage = parse_float(row.get("avg_lineage_confidence"))
        avg_ontology = parse_float(row.get("avg_ontology_confidence"))
        archetype = classify_archetype(row)
        persistence = persistence_score(rows, unique_races, unique_horses, safe_cross, safe_shadow, avg_ontology)
        grade, status = stability_grade(rows, unique_races, safe_shadow, avg_ontology, persistence, archetype)
        memory.append(
            {
                "jurisdiction": row.get("jurisdiction", ""),
                "track": row.get("track", ""),
                "regime_archetype": archetype,
                "signal_family": row.get("universal_signal_family", ""),
                "dominant_state": row.get("universal_state", ""),
                "dominant_phase": row.get("universal_phase", ""),
                "dominant_movement": row.get("universal_movement", ""),
                "dominant_pressure": row.get("universal_pressure", ""),
                "ontology_rows": str(rows),
                "unique_races": str(unique_races),
                "unique_horses": str(unique_horses),
                "safe_cross_research_rows": str(safe_cross),
                "safe_shadow_research_rows": str(safe_shadow),
                "avg_telemetry_confidence": f"{avg_tel:.2f}",
                "avg_lineage_confidence": f"{avg_lineage:.2f}",
                "avg_ontology_confidence": f"{avg_ontology:.2f}",
                "regime_persistence_score": f"{persistence:.2f}",
                "regime_stability_grade": grade,
                "regime_research_status": status,
                "recommended_action": recommended_action(grade, archetype, safe_shadow),
                "notes": OFFLINE_NOTES,
            }
        )
    memory.sort(key=lambda item: (-parse_float(item.get("regime_persistence_score")), item.get("jurisdiction", ""), item.get("track", ""), item.get("regime_archetype", "")))
    return memory


def build_watchlist(memory_rows: list[dict[str, object]], environment_rows: list[dict[str, str]], signal_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    watchlist: list[dict[str, object]] = []
    for row in memory_rows:
        grade = clean(row.get("regime_stability_grade"))
        archetype = clean(row.get("regime_archetype"))
        rows = parse_int(row.get("ontology_rows"))
        safe_shadow = parse_int(row.get("safe_shadow_research_rows"))
        avg_ontology = parse_float(row.get("avg_ontology_confidence"))
        if grade in {"F", "D"}:
            watchlist.append(
                {
                    "watch_type": "REGIME_QUALITY_BLOCKER",
                    "jurisdiction": row.get("jurisdiction", ""),
                    "track": row.get("track", ""),
                    "regime_archetype": archetype,
                    "issue": "Low sample, low confidence, or noisy ontology regime.",
                    "severity": "HIGH" if grade == "F" else "MEDIUM",
                    "affected_rows": str(rows),
                    "recommended_repair": recommended_action(grade, archetype, safe_shadow),
                    "notes": OFFLINE_NOTES,
                }
            )
        elif safe_shadow == 0 and rows >= 1000:
            watchlist.append(
                {
                    "watch_type": "NO_SHADOW_SAFE_MEMORY",
                    "jurisdiction": row.get("jurisdiction", ""),
                    "track": row.get("track", ""),
                    "regime_archetype": archetype,
                    "issue": "Large regime memory has no shadow-safe rows.",
                    "severity": "MEDIUM",
                    "affected_rows": str(rows),
                    "recommended_repair": "Improve shadow research eligibility or keep as cross-jurisdiction descriptive memory only.",
                    "notes": OFFLINE_NOTES,
                }
            )
        elif avg_ontology < 65:
            watchlist.append(
                {
                    "watch_type": "LOW_ONTOLOGY_CONFIDENCE",
                    "jurisdiction": row.get("jurisdiction", ""),
                    "track": row.get("track", ""),
                    "regime_archetype": archetype,
                    "issue": "Ontology confidence below stable-memory threshold.",
                    "severity": "MEDIUM",
                    "affected_rows": str(rows),
                    "recommended_repair": "Improve source lineage and signal normalisation before deeper regime interpretation.",
                    "notes": OFFLINE_NOTES,
                }
            )

    for row in environment_rows:
        if clean(row.get("environment_grade")) in {"D", "F"}:
            watchlist.append(
                {
                    "watch_type": "ENVIRONMENT_MEMORY_WEAK",
                    "jurisdiction": row.get("jurisdiction", ""),
                    "track": row.get("track", ""),
                    "regime_archetype": "ENVIRONMENT_SUMMARY",
                    "issue": "Compressed environment has weak or blocked memory quality.",
                    "severity": "LOW",
                    "affected_rows": row.get("rows", "0"),
                    "recommended_repair": "Accumulate cleaner telemetry rows and validate cross-source consistency.",
                    "notes": OFFLINE_NOTES,
                }
            )

    for row in signal_rows:
        if parse_float(row.get("avg_ontology_confidence")) < 55:
            watchlist.append(
                {
                    "watch_type": "SIGNAL_MEMORY_WEAK",
                    "jurisdiction": row.get("jurisdiction", ""),
                    "track": "ALL",
                    "regime_archetype": classify_archetype(
                        {
                            "universal_signal_family": row.get("universal_signal_family", ""),
                            "universal_state": row.get("universal_state", ""),
                            "universal_phase": row.get("universal_phase", ""),
                            "universal_movement": row.get("universal_movement", ""),
                            "universal_pressure": row.get("universal_pressure", ""),
                            "dominant_raw_signal": row.get("dominant_raw_signal", ""),
                            "avg_ontology_confidence": row.get("avg_ontology_confidence", ""),
                            "rows": row.get("rows", ""),
                            "safe_shadow_research_yes": row.get("safe_shadow_research_yes", ""),
                        }
                    ),
                    "issue": "Universal signal family has weak ontology confidence.",
                    "severity": "MEDIUM",
                    "affected_rows": row.get("rows", "0"),
                    "recommended_repair": "Review universal state mapping and source-specific signal definitions.",
                    "notes": OFFLINE_NOTES,
                }
            )

    watchlist.sort(key=lambda item: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(clean(item.get("severity")), 3), -parse_int(item.get("affected_rows"))))
    return watchlist


def summary_value(rows: list[dict[str, object]], status: str) -> int:
    return sum(1 for row in rows if clean(row.get("regime_research_status")) == status)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    compact_rows = safe_read_csv(IN_COMPACT)
    environment_rows = safe_read_csv(IN_ENVIRONMENT)
    signal_rows = safe_read_csv(IN_SIGNAL)
    compression_summary = safe_read_csv(IN_COMPRESSION)

    memory_rows = build_memory_rows(compact_rows)
    watchlist_rows = build_watchlist(memory_rows, environment_rows, signal_rows)

    write_csv_atomic(OUT_MEMORY, memory_rows, MEMORY_FIELDS)
    write_csv_atomic(OUT_DICTIONARY, ARCHETYPE_DICTIONARY, DICTIONARY_FIELDS)
    write_csv_atomic(OUT_WATCHLIST, watchlist_rows, WATCHLIST_FIELDS)

    jurisdictions = {clean(row.get("jurisdiction")) for row in memory_rows if clean(row.get("jurisdiction"))}
    tracks = {clean(row.get("track")) for row in memory_rows if clean(row.get("track"))}
    safe_cross = sum(parse_int(row.get("safe_cross_research_rows")) for row in memory_rows)
    safe_shadow = sum(parse_int(row.get("safe_shadow_research_rows")) for row in memory_rows)
    grade_counts = Counter(clean(row.get("regime_stability_grade")) for row in memory_rows)
    missing_inputs = []
    for path in (IN_COMPACT, IN_ENVIRONMENT, IN_SIGNAL, IN_COMPRESSION):
        if not path.exists():
            missing_inputs.append(path.name)

    summary = [
        {"metric": "regime_rows", "value": str(len(memory_rows))},
        {"metric": "archetype_dictionary_rows", "value": str(len(ARCHETYPE_DICTIONARY))},
        {"metric": "watchlist_rows", "value": str(len(watchlist_rows))},
        {"metric": "high_trust_repeating_regimes", "value": str(summary_value(memory_rows, "HIGH_TRUST_REPEATING_REGIME"))},
        {"metric": "usable_repeating_regimes", "value": str(summary_value(memory_rows, "USABLE_REPEATING_REGIME"))},
        {"metric": "descriptive_regimes", "value": str(summary_value(memory_rows, "DESCRIPTIVE_REGIME"))},
        {"metric": "blocked_regimes", "value": str(summary_value(memory_rows, "BLOCKED_REGIME"))},
        {"metric": "grade_A_rows", "value": str(grade_counts.get("A", 0))},
        {"metric": "grade_B_rows", "value": str(grade_counts.get("B", 0))},
        {"metric": "grade_C_rows", "value": str(grade_counts.get("C", 0))},
        {"metric": "grade_D_rows", "value": str(grade_counts.get("D", 0))},
        {"metric": "grade_F_rows", "value": str(grade_counts.get("F", 0))},
        {"metric": "jurisdictions_covered", "value": str(len(jurisdictions))},
        {"metric": "tracks_covered", "value": str(len(tracks))},
        {"metric": "safe_cross_research_rows", "value": str(safe_cross)},
        {"metric": "safe_shadow_research_rows", "value": str(safe_shadow)},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "missing_inputs", "value": ";".join(missing_inputs)},
        {"metric": "source_compression_rows", "value": next((row.get("value", "") for row in compression_summary if row.get("metric") == "compact_rows"), "")},
    ]
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)

    print(f"Temporal regime memory rows: {len(memory_rows)}")
    print(f"Archetype dictionary rows: {len(ARCHETYPE_DICTIONARY)}")
    print(f"Watchlist rows: {len(watchlist_rows)}")
    print(f"Jurisdictions: {len(jurisdictions)}")
    print(f"Tracks: {len(tracks)}")


if __name__ == "__main__":
    main()
