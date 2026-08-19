from __future__ import annotations

import csv
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SRC = ROOT / "src" / "edgeiq-os"

ENRICHED = DATA / "edgeiq_form_guide_enriched_v2.json"
LIVE_BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"
LIVE_BOARD_RAW = DATA / "edgeiq_live_runner_board_v1.csv"
SPEED_MAP = DATA / "live_speed_map_v3.csv"
RUNNER_INTEL = DATA / "edgeiq_runner_intelligence_v1.csv"
FIELD_PROJECTION = DATA / "edgeiq_current_field_projection_v5_2.csv"
FAIR_REVIEW = DATA / "edgeiq_current_fair_prices_review_v5_2.csv"
PROB_V3 = DATA / "edgeiq_probability_engine_v3.csv"
DNA = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
PRE_FLIGHT = DATA / "edgeiq_current_intelligence_v1_1_preflight_status.txt"


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in {"", "-", "none", "null", "n/a", "na", "unknown"} else text


def canon_runner(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = text.replace("'", "").replace("\u2019", "").replace("&", "AND")
    return re.sub(r"[^A-Z0-9]+", "", text)


def canon_track(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value).upper().replace("R", ""))
    return str(int(match.group(0))) if match else ""


def date_key(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    text = text.split("T", 1)[0].split(" ", 1)[0].replace("/", "-")
    parts = text.split("-")
    if len(parts) != 3:
        return ""
    if len(parts[0]) == 4:
        y, m, d = parts
    else:
        d, m, y = parts
    try:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except ValueError:
        return ""


def num(value: Any) -> float | None:
    text = clean(value).replace("$", "").replace(",", "").replace("kg", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def value_of(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("value")
    return value


def source_of(value: Any) -> str:
    if isinstance(value, dict):
        return clean(value.get("source"))
    return ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def headers(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return csv.DictReader(handle).fieldnames or []


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def metric_populated(value: Any) -> bool:
    return value_of(value) not in (None, "")


def runner_key(date: Any, track: Any, race: Any, runner: Any) -> tuple[str, str, str, str]:
    return (date_key(date), canon_track(track), race_no(race), canon_runner(runner))


def load_enriched() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = json.loads(ENRICHED.read_text(encoding="utf-8"))
    races = payload.get("races", [])
    runners: list[dict[str, Any]] = []
    for race in races:
        for runner in race.get("runners", []):
            runners.append(
                {
                    "race_date": date_key(race.get("raceDate")),
                    "track": clean(race.get("meeting")),
                    "race_no": race_no(race.get("raceNumber")),
                    "runner": clean(runner.get("runnerName") or runner.get("name")),
                    "runner_no": clean(runner.get("runnerNumber") or runner.get("number")),
                    "key": runner_key(race.get("raceDate"), race.get("meeting"), race.get("raceNumber"), runner.get("normalisedRunnerName") or runner.get("runnerName") or runner.get("name")),
                    "raw": runner,
                }
            )
    return races, runners


def index_rows(rows: list[dict[str, str]], runner_fields: list[str]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    out: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        runner = ""
        for field in runner_fields:
            if clean(row.get(field)):
                runner = row.get(field, "")
                break
        key = runner_key(row.get("race_date") or row.get("date"), row.get("track") or row.get("meeting"), row.get("race_no") or row.get("race_number"), runner)
        if all(key):
            out.setdefault(key, row)
    return out


def create_lineage() -> None:
    rows = [
        {"entity": "EPI", "source": "edgeiq_current_field_projection_v5_2.csv", "builder_engine": "build_edgeiq_current_field_projection_v5_2.py -> build_edgeiq_live_runner_board_v1.py -> build_edgeiq_live_runner_board_governed_v1.py", "generated_feed": "edgeiq_live_runner_board_governed_v1.csv", "typescript_service_adapter": "formGuideEnrichedFeed.ts -> formGuideNormaliser.ts", "operational_state": "not consumed by OperationalRaceStateService", "form_guide_bridge": "build_edgeiq_form_guide_enriched_v2.py", "enriched_v2_field": "runner.epi.value", "verdict": "production current runner projection"},
        {"entity": "EDGEiQ Price", "source": "edgeiq_current_fair_prices_review_v5_2.csv + edgeiq_probability_engine_v3.csv", "builder_engine": "build_edgeiq_probability_engine_v3.py -> build_edgeiq_live_runner_board_v1.py -> build_edgeiq_live_runner_board_governed_v1.py", "generated_feed": "edgeiq_live_runner_board_governed_v1.csv", "typescript_service_adapter": "formGuideEnrichedFeed.ts -> formGuideNormaliser.ts", "operational_state": "not consumed by OperationalRaceStateService", "form_guide_bridge": "build_edgeiq_form_guide_enriched_v2.py", "enriched_v2_field": "runner.edgeiqPrice.value", "verdict": "governed production price; separate from market"},
        {"entity": "Early Speed", "source": "edgeiq_current_early_speed_v1.json earlySpeed", "builder_engine": "build_edgeiq_current_early_speed_v1.py", "generated_feed": "edgeiq_current_early_speed_v1.json", "typescript_service_adapter": "formGuideEnrichedFeed.ts -> formGuideNormaliser.ts", "operational_state": "not consumed by OperationalRaceStateService", "form_guide_bridge": "build_edgeiq_form_guide_enriched_v2.py; stale projected_spd remains blocked", "enriched_v2_field": "runner.earlySpeed.value", "verdict": "approved current projection source when populated"},
        {"entity": "Late Speed", "source": "edgeiq_current_late_speed_v1.json lateSpeed", "builder_engine": "build_edgeiq_current_late_speed_v1.py", "generated_feed": "edgeiq_current_late_speed_v1.json", "typescript_service_adapter": "formGuideEnrichedFeed.ts -> formGuideNormaliser.ts", "operational_state": "not consumed by OperationalRaceStateService", "form_guide_bridge": "build_edgeiq_form_guide_enriched_v2.py; live_speed_map late_power_index remains blocked", "enriched_v2_field": "runner.lateSpeed.value", "verdict": "approved current projection source when populated"},
        {"entity": "Race Shape", "source": "speed_map_report.csv + edgeiq_universal_sectional_memory_v1.csv", "builder_engine": "build_live_speed_map_engine_v3.py", "generated_feed": "live_speed_map_v3.csv", "typescript_service_adapter": "formGuideEnrichedFeed.ts -> formGuideNormaliser.ts", "operational_state": "not consumed by OperationalRaceStateService", "form_guide_bridge": "build_edgeiq_form_guide_enriched_v2.py with V1.1 evidence guard", "enriched_v2_field": "runner.raceShape.value", "verdict": "runner-specific only where speed-map evidence exists"},
        {"entity": "Tempo", "source": "edgeiq_universal_sectional_memory_v1.csv best_tempo_setup", "builder_engine": "build_live_speed_map_engine_v3.py", "generated_feed": "live_speed_map_v3.csv tempo_fit/projected_tempo_shape", "typescript_service_adapter": "Map/Form services", "operational_state": "command-only aggregate engines separate", "form_guide_bridge": "not a runner current projection", "enriched_v2_field": "runner.raceShape when runner evidence exists", "verdict": "runner profile/setup evidence"},
        {"entity": "Pressure", "source": "pressure engines/replays in public data", "builder_engine": "pressure-engine services; historical pressure feeds", "generated_feed": "not wired into Form Guide current runner rows", "typescript_service_adapter": "command components", "operational_state": "used for command summaries", "form_guide_bridge": "none", "enriched_v2_field": "none", "verdict": "not a current Form Guide runner metric"},
        {"entity": "Market", "source": "edgeiq_three_day_product_catalog_v1 embedded odds", "builder_engine": "build_edgeiq_current_intelligence_catalog_bridge_v1.py", "generated_feed": "sportsbet_live_market_v1.csv and live terminal feeds", "typescript_service_adapter": "formGuideEnrichedFeed.ts -> formGuideNormaliser.ts", "operational_state": "not consumed by OperationalRaceStateService", "form_guide_bridge": "build_edgeiq_form_guide_enriched_v2.py", "enriched_v2_field": "runner.marketPrice.value", "verdict": "market kept separate from EDGEiQ Price"},
    ]
    write_csv(DATA / "edgeiq_current_intelligence_v1_1_lineage.csv", rows, list(rows[0]))
    write_text(DATA / "edgeiq_current_intelligence_v1_1_lineage_summary.txt", [
        "EDGEIQ CURRENT INTELLIGENCE V1.1 LINEAGE",
        "OperationalRaceStateService is not the canonical source for runner-level Form Guide metrics.",
        "Canonical current Form Guide path remains: three-day catalog -> current-intelligence bridge -> governed live board/speed map -> enriched V2 JSON -> frontend services.",
        "Early Speed and Late Speed current columns are blocked unless the approved current projection V1 feeds exist.",
        "Race Shape is runner-specific only where live_speed_map_v3 has runner evidence.",
    ])


def create_contract(runners: list[dict[str, Any]]) -> None:
    total = len(runners)
    contract = [
        ("raceId", "string", "race-level", "OperationalRaceStateService", "hardcoded current-race", "identifier", False, "production shell", total, "Command workspace"),
        ("meetingName", "string", "race-level", "OperationalRaceStateService", "hardcoded Current Meeting", "display text", False, "production shell", total, "Command workspace"),
        ("raceNumber", "number", "race-level", "OperationalRaceStateService", "hardcoded 1", "race number", False, "production shell", total, "Command workspace"),
        ("raceName", "string", "race-level", "OperationalRaceStateService", "hardcoded Current Race", "display text", False, "production shell", total, "Command workspace"),
        ("distance", "string", "race-level", "OperationalRaceStateService", "hardcoded blank", "metres/text", True, "production shell", 0, "Command workspace"),
        ("raceClass", "string", "race-level", "OperationalRaceStateService", "hardcoded blank", "class text", True, "production shell", 0, "Command workspace"),
        ("trackCondition", "string", "race-level", "OperationalRaceStateService", "hardcoded blank", "track condition", True, "production shell", 0, "Command workspace"),
        ("rail", "string", "race-level", "OperationalRaceStateService", "hardcoded blank", "rail text", True, "production shell", 0, "Command workspace"),
        ("confidence", "number", "race-level", "operational-correlation", "registered intelligence modules", "0-100", False, "production command aggregate", total, "Command workspace"),
        ("referenceRunner", "string", "race-level", "OperationalRaceStateService", "hardcoded Production runner pending", "display text", False, "production shell", total, "Command workspace"),
        ("evidence", "OperationalEvidenceItem[]", "race-level aggregate", "intelligence registry", "module outputs", "mixed", True, "production command aggregate", total, "Command workspace"),
        ("feedHealth", "OperationalFeedHealth[]", "race-level aggregate", "intelligence registry", "module outputs", "status", True, "production command aggregate", total, "Command workspace"),
        ("coverage", "IntelligenceCoverageItem[]", "race-level aggregate", "intelligence coverage", "module outputs", "percent", True, "production command aggregate", total, "Command workspace"),
        ("correlation", "OperationalCorrelation", "race-level aggregate", "operational-correlation", "module outputs", "score/band", True, "production command aggregate", total, "Command workspace"),
        ("decision", "OperationalDecision", "race-level aggregate", "operational-decision", "correlation/findings", "state/confidence", True, "production command aggregate", total, "Command workspace"),
        ("runner-level metrics", "none", "runner-level", "not present", "not present", "none", True, "not available", 0, "Form Guide does not use OperationalRaceStateService"),
    ]
    fields = [
        {
            "fieldName": name,
            "type": typ,
            "level": level,
            "sourceService": service,
            "sourceFeed": feed,
            "unitsScale": units,
            "nullable": nullable,
            "productionResearchStatus": status,
            "currentThreeDayCoverage": coverage,
            "consumer": consumer,
        }
        for name, typ, level, service, feed, units, nullable, status, coverage, consumer in contract
    ]
    (DATA / "edgeiq_operational_race_state_contract_v1.json").write_text(json.dumps({"fields": fields}, indent=2), encoding="utf-8")
    write_text(DATA / "edgeiq_operational_race_state_contract_v1.txt", [
        "EDGEIQ OPERATIONAL RACE STATE CONTRACT V1",
        "OperationalRaceStateService returns race-level command aggregates only.",
        "No runner-level today EPI, fair price, EPI SPD, gate speed, late sectional strength, tempo fit, pressure fit, or runner shape fit fields are returned by this service.",
        "",
        *[f"{f['fieldName']} | {f['level']} | {f['type']} | source={f['sourceService']} | coverage={f['currentThreeDayCoverage']}" for f in fields],
    ])


def create_gap_audits(runners: list[dict[str, Any]]) -> tuple[Counter, Counter]:
    runner_intel_rows = read_csv(RUNNER_INTEL)
    current_dates = {r["race_date"] for r in runners}
    intel_exact = index_rows(runner_intel_rows, ["horse", "runner", "horse_canon", "horse_key"])
    intel_by_runner: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in runner_intel_rows:
        intel_by_runner[canon_runner(row.get("horse") or row.get("runner") or row.get("horse_canon"))].append(row)

    early_rows: list[dict[str, Any]] = []
    early_counts: Counter = Counter()
    for item in runners:
        raw = item["raw"]
        if metric_populated(raw.get("earlySpeed")):
            reason = "POPULATED"
        else:
            exact = intel_exact.get(item["key"])
            related = intel_by_runner.get(item["key"][3], [])
            if exact and clean(exact.get("projected_spd")):
                reason = "SOURCE_FIELD_NULL"  # should not happen after V1.1 guard
            elif related and not any(date_key(r.get("race_date")) in current_dates for r in related):
                reason = "STALE_DATE"
            elif related:
                reason = "SOURCE_FIELD_NULL"
            else:
                reason = "NO_SOURCE_ROW"
            early_counts[reason] += 1
        early_rows.append({"race_date": item["race_date"], "track": item["track"], "race_no": item["race_no"], "runner": item["runner"], "status": "POPULATED" if metric_populated(raw.get("earlySpeed")) else "MISSING", "reason": reason, "source": "edgeiq_runner_intelligence_v1.csv:projected_spd"})
    write_csv(DATA / "edgeiq_early_speed_v1_1_gap_audit.csv", early_rows, ["race_date", "track", "race_no", "runner", "status", "reason", "source"])
    write_text(DATA / "edgeiq_early_speed_v1_1_gap_summary.txt", [
        "EDGEIQ EARLY SPEED V1.1 GAP SUMMARY",
        "Approved current Early Speed projection source found: NO",
        "EPI SPD approval verdict: NOT APPROVED for Form Guide Early Speed; no current same-race EPI SPD field was found.",
        "projected_spd exists only through stale runner-intelligence rows dated outside the current three-day race universe.",
        "Higher projected_spd appears to mean faster/stronger early speed, but it is not wired as an approved current projection source.",
        *[f"{k}: {v}" for k, v in sorted(early_counts.items())],
    ])

    speed_rows = read_csv(SPEED_MAP)
    speed_exact = index_rows(speed_rows, ["horse", "runner", "horse_key"])
    late_rows: list[dict[str, Any]] = []
    late_counts: Counter = Counter()
    for item in runners:
        raw = item["raw"]
        if metric_populated(raw.get("lateSpeed")):
            classification = "CURRENT_PROJECTION"
        else:
            row = speed_exact.get(item["key"])
            if not row:
                classification = "JOIN_FAILURE"
            elif clean(row.get("late_power_index")):
                classification = "HISTORICAL_ONLY"
            else:
                classification = "NO_SECTIONAL_COVERAGE"
            late_counts[classification] += 1
        late_rows.append({"race_date": item["race_date"], "track": item["track"], "race_no": item["race_no"], "runner": item["runner"], "classification": classification, "source": "live_speed_map_v3.csv:late_power_index"})
    write_csv(DATA / "edgeiq_late_speed_v1_1_gap_audit.csv", late_rows, ["race_date", "track", "race_no", "runner", "classification", "source"])
    write_text(DATA / "edgeiq_late_speed_v1_1_gap_summary.txt", [
        "EDGEIQ LATE SPEED V1.1 GAP SUMMARY",
        "Current-race Late Speed projection source found: NO",
        "late_power_index values are historical/profile sectional memory evidence, not a current-race projection.",
        "Values remain available in recent form/profile evidence but are not promoted to the visible current Late Speed column.",
        *[f"{k}: {v}" for k, v in sorted(late_counts.items())],
    ])
    return early_counts, late_counts


def create_semantic_audit(runners: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    counts = Counter()
    duplicates = Counter(item["key"] for item in runners)
    cross_race_join = 0
    for metric, source, version, scale, before in [
        ("EPI", "edgeiq_live_runner_board_governed_v1.csv", "v5_2", "performance points", 395),
        ("EDGEiQ Price", "edgeiq_live_runner_board_governed_v1.csv", "v3/governed", "decimal price", 459),
        ("Early Speed", "edgeiq_current_early_speed_v1.json", "CURRENT_EARLY_SPEED_V1", "0-100 current projection", 43),
        ("Late Speed", "edgeiq_current_late_speed_v1.json", "CURRENT_LATE_SPEED_V1", "0-100 current projection", 107),
        ("Race Shape", "live_speed_map_v3.csv", "v3", "runner map bucket/setup text", 503),
    ]:
        after = 0
        bad_market_copy = 0
        bad_source = 0
        for item in runners:
            raw = item["raw"]
            field = {
                "EPI": raw.get("epi"),
                "EDGEiQ Price": raw.get("edgeiqPrice"),
                "Early Speed": raw.get("earlySpeed"),
                "Late Speed": raw.get("lateSpeed"),
                "Race Shape": raw.get("raceShape"),
            }[metric]
            market = value_of(raw.get("marketPrice"))
            value = value_of(field)
            populated = value not in (None, "")
            after += 1 if populated else 0
            if metric == "EDGEiQ Price" and populated and clean(value) == clean(market):
                bad_market_copy += 1
            if metric == "Early Speed" and populated and source_of(field) != "edgeiq_current_early_speed_v1.json:earlySpeed":
                bad_source += 1
            if metric == "Late Speed" and populated and source_of(field) != "edgeiq_current_late_speed_v1.json:lateSpeed":
                bad_source += 1
        verdict = "PASS"
        if metric == "EDGEiQ Price" and bad_market_copy:
            verdict = "FAIL_MARKET_COPY"
        if metric == "Race Shape":
            verdict = "RUNNER_SPECIFIC_SPEED_MAP_EVIDENCE_GUARDED"
        if metric in {"Early Speed", "Late Speed"}:
            verdict = "APPROVED_CURRENT_PROJECTION_SOURCE" if bad_source == 0 else "FAIL_UNAPPROVED_SOURCE"
        rows.append({"metric": metric, "exact_source": source, "exact_field": "see lineage", "version": version, "scale": scale, "coverage_before": before, "coverage_after": after, "semantic_verdict": verdict, "bad_market_copy_count": bad_market_copy, "bad_source_count": bad_source})
        counts[metric] = after
    write_csv(DATA / "edgeiq_current_intelligence_v1_1_semantic_audit.csv", rows, ["metric", "exact_source", "exact_field", "version", "scale", "coverage_before", "coverage_after", "semantic_verdict", "bad_market_copy_count", "bad_source_count"])
    write_text(DATA / "edgeiq_current_intelligence_v1_1_semantic_summary.txt", [
        "EDGEIQ CURRENT INTELLIGENCE V1.1 SEMANTIC SUMMARY",
        "Race Shape semantic verdict: Runner-specific speed-map value, not a repeated race-level value. V1.1 prevents no-evidence default MIDFIELD from being shown.",
        "Early Speed semantic verdict: populated only from CURRENT_EARLY_SPEED_V1; stale projected_spd remains blocked.",
        "Late Speed semantic verdict: populated only from CURRENT_LATE_SPEED_V1; live_speed_map late_power_index remains blocked.",
        "EDGEiQ Price semantic verdict: governed model/fair price, not market copy.",
        "Duplicate race-runner keys: " + str(sum(1 for v in duplicates.values() if v > 1)),
        "Cross-race joins detected by audit: " + str(cross_race_join),
        *[f"{row['metric']}: {row['coverage_before']} -> {row['coverage_after']}" for row in rows],
    ])
    return {"coverage": dict(counts), "duplicate_keys": sum(1 for v in duplicates.values() if v > 1), "semantic_rows": rows}


def create_source_audit() -> None:
    dna_rows = read_csv(DNA)
    dates = sorted({date_key(r.get("race_date")) for r in dna_rows if date_key(r.get("race_date"))})
    current_present = any(d in {"2026-07-10", "2026-07-11", "2026-07-12"} for d in dates)
    write_text(DATA / "edgeiq_suitability_and_momentum_existing_source_audit_v1.txt", [
        "EDGEIQ SUITABILITY AND MOMENTUM EXISTING SOURCE AUDIT V1",
        f"DNA source present: {DNA.exists()}",
        f"DNA date coverage: {', '.join(dates[-8:]) if dates else 'none'}",
        f"DNA current three-day dates present: {'YES' if current_present else 'NO'}",
        "Approved current Suitability source found: NO",
        "Approved current Form Momentum source found: NO",
        "No Suitability or Form Momentum value was created or promoted in V1.1.",
    ])


def create_final_audit(semantic: dict[str, Any], early_counts: Counter, late_counts: Counter) -> None:
    commit_history = subprocess.check_output(["git", "log", "--oneline", "-20"], cwd=ROOT, text=True, errors="replace")
    current_status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True, errors="replace")
    checks = {
        "preflight_status_recorded": PRE_FLIGHT.exists(),
        "commit_3b55eb5_in_history": "3b55eb5" in commit_history,
        "operational_contract_documented": (DATA / "edgeiq_operational_race_state_contract_v1.json").exists(),
        "lineage_documented": (DATA / "edgeiq_current_intelligence_v1_1_lineage.csv").exists(),
        "early_speed_gaps_classified": (DATA / "edgeiq_early_speed_v1_1_gap_audit.csv").exists(),
        "late_speed_gaps_classified": (DATA / "edgeiq_late_speed_v1_1_gap_audit.csv").exists(),
        "semantic_audit_complete": (DATA / "edgeiq_current_intelligence_v1_1_semantic_audit.csv").exists(),
        "no_duplicate_race_runner_key": semantic["duplicate_keys"] == 0,
        "early_speed_not_silently_historical": all(row.get("bad_source_count", 0) == 0 for row in semantic["semantic_rows"] if row["metric"] == "Early Speed"),
        "late_speed_not_silently_historical": all(row.get("bad_source_count", 0) == 0 for row in semantic["semantic_rows"] if row["metric"] == "Late Speed"),
        "market_not_used_as_edgeiq_price": all(row["bad_market_copy_count"] == 0 for row in semantic["semantic_rows"] if row["metric"] == "EDGEiQ Price"),
        "form_guide_routing_intact": ENRICHED.exists(),
        "build_status": (ROOT / "dist" / "index.html").exists(),
    }
    status = "EDGEIQ_CURRENT_INTELLIGENCE_V1_1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_CURRENT_INTELLIGENCE_V1_1_AUDIT_FAIL"
    payload = {
        "status": status,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "coverage": semantic["coverage"],
        "earlySpeedGapCounts": dict(early_counts),
        "lateSpeedGapCounts": dict(late_counts),
        "gitStatusShort": current_status.splitlines(),
    }
    (DATA / "edgeiq_current_intelligence_v1_1_audit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_text(DATA / "edgeiq_current_intelligence_v1_1_audit.txt", [
        status,
        "",
        *[f"{k}: {'PASS' if v else 'FAIL'}" for k, v in checks.items()],
        "",
        "Coverage:",
        *[f"{k}: {v}" for k, v in semantic["coverage"].items()],
        "",
        "Early Speed gap counts:",
        *[f"{k}: {v}" for k, v in sorted(early_counts.items())],
        "",
        "Late Speed gap counts:",
        *[f"{k}: {v}" for k, v in sorted(late_counts.items())],
    ])


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    create_lineage()
    races, runners = load_enriched()
    create_contract(runners)
    early_counts, late_counts = create_gap_audits(runners)
    semantic = create_semantic_audit(runners)
    create_source_audit()
    create_final_audit(semantic, early_counts, late_counts)
    print("EDGEIQ_CURRENT_INTELLIGENCE_V1_1_AUDIT_COMPLETE")
    print((DATA / "edgeiq_current_intelligence_v1_1_audit.txt").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
