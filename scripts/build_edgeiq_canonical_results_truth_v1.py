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
REBUILD_OUTPUTS = ROOT.parents[1] / "edgeiq_rebuild" / "outputs"

SOURCES = [
    DATA / "edgeiq_ra_historical_results_harvest_v1.csv",
    DATA / "edgeiq_official_results_backfill_v1.csv",
    DATA / "race_results.csv",
    DATA / "edgeiq_results_master.csv",
    DATA / "edgeiq_results_truth_loop.csv",
    DATA / "edgeiq_results_auto_settlement.csv",
    DATA / "edgeiq_execution_accountability.csv",
    DATA / "edgeiq_execution_engine_v4.csv",
    DATA / "edgeiq_canonical_market_entity_graph_v1.csv",
    DATA / "edgeiq_vic_three_day_race_fields.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
    DATA / "model_result_review.csv",
    DATA / "race_card_report.csv",
    REBUILD_OUTPUTS / "edgeiq_results_master.csv",
    REBUILD_OUTPUTS / "edgeiq_results_summary.csv",
    REBUILD_OUTPUTS / "edgeiq_results_by_regime.csv",
    REBUILD_OUTPUTS / "edgeiq_results_by_confidence.csv",
    DATA / "results_history_clean.csv",
    DATA / "master_result_events.csv",
    DATA / "ra_calendar_official_results.csv",
]

OUT = DATA / "edgeiq_canonical_results_truth_v1.csv"
SUMMARY = DATA / "edgeiq_canonical_results_truth_summary_v1.csv"
CONFLICTS = DATA / "edgeiq_results_truth_conflicts_v1.csv"

OUT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "canonical_runner_key",
    "finish_position",
    "winner_flag",
    "place_flag",
    "top4_flag",
    "result_status",
    "result_source",
    "result_confidence",
    "result_resolution_status",
    "conflict_flag",
    "conflict_reason",
    "safe_for_model_validation",
    "safe_for_execution_settlement",
    "notes",
]

CONFLICT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "canonical_runner_key",
    "candidate_count",
    "finish_positions_seen",
    "sources_seen",
    "conflict_reason",
    "recommended_resolution",
]

SUMMARY_FIELDS = ["metric", "value"]

VICTORIAN_TRACK_ALIASES = {
    "BET365 YARRA VALLEY": "YARRA VALLEY",
    "YARRA VALLEY": "YARRA VALLEY",
    "SPORTSBET WANGARATTA": "WANGARATTA",
    "WANGARATTA": "WANGARATTA",
    "SOUTHSIDE PAKENHAM": "PAKENHAM",
    "PAKENHAM": "PAKENHAM",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "CAULFIELD HEATH": "CAULFIELD HEATH",
    "CAULFIELD": "CAULFIELD",
    "FLEMINGTON": "FLEMINGTON",
    "MOONEE VALLEY": "MOONEE VALLEY",
    "THE VALLEY": "MOONEE VALLEY",
    "SANDOWN": "SANDOWN",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
    "CRANBOURNE": "CRANBOURNE",
    "BALLARAT": "BALLARAT",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "BENDIGO": "BENDIGO",
    "GEELONG": "GEELONG",
    "GEELONG SYNTHETIC": "GEELONG",
    "SEYMOUR": "SEYMOUR",
    "WARRNAMBOOL": "WARRNAMBOOL",
    "SALE": "SALE",
    "MORNINGTON": "MORNINGTON",
    "HORSHAM": "HORSHAM",
    "STAWELL": "STAWELL",
    "ARARAT": "ARARAT",
    "CAMPERDOWN": "CAMPERDOWN",
    "COLAC": "COLAC",
    "DONALD": "DONALD",
    "EDENHOPE": "EDENHOPE",
    "HAMILTON": "HAMILTON",
    "KYNETON": "KYNETON",
    "MILDURA": "MILDURA",
    "MOE": "MOE",
    "MURTOA": "MURTOA",
    "TERANG": "TERANG",
    "WERRIBEE": "WERRIBEE",
    "WODONGA": "WODONGA",
}

FINISH_FIELDS = [
    "finish_position",
    "position",
    "place",
    "placing",
    "result",
    "finishing_position",
    "finish",
    "rank",
    "fin_pos",
    "official_position",
    "settled_position",
    "finish_pos",
    "finish_pos_num",
    "finish",
]

HORSE_FIELDS = ["horse", "horse_name", "runner", "runner_name", "market_runner", "execution_runner", "results_runner", "sportsbook_runner"]
DATE_FIELDS = ["race_date", "date", "date_k", "meeting_date"]
TRACK_FIELDS = ["track", "track_name", "meeting", "track_key", "track_k"]
RACE_NO_FIELDS = ["race_no", "race_number", "race_k"]

SOURCE_PRIORITY = {
    "edgeiq_ra_historical_results_harvest_v1.csv": 120,
    "edgeiq_official_results_backfill_v1.csv": 110,
    "ra_calendar_official_results.csv": 100,
    "results_history_clean.csv": 95,
    "master_result_events.csv": 92,
    "model_result_review.csv": 80,
    "edgeiq_results_truth_loop.csv": 76,
    "edgeiq_results_auto_settlement.csv": 74,
    "race_results.csv": 70,
    "edgeiq_results_master.csv": 64,
    "race_card_report.csv": 30,
    "edgeiq_canonical_market_entity_graph_v1.csv": 25,
    "edgeiq_vic_three_day_race_fields.csv": 20,
    "edgeiq_vic_three_day_meeting_universe.csv": 20,
    "edgeiq_execution_engine_v4.csv": 15,
}

SETTLEMENT_SOURCES = {"edgeiq_results_truth_loop.csv", "edgeiq_results_auto_settlement.csv", "edgeiq_results_master.csv"}


def clean(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def first_value(row: dict[str, str], fields: list[str]) -> str:
    for field in fields:
        value = clean(row.get(field))
        if value:
            return value
    return ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def normalise_text(value: object) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("&", " AND ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"['`â€™â€˜]", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def horse_key(value: object) -> str:
    return normalise_text(value)


def normalise_track(value: object) -> str:
    track = normalise_text(value)
    track = re.sub(r"\bRACING\b", "", track)
    track = re.sub(r"\bCLUB\b", "", track)
    track = re.sub(r"\s+", " ", track).strip()
    return VICTORIAN_TRACK_ALIASES.get(track, track)


def normalise_race_no(value: object) -> str:
    text = clean(value).upper()
    match = re.search(r"\d+", text)
    if not match:
        return ""
    return str(int(match.group(0)))


def normalise_date(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    text = text.replace("/", "-")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return text[:10]


def canonical_runner_key(race_date: str, track: str, race_no: str, horse: str) -> str:
    if not race_date or not track or not race_no or not horse:
        return ""
    return f"{race_date}|{track}|{race_no}|{horse_key(horse)}"


def extract_finish(row: dict[str, str]) -> tuple[str, str]:
    status_text = " ".join(clean(row.get(field)) for field in ["result_status", "status", "result", "finish", "finish_pos"])
    status_norm = normalise_text(status_text)
    if any(token in status_norm.split() for token in ["SCR", "SCRATCHED", "SCRATCHING"]):
        return "", "SCRATCHED"

    for field in FINISH_FIELDS:
        raw = clean(row.get(field))
        if not raw:
            continue
        norm = normalise_text(raw)
        if any(token in norm.split() for token in ["SCR", "SCRATCHED", "SCRATCHING"]):
            return "", "SCRATCHED"
        if norm in {"WON", "WINNER", "WIN"}:
            return "1", "RESULTED"
        if norm in {"LOST", "LOSS", "PENDING", "OPEN", "NO RESULT"}:
            continue
        match = re.search(r"\d+", raw)
        if match:
            position = int(match.group(0))
            if 0 < position < 40:
                return str(position), "RESULTED"

    explicit = normalise_text(first_value(row, ["result_status", "status"]))
    if explicit in {"SCR", "SCRATCHED", "SCRATCHING"}:
        return "", "SCRATCHED"
    return "", "PENDING_OR_NO_POSITION"


def flags(finish_position: str) -> tuple[str, str, str]:
    if not finish_position:
        return "", "", ""
    position = int(finish_position)
    return (
        "YES" if position == 1 else "NO",
        "YES" if position <= 3 else "NO",
        "YES" if position <= 4 else "NO",
    )


def confidence_for(source: str, finish_position: str, result_status: str, row: dict[str, str]) -> int:
    score = SOURCE_PRIORITY.get(source, 40)
    if finish_position:
        score += 10
    if result_status == "SCRATCHED":
        score += 6
    identity_score = clean(row.get("result_identity_score"))
    if identity_score:
        try:
            score += min(8, max(0, int(float(identity_score)) - 90))
        except ValueError:
            pass
    confidence_text = normalise_text(row.get("result_identity_confidence"))
    if confidence_text == "HIGH":
        score += 5
    elif confidence_text in {"LOW", "WEAK"}:
        score -= 10
    return max(0, min(100, score))


def candidate_from_row(row: dict[str, str], source_name: str) -> dict[str, object] | None:
    race_date = normalise_date(first_value(row, DATE_FIELDS))
    track = normalise_track(first_value(row, TRACK_FIELDS))
    race_no = normalise_race_no(first_value(row, RACE_NO_FIELDS))
    horse = first_value(row, HORSE_FIELDS)
    key = clean(row.get("canonical_runner_key"))

    if key and not all([race_date, track, race_no, horse]):
        pieces = key.split("|")
        if len(pieces) == 4:
            race_date = race_date or pieces[0]
            track = track or pieces[1]
            race_no = race_no or pieces[2]
            horse = horse or pieces[3]

    key = canonical_runner_key(race_date, track, race_no, horse)
    if not key:
        return None

    finish_position, result_status = extract_finish(row)
    if result_status == "PENDING_OR_NO_POSITION" and normalise_text(row.get("result_status")) in {"PENDING", "OPEN"}:
        result_status = "PENDING_OR_NO_POSITION"

    return {
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "horse": horse,
        "canonical_runner_key": key,
        "finish_position": finish_position,
        "result_status": result_status,
        "result_source": source_name,
        "result_confidence": confidence_for(source_name, finish_position, result_status, row),
        "raw_row": row,
    }


def collect_candidates() -> tuple[dict[str, list[dict[str, object]]], Counter, list[str]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    source_counts: Counter = Counter()
    missing: list[str] = []

    for path in SOURCES:
        if not path.exists():
            missing.append(path.name)
            continue
        rows = read_csv(path)
        source_counts[path.name] += len(rows)
        for row in rows:
            candidate = candidate_from_row(row, path.name)
            if candidate:
                grouped[str(candidate["canonical_runner_key"])].append(candidate)

    return grouped, source_counts, missing


def resolve_group(key: str, candidates: list[dict[str, object]]) -> tuple[dict[str, object], dict[str, object] | None]:
    finished = [candidate for candidate in candidates if candidate.get("finish_position")]
    scratched = [candidate for candidate in candidates if candidate.get("result_status") == "SCRATCHED"]
    finish_positions = sorted({str(candidate.get("finish_position")) for candidate in finished if candidate.get("finish_position")}, key=lambda x: int(x))
    sources = sorted({str(candidate.get("result_source")) for candidate in candidates})

    best = sorted(
        candidates,
        key=lambda candidate: (
            1 if candidate.get("finish_position") else 0,
            1 if candidate.get("result_status") == "SCRATCHED" else 0,
            int(candidate.get("result_confidence") or 0),
            SOURCE_PRIORITY.get(str(candidate.get("result_source")), 0),
        ),
        reverse=True,
    )[0]

    conflict = len(finish_positions) > 1
    no_result_row = not finished and not scratched and all(candidate.get("result_status") == "PENDING_OR_NO_POSITION" for candidate in candidates)

    if conflict:
        resolution_status = "CONFLICT_RESULT"
        conflict_flag = "YES"
        conflict_reason = f"Conflicting finish positions for canonical runner: {', '.join(finish_positions)}"
        safe_model = "NO"
    elif best.get("finish_position") or best.get("result_status") == "SCRATCHED":
        resolution_status = "TRUSTED_RESULT"
        conflict_flag = "NO"
        conflict_reason = ""
        safe_model = "YES" if best.get("finish_position") else "NO"
    elif no_result_row:
        resolution_status = "NO_RESULT_ROW"
        conflict_flag = "NO"
        conflict_reason = ""
        safe_model = "NO"
    else:
        resolution_status = "NO_POSITION"
        conflict_flag = "NO"
        conflict_reason = ""
        safe_model = "NO"

    settlement_safe = "NO"
    if (
        resolution_status == "TRUSTED_RESULT"
        and best.get("finish_position")
        and str(best.get("result_source")) in SETTLEMENT_SOURCES
        and normalise_text(best.get("raw_row", {}).get("result_status")) in {"SETTLED", "RESULTED", "FINAL", "CLOSED"}
    ):
        settlement_safe = "YES"

    winner, place, top4 = flags(str(best.get("finish_position") or ""))
    output = {
        "race_date": best.get("race_date", ""),
        "track": best.get("track", ""),
        "race_no": best.get("race_no", ""),
        "horse": best.get("horse", ""),
        "canonical_runner_key": key,
        "finish_position": best.get("finish_position", ""),
        "winner_flag": winner,
        "place_flag": place,
        "top4_flag": top4,
        "result_status": best.get("result_status", "PENDING_OR_NO_POSITION"),
        "result_source": best.get("result_source", ""),
        "result_confidence": best.get("result_confidence", 0),
        "result_resolution_status": resolution_status,
        "conflict_flag": conflict_flag,
        "conflict_reason": conflict_reason,
        "safe_for_model_validation": safe_model,
        "safe_for_execution_settlement": settlement_safe,
        "notes": "Canonical result truth resolved from available result and field sources. Pending rows are not treated as settled.",
    }

    conflict_row = None
    if conflict:
        conflict_row = {
            "race_date": best.get("race_date", ""),
            "track": best.get("track", ""),
            "race_no": best.get("race_no", ""),
            "horse": best.get("horse", ""),
            "canonical_runner_key": key,
            "candidate_count": len(candidates),
            "finish_positions_seen": ";".join(finish_positions),
            "sources_seen": ";".join(sources),
            "conflict_reason": conflict_reason,
            "recommended_resolution": "Review official result source and suppress from model validation until finish-position conflict is resolved.",
        }

    return output, conflict_row


def build_summary(rows: list[dict[str, object]], conflicts: list[dict[str, object]], source_counts: Counter, missing: list[str]) -> list[dict[str, object]]:
    statuses = Counter(str(row.get("result_resolution_status")) for row in rows)
    result_statuses = Counter(str(row.get("result_status")) for row in rows)
    sources = Counter(str(row.get("result_source")) for row in rows)
    summary: list[dict[str, object]] = [
        {"metric": "rows", "value": len(rows)},
        {"metric": "trusted_results", "value": statuses.get("TRUSTED_RESULT", 0)},
        {"metric": "safe_for_model_validation_yes", "value": sum(1 for row in rows if row.get("safe_for_model_validation") == "YES")},
        {"metric": "safe_for_execution_settlement_yes", "value": sum(1 for row in rows if row.get("safe_for_execution_settlement") == "YES")},
        {"metric": "no_position", "value": statuses.get("NO_POSITION", 0)},
        {"metric": "no_result_row", "value": statuses.get("NO_RESULT_ROW", 0)},
        {"metric": "scratched_rows", "value": result_statuses.get("SCRATCHED", 0)},
        {"metric": "conflict_results", "value": len(conflicts)},
    ]

    for name in missing:
        summary.append({"metric": f"missing_input::{name}", "value": 1})
    for name, count in source_counts.most_common():
        summary.append({"metric": f"source_rows::{name}", "value": count})
    for name, count in statuses.most_common():
        summary.append({"metric": f"resolution_status::{name}", "value": count})
    for name, count in result_statuses.most_common():
        summary.append({"metric": f"result_status::{name}", "value": count})
    for name, count in sources.most_common():
        summary.append({"metric": f"chosen_source::{name}", "value": count})

    return summary


def main() -> None:
    grouped, source_counts, missing = collect_candidates()
    output_rows: list[dict[str, object]] = []
    conflict_rows: list[dict[str, object]] = []

    for key in sorted(grouped):
        row, conflict = resolve_group(key, grouped[key])
        output_rows.append(row)
        if conflict:
            conflict_rows.append(conflict)

    summary_rows = build_summary(output_rows, conflict_rows, source_counts, missing)

    write_csv(OUT, output_rows, OUT_FIELDS)
    write_csv(SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv(CONFLICTS, conflict_rows, CONFLICT_FIELDS)

    statuses = Counter(str(row.get("result_resolution_status")) for row in output_rows)
    print("=" * 88)
    print("EDGEIQ CANONICAL RESULTS TRUTH V1")
    print("=" * 88)
    print(f"canonical result rows: {len(output_rows)}")
    print(f"trusted results: {statuses.get('TRUSTED_RESULT', 0)}")
    print(f"safe for model validation: {sum(1 for row in output_rows if row.get('safe_for_model_validation') == 'YES')}")
    print(f"conflicts: {len(conflict_rows)}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {CONFLICTS}")
    for status, count in statuses.most_common():
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()

