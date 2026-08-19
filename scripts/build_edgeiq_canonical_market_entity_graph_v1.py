from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "sectional_edge": DATA / "edgeiq_sectional_edge_detection_v1.csv",
    "trusted_sectional_v2": DATA / "edgeiq_trusted_sectional_universe_v2.csv",
    "shadow_validation": DATA / "edgeiq_shadow_validation_engine_v1.csv",
    "sectional_feature": DATA / "edgeiq_sectional_feature_engine_v1.csv",
    "archetype_cluster": DATA / "edgeiq_sectional_archetype_cluster_v1.csv",
    "race_shape_response": DATA / "edgeiq_race_shape_response_v1.csv",
    "sportsbet_live_market": DATA / "sportsbet_live_market_v1.csv",
    "execution_engine_v4": DATA / "edgeiq_execution_engine_v4.csv",
    "live_runner_board": DATA / "edgeiq_live_runner_board_v1.csv",
    "execution_board_live": DATA / "edgeiq_execution_board_live.csv",
    "execution_board_terminal": DATA / "edgeiq_execution_board_terminal.csv",
    "market_truth": DATA / "edgeiq_market_truth_engine_v3.csv",
    "race_results": DATA / "race_results.csv",
    "three_day_fields": DATA / "edgeiq_vic_three_day_race_fields.csv",
    "three_day_universe": DATA / "edgeiq_vic_three_day_meeting_universe.csv",
}

GRAPH_OUT = DATA / "edgeiq_canonical_market_entity_graph_v1.csv"
CONFLICT_OUT = DATA / "edgeiq_market_entity_conflicts_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_market_entity_resolution_summary_v1.csv"

GRAPH_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "canonical_runner_key",
    "sectional_runner",
    "market_runner",
    "execution_runner",
    "results_runner",
    "sportsbook_runner",
    "sectional_source_present",
    "market_source_present",
    "execution_source_present",
    "results_source_present",
    "market_price",
    "rated_price",
    "entity_match_score",
    "entity_match_confidence",
    "entity_resolution_status",
    "match_method",
    "conflict_flag",
    "conflict_reason",
    "trusted_market_link",
    "safe_for_market_comparison",
    "safe_for_execution",
    "notes",
]

CONFLICT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "candidate_count",
    "conflict_type",
    "conflict_reason",
    "candidate_sources",
    "recommended_resolution",
]

SUMMARY_FIELDS = ["metric", "value"]

TRACK_ALIASES = {
    "CAULFIELDHEATH": "CAULFIELD HEATH",
    "CAULFIELD": "CAULFIELD",
    "FLEMINGTON": "FLEMINGTON",
    "THEVALLEY": "MOONEE VALLEY",
    "MOONEEVALLEY": "MOONEE VALLEY",
    "SANDOWN": "SANDOWN",
    "SANDOWNHILLSIDE": "SANDOWN",
    "SANDOWNLAKESIDE": "SANDOWN",
    "LADBROKESPARK": "SANDOWN",
    "PAKENHAM": "PAKENHAM",
    "SPORTSBETPAKENHAM": "PAKENHAM",
    "PAKENHAMSYNTHETIC": "PAKENHAM",
    "CRANBOURNE": "CRANBOURNE",
    "BALLARAT": "BALLARAT",
    "BENDIGO": "BENDIGO",
    "GEELONG": "GEELONG",
    "BET365GEELONG": "GEELONG",
    "SEYMOUR": "SEYMOUR",
    "WARRNAMBOOL": "WARRNAMBOOL",
    "SALE": "SALE",
    "MORNINGTON": "MORNINGTON",
    "HORSHAM": "HORSHAM",
    "STAWELL": "STAWELL",
    "WANGARATTA": "WANGARATTA",
    "WODONGA": "WODONGA",
    "KYNETON": "KYNETON",
    "KILMORE": "KILMORE",
    "COLAC": "COLAC",
    "TERANG": "TERANG",
    "ARARAT": "ARARAT",
    "CAMPERDOWN": "CAMPERDOWN",
    "CASTERTON": "CASTERTON",
    "DONALD": "DONALD",
    "ECHUCA": "ECHUCA",
    "HAMILTON": "HAMILTON",
    "HEALESVILLE": "HEALESVILLE",
    "KERANG": "KERANG",
    "MILDURA": "MILDURA",
    "MOE": "MOE",
    "MURTOA": "MURTOA",
    "SWANHILL": "SWAN HILL",
    "TATURA": "TATURA",
    "WERRIBEE": "WERRIBEE",
    "YARRAVALLEY": "YARRA VALLEY",
}


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else text


def ascii_text(value: object) -> str:
    return unicodedata.normalize("NFKD", clean(value)).encode("ascii", "ignore").decode("ascii")


def normalised_horse(value: object) -> str:
    text = ascii_text(value).upper()
    text = text.replace("'", "").replace("`", "").replace("’", "").replace("‘", "")
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\b(NZ|AUS|GB|IRE|USA|FR|JPN|SAF|GER)\b", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def normalised_track(value: object) -> str:
    text = ascii_text(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|MRC|VRC|RACING|CLUB)\b", " ", text)
    key = re.sub(r"[^A-Z0-9]", "", text)
    return TRACK_ALIASES.get(key, " ".join(re.sub(r"[^A-Z0-9]+", " ", text).split()))


def normalised_race_date(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    return text[:10]


def normalised_race_no(value: object) -> str:
    text = clean(value).upper().replace("RACE", "").replace("R", "")
    digits = re.sub(r"[^0-9]", "", text)
    return str(int(digits)) if digits else ""


def canonical_race_key(row: dict[str, str]) -> str:
    date = normalised_race_date(first(row, ["race_date", "date", "meeting_date", "run_date"]))
    track = normalised_track(first(row, ["track", "venue", "meeting"]))
    race_no = normalised_race_no(first(row, ["race_no", "race_number", "race"]))
    return "|".join([date, track, race_no]) if date and track and race_no else ""


def canonical_runner_key(row: dict[str, str]) -> str:
    race_key = canonical_race_key(row)
    horse = normalised_horse(first(row, ["horse_key", "horse", "runner", "runner_name", "horse_name", "sectional_runner"]))
    return f"{race_key}|{horse}" if race_key and horse else ""


def first(row: dict[str, str] | None, names: list[str]) -> str:
    if row is None:
        return ""
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


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


def price_value(value: object) -> str:
    raw = clean(value)
    if not raw:
        return ""
    try:
        parsed = float(raw.replace("$", "").replace(",", ""))
    except ValueError:
        return ""
    return f"{parsed:.2f}".rstrip("0").rstrip(".") if parsed > 0 else ""


def source_price(row: dict[str, str]) -> str:
    for name in [
        "market_price",
        "live_price",
        "sportsbet_price",
        "fixed_win",
        "ui_price",
        "price",
        "win_price",
        "odds",
    ]:
        value = price_value(row.get(name))
        if value:
            return value
    return ""


def rated_price(row: dict[str, str]) -> str:
    for name in ["rated_price", "fair_price", "ui_fair_price", "model_price", "sectional_fair_price"]:
        value = price_value(row.get(name))
        if value:
            return value
    return ""


def make_row(source: str, row: dict[str, str]) -> dict[str, str]:
    out = dict(row)
    out["_source"] = source
    out["_race_date"] = normalised_race_date(first(row, ["race_date", "date", "meeting_date", "run_date"]))
    out["_track"] = normalised_track(first(row, ["track", "venue", "meeting"]))
    out["_race_no"] = normalised_race_no(first(row, ["race_no", "race_number", "race"]))
    out["_horse"] = first(row, ["horse", "runner", "runner_name", "horse_name", "sectional_runner", "horse_key"])
    out["_horse_key"] = normalised_horse(out["_horse"])
    out["_race_key"] = "|".join([out["_race_date"], out["_track"], out["_race_no"]]) if out["_race_date"] and out["_track"] and out["_race_no"] else ""
    out["_runner_key"] = f"{out['_race_key']}|{out['_horse_key']}" if out["_race_key"] and out["_horse_key"] else ""
    out["_price"] = source_price(row)
    out["_rated_price"] = rated_price(row)
    return out


def load_source(source: str, path: Path) -> list[dict[str, str]]:
    return [make_row(source, row) for row in read_csv(path)]


def has_price(row: dict[str, str] | None) -> bool:
    return bool(row and clean(row.get("_price")))


def confidence_label(score: int) -> str:
    if score >= 85:
        return "HIGH"
    if score >= 70:
        return "MEDIUM"
    if score >= 50:
        return "LOW"
    return "UNSAFE"


def field_row_key(row: dict[str, str]) -> str:
    return clean(row.get("_runner_key"))


def index_rows(rows: list[dict[str, str]]) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    by_runner: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_race_horse: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_horse: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if clean(row.get("_runner_key")):
            by_runner[row["_runner_key"]].append(row)
        race_horse = f"{row.get('_race_key')}|{row.get('_horse_key')}" if row.get("_race_key") and row.get("_horse_key") else ""
        if race_horse:
            by_race_horse[race_horse].append(row)
        if row.get("_horse_key"):
            by_horse[row["_horse_key"]].append(row)
    return by_runner, by_race_horse, by_horse


def candidate_market_rows(base: dict[str, str], market_rows: list[dict[str, str]], by_runner: dict[str, list[dict[str, str]]], by_race_horse: dict[str, list[dict[str, str]]], by_horse: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    candidates: dict[int, dict[str, str]] = {}
    for row in by_runner.get(base["_runner_key"], []):
        candidates[id(row)] = row
    for row in by_race_horse.get(f"{base.get('_race_key')}|{base.get('_horse_key')}", []):
        candidates[id(row)] = row
    for row in by_horse.get(base.get("_horse_key", ""), []):
        same_meeting = row.get("_race_date") == base.get("_race_date") and row.get("_track") == base.get("_track")
        same_race = row.get("_race_key") == base.get("_race_key")
        if same_race or same_meeting:
            candidates[id(row)] = row
    return list(candidates.values())


def duplicate_market_count(candidates: list[dict[str, str]]) -> int:
    priced = [row for row in candidates if has_price(row)]
    if len(priced) > 1:
        prices = {row["_price"] for row in priced}
        if len(prices) > 1:
            return len(priced)
    return 0


def choose_market_candidate(candidates: list[dict[str, str]]) -> dict[str, str] | None:
    if not candidates:
        return None
    priced = [row for row in candidates if has_price(row)]
    pool = priced or candidates
    priority = {
        "three_day_universe": 100,
        "three_day_fields": 98,
        "execution_engine_v4": 90,
        "sportsbet_live_market": 86,
        "market_truth": 82,
        "live_runner_board": 78,
        "execution_board_live": 74,
        "execution_board_terminal": 70,
    }
    return sorted(pool, key=lambda row: (priority.get(row["_source"], 0), 1 if has_price(row) else 0), reverse=True)[0]


def score_link(base: dict[str, str], market: dict[str, str] | None, execution: dict[str, str] | None, results: dict[str, str] | None, field: dict[str, str] | None, sectional_present: bool, candidate_count: int, conflict: bool) -> tuple[int, str, list[str]]:
    notes: list[str] = []
    score = 0
    exact_race = bool(market and market.get("_race_key") and market.get("_race_key") == base.get("_race_key"))
    exact_horse = bool(market and market.get("_horse_key") and market.get("_horse_key") == base.get("_horse_key"))
    if exact_race:
        score += 35
    if exact_horse:
        score += 30
    if market and has_price(market):
        score += 15
    if execution:
        score += 10
    if field:
        score += 10
    if sectional_present:
        score += 10
    if candidate_count > 1:
        score -= 40
        notes.append("duplicate market candidates")
    if not base.get("_race_key") or not (market and market.get("_race_key")):
        score -= 30
        notes.append("missing race key")
    if not base.get("_horse_key") or not (market and market.get("_horse_key")):
        score -= 25
        notes.append("missing horse")
    if not (market and has_price(market)):
        score -= 20
        notes.append("no market price")
    if conflict:
        score -= 50
        notes.append("conflicting candidates")
    score = max(0, min(100, score))
    if conflict:
        status = "CONFLICT_MARKET_LINK"
    elif market and not has_price(market):
        status = "NO_MARKET_PRICE"
    elif not market:
        status = "NO_MARKET_LINK"
    elif score >= 85 and exact_race and exact_horse and has_price(market):
        status = "TRUSTED_MARKET_LINK"
    elif score >= 70:
        status = "LIKELY_MARKET_LINK"
    elif candidate_count > 1:
        status = "AMBIGUOUS_MARKET_LINK"
    else:
        status = "NO_MARKET_LINK"
    return score, status, notes


def graph_base_rows() -> tuple[list[dict[str, str]], dict[str, int]]:
    source_order = [
        "sectional_edge",
        "trusted_sectional_v2",
        "shadow_validation",
        "sectional_feature",
        "archetype_cluster",
        "race_shape_response",
    ]
    rows: dict[str, dict[str, str]] = {}
    counts: dict[str, int] = {}
    for source in source_order:
        loaded = load_source(source, INPUTS[source])
        counts[source] = len(loaded)
        for row in loaded:
            key = clean(row.get("_runner_key"))
            if not key:
                key = "|".join([row.get("_race_date", ""), row.get("_track", ""), row.get("_race_no", ""), row.get("_horse_key", "")])
            if key and key not in rows:
                rows[key] = row
    return list(rows.values()), counts


def main() -> None:
    missing = [path.name for path in INPUTS.values() if not path.exists()]
    base_rows, sectional_counts = graph_base_rows()
    market_sources = [
        "three_day_universe",
        "three_day_fields",
        "sportsbet_live_market",
        "execution_engine_v4",
        "live_runner_board",
        "execution_board_live",
        "execution_board_terminal",
        "market_truth",
    ]
    market_rows: list[dict[str, str]] = []
    source_counts: dict[str, int] = dict(sectional_counts)
    for source in market_sources:
        rows = load_source(source, INPUTS[source])
        market_rows.extend(rows)
        source_counts[source] = len(rows)
    result_rows = load_source("race_results", INPUTS["race_results"])
    source_counts["race_results"] = len(result_rows)
    field_rows = load_source("three_day_universe", INPUTS["three_day_universe"]) + load_source("three_day_fields", INPUTS["three_day_fields"])
    execution_rows = load_source("execution_engine_v4", INPUTS["execution_engine_v4"]) + load_source("execution_board_live", INPUTS["execution_board_live"]) + load_source("execution_board_terminal", INPUTS["execution_board_terminal"])

    market_by_runner, market_by_race_horse, market_by_horse = index_rows(market_rows)
    execution_by_runner, _, _ = index_rows(execution_rows)
    results_by_runner, _, _ = index_rows(result_rows)
    field_by_runner, _, _ = index_rows(field_rows)

    graph: list[dict[str, object]] = []
    conflicts: list[dict[str, object]] = []
    for base in base_rows:
        candidates = candidate_market_rows(base, market_rows, market_by_runner, market_by_race_horse, market_by_horse)
        duplicate_count = duplicate_market_count(candidates)
        market = choose_market_candidate(candidates)
        execution = next(iter(execution_by_runner.get(base.get("_runner_key", ""), [])), None)
        results = next(iter(results_by_runner.get(base.get("_runner_key", ""), [])), None)
        field = next(iter(field_by_runner.get(base.get("_runner_key", ""), [])), None)
        conflict = duplicate_count > 1
        score, status, notes = score_link(base, market, execution, results, field, True, duplicate_count, conflict)
        match_method = "EXACT_RACE_HORSE" if market and market.get("_race_key") == base.get("_race_key") and market.get("_horse_key") == base.get("_horse_key") else "DATE_TRACK_HORSE_REVIEW" if market and market.get("_race_date") == base.get("_race_date") and market.get("_track") == base.get("_track") and market.get("_horse_key") == base.get("_horse_key") else "NO_SAFE_MATCH"
        trusted = "YES" if status == "TRUSTED_MARKET_LINK" and not conflict else "NO"
        graph.append({
            "race_date": base.get("_race_date", ""),
            "track": base.get("_track", ""),
            "race_no": base.get("_race_no", ""),
            "horse": base.get("_horse", ""),
            "canonical_runner_key": base.get("_runner_key", ""),
            "sectional_runner": first(base, ["sectional_runner", "horse", "runner", "horse_name"]) or base.get("_horse", ""),
            "market_runner": first(market, ["horse", "runner", "horse_name", "horse_key"]) if market else "",
            "execution_runner": first(execution, ["horse", "runner", "horse_name", "horse_key"]) if execution else "",
            "results_runner": first(results, ["horse", "runner", "horse_name", "horse_key"]) if results else "",
            "sportsbook_runner": first(market, ["horse", "runner", "horse_name", "horse_key"]) if market and market.get("_source") == "sportsbet_live_market" else "",
            "sectional_source_present": "YES",
            "market_source_present": "YES" if market else "NO",
            "execution_source_present": "YES" if execution else "NO",
            "results_source_present": "YES" if results else "NO",
            "market_price": market.get("_price", "") if market else "",
            "rated_price": first(market, ["_rated_price"]) or first(base, ["rated_price", "fair_price", "ui_fair_price"]) or first(execution, ["fair_price", "rated_price"]) if market or execution else first(base, ["rated_price", "fair_price", "ui_fair_price"]),
            "entity_match_score": score,
            "entity_match_confidence": confidence_label(score),
            "entity_resolution_status": status,
            "match_method": match_method,
            "conflict_flag": "YES" if conflict else "NO",
            "conflict_reason": "; ".join(notes),
            "trusted_market_link": trusted,
            "safe_for_market_comparison": "YES" if trusted == "YES" else "NO",
            "safe_for_execution": "NO",
            "notes": "Canonical market graph only. No execution impact.",
        })
        if conflict:
            conflicts.append({
                "race_date": base.get("_race_date", ""),
                "track": base.get("_track", ""),
                "race_no": base.get("_race_no", ""),
                "horse": base.get("_horse", ""),
                "candidate_count": duplicate_count,
                "conflict_type": "DUPLICATE_MARKET_CANDIDATES",
                "conflict_reason": "; ".join(notes),
                "candidate_sources": "|".join(sorted({row.get("_source", "") for row in candidates if has_price(row)})),
                "recommended_resolution": "Keep out of market comparison until one canonical market source is selected.",
            })

    status_counts = Counter(str(row["entity_resolution_status"]) for row in graph)
    summary = [
        {"metric": "rows", "value": len(graph)},
        {"metric": "trusted_market_links", "value": status_counts.get("TRUSTED_MARKET_LINK", 0)},
        {"metric": "likely_market_links", "value": status_counts.get("LIKELY_MARKET_LINK", 0)},
        {"metric": "ambiguous_market_links", "value": status_counts.get("AMBIGUOUS_MARKET_LINK", 0)},
        {"metric": "no_market_links", "value": status_counts.get("NO_MARKET_LINK", 0)},
        {"metric": "conflict_market_links", "value": status_counts.get("CONFLICT_MARKET_LINK", 0)},
        {"metric": "no_market_price", "value": status_counts.get("NO_MARKET_PRICE", 0)},
        {"metric": "safe_for_market_comparison_yes", "value": sum(1 for row in graph if row["safe_for_market_comparison"] == "YES")},
        {"metric": "safe_for_execution_yes", "value": sum(1 for row in graph if row["safe_for_execution"] == "YES")},
    ]
    summary.extend({"metric": f"missing_input::{name}", "value": "YES"} for name in missing)
    summary.extend({"metric": f"source_rows::{source}", "value": count} for source, count in sorted(source_counts.items()))
    write_csv(GRAPH_OUT, graph, GRAPH_FIELDS)
    write_csv(CONFLICT_OUT, conflicts, CONFLICT_FIELDS)
    write_csv(SUMMARY_OUT, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ CANONICAL MARKET ENTITY GRAPH V1")
    print("=" * 90)
    print("ROWS:", len(graph))
    print("TRUSTED MARKET LINKS:", status_counts.get("TRUSTED_MARKET_LINK", 0))
    print("NO MARKET PRICE:", status_counts.get("NO_MARKET_PRICE", 0))
    print("CONFLICTS:", len(conflicts))
    print("OUT:", GRAPH_OUT)


if __name__ == "__main__":
    main()
