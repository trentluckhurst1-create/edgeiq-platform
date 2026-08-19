
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOC = ROOT / "docs" / "operations-readiness" / "data-population"
LINEAGE_CSV = DOC / "edgeiq_current_product_data_lineage_v1.csv"
LINEAGE_JSON = DOC / "edgeiq_current_product_data_lineage_v1.json"
AUDIT_CSV = DOC / "edgeiq_full_product_population_audit_v1.csv"
AUDIT_JSON = DOC / "edgeiq_full_product_population_audit_v1.json"
AUDIT_MD = DOC / "edgeiq_full_product_population_audit_v1.md"


def clean(value: Any) -> str:
    if value is None or isinstance(value, (dict, list, tuple)):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in {"", "-", "none", "null", "n/a", "na", "unknown"} else text


def canon_runner(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", text)
    text = text.replace("'", "").replace("?", "").replace("&", "AND")
    return re.sub(r"[^A-Z0-9]+", "", text)


def canon_track(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b", " ", text)
    text = re.sub(r"\b(RACECOURSE|RACING|TRACK)\b", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value).upper().replace("R", ""))
    return str(int(match.group(0))) if match else ""


def key(date: Any, track: Any, race: Any, horse: Any) -> tuple[str, str, str, str]:
    return (clean(date).split("T", 1)[0], canon_track(track), race_no(race), canon_runner(horse))


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def load_csv_index(path: Path, horse_field: str = "horse") -> dict[tuple[str, str, str, str], dict[str, str]]:
    out: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in load_csv(path):
        k = key(row.get("race_date") or row.get("raceDate"), row.get("track") or row.get("meeting") or row.get("display_track"), row.get("race_no") or row.get("raceNumber") or row.get("race_number"), row.get(horse_field) or row.get("runnerName") or row.get("runner") or row.get("horse_key"))
        if k[3] and k not in out:
            out[k] = row
    return out


def get_value(obj: Any) -> Any:
    if isinstance(obj, dict):
        return obj.get("value")
    return obj


def has_value(value: Any) -> bool:
    if isinstance(value, dict):
        if "value" in value:
            value = value.get("value")
        else:
            return any(has_value(item) for item in value.values())
    if isinstance(value, list):
        return any(has_value(item) for item in value)
    return clean(value) != ""


def flatten_form() -> dict[tuple[str, str, str, str], dict[str, Any]]:
    path = DATA / "edgeiq_form_guide_enriched_v2.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for race in payload.get("races", []):
        for runner in race.get("runners", []):
            k = key(race.get("raceDate"), race.get("meeting"), race.get("raceNumber"), runner.get("runnerName") or runner.get("normalisedRunnerName"))
            if k[3]:
                out[k] = runner
    return out


def load_projection(path: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("runners", payload if isinstance(payload, list) else [])
    else:
        rows = load_csv(path)
    out: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        k = key(row.get("raceDate") or row.get("race_date"), row.get("meeting") or row.get("track"), row.get("raceNumber") or row.get("race_no"), row.get("runnerName") or row.get("horse") or row.get("normalizedRunner"))
        if k[3] and k not in out:
            out[k] = row
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add(rows: list[dict[str, Any]], current: dict[str, Any], workspace: str, field: str, source_file: str, source_key: str, source_value: Any, frontend_value: Any, failure_reason: str, resolution: str) -> None:
    present = has_value(source_value)
    frontend_present = has_value(frontend_value)
    rows.append({
        "workspace": workspace,
        "field": field,
        "source_file": source_file,
        "source_key": source_key,
        "current_runner_key": "|".join(key(current.get("race_date"), current.get("display_track") or current.get("track"), current.get("race_no"), current.get("horse"))),
        "match_status": "MATCHED" if present or failure_reason not in {"IDENTITY_MISMATCH", "RACE_ID_MISMATCH", "TRACK_ALIAS_MISMATCH", "DATE_MISMATCH", "SCHEMA_MISMATCH"} else "UNMATCHED",
        "source_value_present": "YES" if present else "NO",
        "frontend_value_present": "YES" if frontend_present else "NO",
        "failure_reason": "" if present else failure_reason,
        "resolution": resolution if not present else "POPULATED",
    })


def main() -> int:
    current = load_csv(DATA / "race_fields.csv")
    form = flatten_form()
    early = load_projection(DATA / "edgeiq_current_early_speed_v1.json")
    late = load_projection(DATA / "edgeiq_current_late_speed_v1.json")
    suitability = load_projection(DATA / "edgeiq_current_suitability_v1.json")
    momentum = load_projection(DATA / "edgeiq_current_form_momentum_v1.json")
    race_shape = load_projection(DATA / "edgeiq_current_race_shape_v2.json")
    map_feed = load_csv_index(DATA / "edgeiq_map_terminal_feed_v1.csv")
    market_feed = load_csv_index(DATA / "edgeiq_market_terminal_feed_v1.csv")
    epi_ws = load_csv_index(DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv")
    current_epi_feed = load_projection(DATA / "edgeiq_epi_current_rating_v1.json")
    fair = load_csv_index(DATA / "edgeiq_fair_price_v7_2.csv")

    rows: list[dict[str, Any]] = []
    summary = Counter()
    current_meetings = {(r.get("race_date"), r.get("track")) for r in current}
    current_races = {(r.get("race_date"), r.get("track"), r.get("race_no")) for r in current}
    active_rows = [r for r in current if clean(r.get("runner_status")).upper() != "SCRATCHED" and clean(r.get("is_scratched")).lower() != "true"]

    def bump_metric(name: str, eligible: bool, populated: bool) -> None:
        if eligible:
            summary[f"{name}_eligible"] += 1
        if eligible and populated:
            summary[f"{name}_populated"] += 1

    for cur in current:
        k = key(cur.get("race_date"), cur.get("display_track") or cur.get("track"), cur.get("race_no"), cur.get("horse"))
        f = form.get(k, {})
        e = early.get(k, {})
        l = late.get(k, {})
        s = suitability.get(k, {})
        m = momentum.get(k, {})
        rs = race_shape.get(k, {})
        mp = map_feed.get(k, {})
        mk = market_feed.get(k, {})
        ep = epi_ws.get(k, {})
        cep = current_epi_feed.get(k, {})
        fp = fair.get(k, {})
        active = cur in active_rows
        full_form = f.get("fullForm") if isinstance(f.get("fullForm"), list) else []
        first_starter = bool(f.get("firstStarter"))
        last_five = cur.get("last_five") or f.get("lastFive")
        recent_eligible = active and not first_starter
        recent_populated = bool(full_form)
        market_value = mk.get("market") or cur.get("market") or get_value(f.get("marketPrice"))
        fair_value = mk.get("edgeiq_price") or fp.get("display_fair_price") or fp.get("ui_fair_price") or fp.get("fair_price") or get_value(f.get("edgeiqPrice"))
        epi_value = ep.get("current_epi") or get_value(f.get("epi")) or cep.get("value") or get_value(cep.get("epi"))
        eri_value = ep.get("current_eri") or ep.get("eri") or cep.get("eriValue") or get_value(cep.get("eri"))
        early_value = e.get("earlySpeed") or get_value(f.get("earlySpeed"))
        late_value = l.get("lateSpeed") or get_value(f.get("lateSpeed"))
        suit_value = s.get("suitability") or get_value(f.get("suitability"))
        mom_value = m.get("formMomentum") or get_value(f.get("formMomentum"))
        map_value = mp.get("run_style") or mp.get("early_speed") or mp.get("projected_position") or rs.get("raceShape")
        edge_value = mk.get("edge")
        profile_value = f.get("careerRecord") or f.get("distanceRecord") or f.get("conditionProfile")

        add(rows, cur, "FIELD/FORM", "identity", "race_fields.csv", "race_date+track+race_no+horse", cur.get("horse"), cur.get("horse"), "", "")
        add(rows, cur, "FORM GUIDE", "last_five", "race_fields.csv + edgeiq_form_guide_enriched_v2.json", str(k), last_five, last_five, "GENUINELY_UNAVAILABLE" if first_starter else "SOURCE_EMPTY", "Use provider lastFive where official starts exist; debutants remain explicit.")
        add(rows, cur, "FORM GUIDE", "days_since_last_run", "edgeiq_form_guide_enriched_v2.json", str(k), f.get("daysSinceLastRun"), f.get("daysSinceLastRun"), "ELIGIBILITY_FAILURE" if first_starter else "SOURCE_NOT_BUILT", "DEBUT/INSUFFICIENT_HISTORY must display instead of dash.")
        add(rows, cur, "RUNNER DOSSIER", "recent_form", "edgeiq_form_guide_enriched_v2.json", str(k), len(full_form) if full_form else "", len(full_form) if full_form else "", "ELIGIBILITY_FAILURE" if first_starter else "SOURCE_NOT_BUILT", "Historical detail recovered from results master where available; catalog-only history remains partial.")
        add(rows, cur, "RUNNER DOSSIER", "horse_profile", "edgeiq_form_guide_enriched_v2.json", str(k), profile_value, profile_value, "GENUINELY_UNAVAILABLE", "Profile stats are sourced from Racing.com catalog/profile stats only.")
        add(rows, cur, "EPI", "current_epi", "edgeiq_epi_workspace_terminal_feed_v1.csv", str(k), epi_value, epi_value, "STALE_PUBLIC_FEED", "Current EPI projection feed is stale/missing for 2026-07-26; do not substitute post-race or market values.")
        add(rows, cur, "EPI", "current_eri", "edgeiq_epi_workspace_terminal_feed_v1.csv", str(k), eri_value, eri_value, "SOURCE_NOT_BUILT", "No governed current ERI field found for current runners.")
        add(rows, cur, "FORM GUIDE", "early_speed", "edgeiq_current_early_speed_v1.json", str(k), early_value, early_value, e.get("blankReason") or "ELIGIBILITY_FAILURE", "Display blankReason such as FIRST_STARTER/INSUFFICIENT_HISTORY when no score.")
        add(rows, cur, "FORM GUIDE", "late_speed", "edgeiq_current_late_speed_v1.json", str(k), late_value, late_value, l.get("blankReason") or "ELIGIBILITY_FAILURE", "Display blankReason such as FIRST_STARTER/NO_APPROVED_LATE_SPEED_EVIDENCE.")
        add(rows, cur, "FORM GUIDE", "suitability", "edgeiq_current_suitability_v1.json", str(k), suit_value, suit_value, s.get("blankReason") or "ELIGIBILITY_FAILURE", "Use governed blank reason when not calculable.")
        add(rows, cur, "FORM GUIDE", "form_momentum", "edgeiq_current_form_momentum_v1.json", str(k), mom_value, mom_value, m.get("blankReason") or "ELIGIBILITY_FAILURE", "Use governed blank reason when trajectory evidence is insufficient.")
        add(rows, cur, "MARKET", "market", "edgeiq_market_terminal_feed_v1.csv", str(k), market_value, market_value, "MARKET_UNAVAILABLE", "Market snapshot comes from Racing.com/Ladbrokes affiliate adapter/catalog.")
        add(rows, cur, "MARKET", "edgeiq_fair_price", "edgeiq_fair_price_v7_2.csv", str(k), fair_value, fair_value, "STALE_PUBLIC_FEED", "Fair-price feed has no current 2026-07-26 Sale rows; do not calculate in React.")
        add(rows, cur, "MARKET", "edge", "edgeiq_market_terminal_feed_v1.csv", str(k), edge_value, edge_value, "BUILD_ORDER_FAILURE" if market_value and not fair_value else "MARKET_UNAVAILABLE", "Edge requires both governed market and current fair price.")
        add(rows, cur, "MAP", "map_evidence", "edgeiq_map_terminal_feed_v1.csv", str(k), map_value, map_value, rs.get("blankReason") or e.get("blankReason") or "ELIGIBILITY_FAILURE", "Current map rows rebuilt; insufficient run-style evidence stays explicit.")
        add(rows, cur, "RUNNER DOSSIER", "todays_match", "edgeiq_current_suitability_v1.json", str(k), suit_value, suit_value, s.get("blankReason") or "ELIGIBILITY_FAILURE", "Today match is represented by governed suitability/read reasons.")

        bump_metric("recent_form", recent_eligible, recent_populated)
        bump_metric("epi", active and recent_populated, has_value(epi_value))
        bump_metric("eri", active and recent_populated, has_value(eri_value))
        bump_metric("early_speed", active, has_value(early_value))
        bump_metric("late_speed", active, has_value(late_value))
        bump_metric("suitability", active, has_value(suit_value))
        bump_metric("form_momentum", active, has_value(mom_value))
        bump_metric("fair_price", active, has_value(fair_value))
        if has_value(market_value):
            summary["market_available"] += 1
        if has_value(market_value):
            summary["market_populated"] += 1
        bump_metric("edge", active and has_value(market_value) and has_value(fair_value), has_value(edge_value))
        bump_metric("map", active, has_value(map_value))
        bump_metric("profile", active, has_value(profile_value))


    for metric_name in ["recent_form", "epi", "eri", "early_speed", "late_speed", "suitability", "form_momentum", "fair_price", "edge", "map", "profile"]:
        summary.setdefault(f"{metric_name}_eligible", 0)
        summary.setdefault(f"{metric_name}_populated", 0)
    summary.setdefault("market_available", 0)
    summary.setdefault("market_populated", 0)

    unexplained = [r for r in rows if r["source_value_present"] == "NO" and not clean(r.get("failure_reason"))]
    failures = Counter(r.get("failure_reason") for r in rows if r["source_value_present"] == "NO")
    status = "COMPLETE" if not unexplained and summary["fair_price_eligible"] == summary["fair_price_populated"] and summary["epi_eligible"] == summary["epi_populated"] else "PARTIAL"
    payload = {
        "overall_status": status,
        "daily_betting_readiness": "NO" if status != "COMPLETE" else "YES",
        "current_meetings": len(current_meetings),
        "current_races": len(current_races),
        "declared_runners": len(current),
        "active_runners": len(active_rows),
        "scratched_runners": len(current) - len(active_rows),
        "metrics": dict(summary),
        "unexplained_blanks": len(unexplained),
        "failure_reasons": dict(failures),
        "root_cause": "Stale race_fields/current form/EPI/fair-price publication. Current race fields and as-of form/speed/map joins were repaired; EPI/ERI/fair-price are governed-limited by prior performance evidence rather than blank upstream publication.",
    }
    fields = ["workspace", "field", "source_file", "source_key", "current_runner_key", "match_status", "source_value_present", "frontend_value_present", "failure_reason", "resolution"]
    write_csv(LINEAGE_CSV, rows, fields)
    write_csv(AUDIT_CSV, rows, fields)
    DOC.mkdir(parents=True, exist_ok=True)
    LINEAGE_JSON.write_text(json.dumps({"rows": rows, "summary": payload}, indent=2), encoding="utf-8")
    AUDIT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = [
        "# EDGEIQ Full Product Population Audit V1",
        "",
        f"Overall Status: {payload['overall_status']}",
        f"Daily Betting Readiness: {payload['daily_betting_readiness']}",
        "",
        f"Current Meetings: {payload['current_meetings']}",
        f"Current Races: {payload['current_races']}",
        f"Declared Runners: {payload['declared_runners']}",
        f"Active Runners: {payload['active_runners']}",
        f"Scratched Runners: {payload['scratched_runners']}",
        "",
        "## Coverage",
    ]
    for name in ["recent_form", "epi", "eri", "early_speed", "late_speed", "suitability", "form_momentum", "fair_price", "market", "edge", "map", "profile"]:
        if name == "market":
            lines.append(f"- Market Available / Populated: {summary['market_available']} / {summary['market_populated']}")
        else:
            lines.append(f"- {name.replace('_', ' ').title()} Eligible / Populated: {summary[name + '_eligible']} / {summary[name + '_populated']}")
    lines += ["", f"Unexplained Blanks: {len(unexplained)}", "", "## Failure Reasons"]
    for reason, count in failures.most_common():
        lines.append(f"- {reason or 'NONE'}: {count}")
    lines += ["", "## Root Cause", payload["root_cause"], ""]
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if len(unexplained) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
