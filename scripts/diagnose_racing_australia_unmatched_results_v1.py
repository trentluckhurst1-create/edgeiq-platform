from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TARGET_DATE = "2026-05-31"
TARGET_TRACK = "SANDOWN LAKESIDE"
TARGET_RACES = {str(number) for number in range(1, 9)}

PRICE_TRUTH = DATA / "edgeiq_price_truth_history_v1.csv"
RA_NORMALISED = DATA / "racing_australia_sandown_2026_05_31_normalised_results_v1.csv"
RA_RAW = DATA / "racing_australia_sandown_2026_05_31_raw_results_v1.csv"
FINAL_CAPTURE = DATA / "edgeiq_sandown_final_results_capture_v1.csv"
SPORTSBET_FULL_DAY = DATA / "sportsbet_live_market_full_day_v5_2.csv"

DETAIL_OUT = DATA / "racing_australia_unmatched_results_v1.csv"
SUMMARY_OUT = DATA / "racing_australia_unmatched_results_v1_summary.csv"

DETAIL_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "issue_type",
    "classification",
    "settlement_blocking_reason",
    "price_truth_is_scratched",
    "ra_present",
    "ra_finish_position",
    "ra_finish_raw",
    "ra_won",
    "ra_starting_price",
    "ra_result_status",
    "sportsbet_present",
    "sportsbet_is_scratched",
    "sportsbet_runner_status",
    "sportsbet_selection_status",
    "sportsbet_status_code",
    "final_capture_status",
    "scratch_indicator_found",
    "scratching_indicator_source",
    "source_evidence",
    "notes",
]

SUMMARY_COLUMNS = ["section", "metric", "value", "source_path", "notes", "built_at"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def normalise_text(value: object) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\([^)]*\)", " ", text)
    text = text.replace("&", " AND ")
    text = re.sub(r"['`]", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def horse_key(value: object) -> str:
    return normalise_text(value).replace(" ", "")


def normalise_track(value: object) -> str:
    track = normalise_text(value)
    track = re.sub(r"\bSPORTS\s*BET\b", "SPORTSBET", track)
    track = re.sub(r"\bVIC\b|\bPROFESSIONAL\b|\bMETRO\b|\bTAB\b|\bMEETING\b", " ", track)
    track = re.sub(r"\bMELBOURNE\b|\bRACING\b|\bCLUB\b", " ", track)
    track = re.sub(r"\s+", " ", track).strip()
    if "SANDOWN" in track and "LAKESIDE" in track:
        return TARGET_TRACK
    if track.startswith("SPORTSBET "):
        track = track.replace("SPORTSBET ", "", 1)
    return track


def clean_race_no(value: object) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def target_key(date: object, track: object, race_no: object, horse_value: object, key_value: object = "") -> str:
    key = horse_key(key_value) or horse_key(horse_value)
    return "|".join([clean(date), normalise_track(track), clean_race_no(race_no), key])


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def truth_targets() -> dict[str, dict[str, str]]:
    columns, rows = read_csv(PRICE_TRUTH)
    required = {"race_date", "track", "race_no", "horse", "horse_key"}
    missing = sorted(required.difference(columns))
    if missing:
        raise ValueError(f"{PRICE_TRUTH} missing required columns: {missing}")

    targets: dict[str, dict[str, str]] = {}
    for row in rows:
        race_date = clean(row.get("race_date"))
        track = normalise_track(row.get("track"))
        race_no = clean_race_no(row.get("race_no"))
        if race_date != TARGET_DATE or track != TARGET_TRACK or race_no not in TARGET_RACES:
            continue
        key = target_key(race_date, track, race_no, row.get("horse"), row.get("horse_key"))
        targets[key] = {
            "race_date": race_date,
            "track": TARGET_TRACK,
            "race_no": race_no,
            "horse": clean(row.get("horse")),
            "horse_key": horse_key(row.get("horse_key")) or horse_key(row.get("horse")),
            "is_scratched": clean(row.get("is_scratched")),
        }
    return targets


def index_ra_normalised() -> dict[str, list[dict[str, str]]]:
    _, rows = read_csv(RA_NORMALISED)
    indexed: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = target_key(row.get("race_date"), row.get("track"), row.get("race_no"), row.get("horse"), row.get("horse_key"))
        indexed[key].append(row)
    return indexed


def index_ra_raw_finish() -> dict[str, str]:
    _, rows = read_csv(RA_RAW)
    indexed: dict[str, str] = {}
    for row in rows:
        key = target_key(row.get("race_date"), row.get("track"), row.get("race_no"), row.get("horse_raw"), "")
        indexed[key] = clean(row.get("finish_raw"))
    return indexed


def index_by_target(path: Path, horse_columns: list[str], key_columns: list[str]) -> dict[str, list[dict[str, str]]]:
    _, rows = read_csv(path)
    indexed: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        race_date = clean(row.get("race_date") or row.get("date") or row.get("snapshot_date"))
        track = normalise_track(row.get("track") or row.get("meeting_name") or row.get("venue"))
        race_no = clean_race_no(row.get("race_no") or row.get("race_number"))
        if race_date != TARGET_DATE or track != TARGET_TRACK or race_no not in TARGET_RACES:
            continue
        horse_value = first_present(row, horse_columns)
        key_value = first_present(row, key_columns)
        if not horse_value and not key_value:
            continue
        indexed[target_key(race_date, track, race_no, horse_value, key_value)].append(row)
    return indexed


def first_present(row: dict[str, str], columns: list[str]) -> str:
    for column in columns:
        if clean(row.get(column)):
            return clean(row.get(column))
    return ""


def truthy(value: object) -> bool:
    text = normalise_text(value)
    return text in {"TRUE", "YES", "Y", "1", "SCR", "SCRATCHED", "WITHDRAWN", "LATEWITHDRAWAL"}


def scratch_text_signal(value: object) -> bool:
    text = normalise_text(value)
    if not text:
        return False
    return bool(re.search(r"\bSCRATCH|WITHDRAW|LATE\s*SCR|NON\s*RUNNER|NOT\s*START", text))


def positive_scratch_signal(row: dict[str, str]) -> tuple[bool, str]:
    positive_columns = [
        "is_scratched",
        "scratched",
        "is_scratched_rated",
        "scratch",
    ]
    text_columns = [
        "scratching_details",
        "runner_status",
        "selection_status",
        "status",
        "market_status",
        "notes",
        "result_status",
        "match_status",
    ]
    for column in positive_columns:
        if column in row and truthy(row.get(column)):
            return True, f"{column}={clean(row.get(column))}"
    for column in text_columns:
        if column in row and scratch_text_signal(row.get(column)):
            return True, f"{column}={clean(row.get(column))}"
    return False, ""


def discovered_scratch_sources() -> list[Path]:
    candidates = [
        DATA / "edgeiq_vic_scratchings_diagnostics.csv",
        DATA / "scratchings.csv",
        DATA / "scratchings_gear.csv",
        DATA / "scratchings_report.csv",
        DATA / "race_card_active.csv",
        DATA / "race_card_report.csv",
        SPORTSBET_FULL_DAY,
    ]
    for path in DATA.glob("*scratch*.csv"):
        candidates.append(path)
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if path.exists() and path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


def build_scratch_evidence(targets: dict[str, dict[str, str]]) -> tuple[dict[str, list[str]], list[str]]:
    evidence: dict[str, list[str]] = defaultdict(list)
    scanned_sources: list[str] = []
    target_keys = set(targets)

    for path in discovered_scratch_sources():
        scanned_sources.append(str(path))
        indexed = index_by_target(path, ["horse", "horse_rated", "runner", "selection_name"], ["horse_key", "_horse_key"])
        for key, rows in indexed.items():
            if key not in target_keys:
                continue
            for row in rows:
                positive, reason = positive_scratch_signal(row)
                if positive:
                    evidence[key].append(f"{path.name}:{reason}")
    return evidence, scanned_sources


def format_source_rows(rows: list[dict[str, str]], columns: list[str]) -> str:
    if not rows:
        return ""
    parts = []
    for row in rows[:3]:
        values = []
        for column in columns:
            value = clean(row.get(column))
            if value:
                values.append(f"{column}={value}")
        if values:
            parts.append("; ".join(values))
    return " | ".join(parts)


def classify_runner(
    target: dict[str, str],
    ra_rows: list[dict[str, str]],
    raw_finish: str,
    sportsbet_rows: list[dict[str, str]],
    final_rows: list[dict[str, str]],
    scratch_evidence: list[str],
) -> dict[str, object] | None:
    price_truth_scratched = truthy(target.get("is_scratched"))
    sportsbet_present = bool(sportsbet_rows)
    final_capture_status = first_present(final_rows[0], ["result_status"]) if final_rows else ""
    sportsbet_evidence = format_source_rows(
        sportsbet_rows,
        ["sportsbet_price", "is_scratched", "runner_status", "selection_status", "status_code", "notes"],
    )
    final_evidence = format_source_rows(final_rows, ["result_status", "match_status", "notes"])

    scratch_sources = list(scratch_evidence)
    if price_truth_scratched:
        scratch_sources.append("edgeiq_price_truth_history_v1.csv:is_scratched=TRUE")

    sportsbet_scratch_sources = []
    for row in sportsbet_rows:
        positive, reason = positive_scratch_signal(row)
        if positive:
            sportsbet_scratch_sources.append(f"sportsbet_live_market_full_day_v5_2.csv:{reason}")
    scratch_sources.extend(sportsbet_scratch_sources)

    if not ra_rows:
        if scratch_sources:
            classification = "LIKELY_SCRATCHED"
            reason = "Runner is absent from the Racing Australia official result rows and a scratching indicator exists in a local source."
        elif sportsbet_present:
            classification = "LIKELY_NON_RUNNER"
            reason = "Runner is absent from Racing Australia official result rows; no local scratching flag was found, so settlement must treat this as non-runner/unresolved until a final scratching source confirms it."
        else:
            classification = "UNKNOWN_SETTLEMENT_BLOCKER"
            reason = "Runner is absent from Racing Australia official result rows and no supporting market/scratching source row was found."
        return {
            "race_date": target["race_date"],
            "track": target["track"],
            "race_no": target["race_no"],
            "horse": target["horse"],
            "horse_key": target["horse_key"],
            "issue_type": "UNMATCHED_TARGET_RUNNER",
            "classification": classification,
            "settlement_blocking_reason": reason,
            "price_truth_is_scratched": target.get("is_scratched", ""),
            "ra_present": "FALSE",
            "ra_finish_position": "",
            "ra_finish_raw": "",
            "ra_won": "",
            "ra_starting_price": "",
            "ra_result_status": "",
            "sportsbet_present": "TRUE" if sportsbet_present else "FALSE",
            "sportsbet_is_scratched": first_present(sportsbet_rows[0], ["is_scratched"]) if sportsbet_rows else "",
            "sportsbet_runner_status": first_present(sportsbet_rows[0], ["runner_status"]) if sportsbet_rows else "",
            "sportsbet_selection_status": first_present(sportsbet_rows[0], ["selection_status"]) if sportsbet_rows else "",
            "sportsbet_status_code": first_present(sportsbet_rows[0], ["status_code"]) if sportsbet_rows else "",
            "final_capture_status": final_capture_status,
            "scratch_indicator_found": "YES" if scratch_sources else "NO",
            "scratching_indicator_source": " | ".join(scratch_sources),
            "source_evidence": " || ".join(part for part in [sportsbet_evidence, final_evidence] if part),
            "notes": "Do not infer a finishing position or winner flag.",
        }

    primary = ra_rows[0]
    finish_position = clean(primary.get("finish_position"))
    won = clean(primary.get("won"))
    if finish_position and won:
        return None

    if raw_finish and not parse_numeric_finish(raw_finish):
        classification = "FAILED_TO_FINISH_OR_NO_FINISH"
        reason = f"Racing Australia result row is present but finish marker is {raw_finish}, not a numeric finishing position."
    elif not finish_position:
        classification = "RESULT_PARSE_GAP"
        reason = "Racing Australia result row is present but no numeric finish position was parsed."
    else:
        classification = "RESULT_PARSE_GAP"
        reason = "Racing Australia result row is present but won flag was not populated."

    return {
        "race_date": target["race_date"],
        "track": target["track"],
        "race_no": target["race_no"],
        "horse": target["horse"],
        "horse_key": target["horse_key"],
        "issue_type": "MATCHED_RA_ROW_MISSING_SETTLEMENT_FIELDS",
        "classification": classification,
        "settlement_blocking_reason": reason,
        "price_truth_is_scratched": target.get("is_scratched", ""),
        "ra_present": "TRUE",
        "ra_finish_position": finish_position,
        "ra_finish_raw": raw_finish,
        "ra_won": won,
        "ra_starting_price": clean(primary.get("starting_price")),
        "ra_result_status": clean(primary.get("result_status")),
        "sportsbet_present": "TRUE" if sportsbet_present else "FALSE",
        "sportsbet_is_scratched": first_present(sportsbet_rows[0], ["is_scratched"]) if sportsbet_rows else "",
        "sportsbet_runner_status": first_present(sportsbet_rows[0], ["runner_status"]) if sportsbet_rows else "",
        "sportsbet_selection_status": first_present(sportsbet_rows[0], ["selection_status"]) if sportsbet_rows else "",
        "sportsbet_status_code": first_present(sportsbet_rows[0], ["status_code"]) if sportsbet_rows else "",
        "final_capture_status": final_capture_status,
        "scratch_indicator_found": "YES" if scratch_sources else "NO",
        "scratching_indicator_source": " | ".join(scratch_sources),
        "source_evidence": " || ".join(part for part in [sportsbet_evidence, final_evidence] if part),
        "notes": "Do not convert FF/no-finish marker into a placing.",
    }


def parse_numeric_finish(value: object) -> bool:
    return bool(re.fullmatch(r"\d+", clean(value)))


def summary_row(section: str, metric: str, value: object, source_path: Path | str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": str(source_path),
        "notes": notes,
        "built_at": now_utc(),
    }


def build_summary(
    targets: dict[str, dict[str, str]],
    ra_index: dict[str, list[dict[str, str]]],
    blocker_rows: list[dict[str, object]],
    scanned_sources: list[str],
    scratch_evidence: dict[str, list[str]],
) -> list[dict[str, object]]:
    ra_rows = [row for rows in ra_index.values() for row in rows]
    matched_keys = set(targets).intersection(ra_index)
    unmatched_keys = set(targets).difference(ra_index)
    matched_missing_finish = [
        row
        for key in matched_keys
        for row in ra_index[key]
        if not clean(row.get("finish_position"))
    ]
    matched_missing_won = [
        row
        for key in matched_keys
        for row in ra_index[key]
        if not clean(row.get("won"))
    ]
    classifications = Counter(str(row["classification"]) for row in blocker_rows)
    issue_types = Counter(str(row["issue_type"]) for row in blocker_rows)
    unmatched_by_race = Counter(targets[key]["race_no"] for key in unmatched_keys)

    true_missing = (
        classifications.get("UNKNOWN_SETTLEMENT_BLOCKER", 0)
        + classifications.get("RESULT_PARSE_GAP", 0)
    )
    rows = [
        summary_row("input", "target_truth_runners", len(targets), PRICE_TRUTH),
        summary_row("input", "ra_normalised_rows", len(ra_rows), RA_NORMALISED),
        summary_row("match", "matched_target_runners", len(matched_keys), RA_NORMALISED),
        summary_row("match", "unmatched_target_runners", len(unmatched_keys), PRICE_TRUTH),
        summary_row("match", "matched_but_missing_finish_position", len(matched_missing_finish), RA_NORMALISED),
        summary_row("match", "matched_but_missing_won_flag", len(matched_missing_won), RA_NORMALISED),
        summary_row("scratchings", "scratching_indicators_found", "YES" if scratch_evidence else "NO", "", "Positive local scratching flags only."),
        summary_row("scratchings", "source_of_scratch_indicator", " | ".join(sorted({item.split(':', 1)[0] for values in scratch_evidence.values() for item in values})) or "NONE"),
        summary_row("scratchings", "scratching_source_files_scanned", len(scanned_sources), "", " | ".join(scanned_sources)),
        summary_row("classification", "likely_scratched_count", classifications.get("LIKELY_SCRATCHED", 0)),
        summary_row("classification", "likely_non_runner_count", classifications.get("LIKELY_NON_RUNNER", 0)),
        summary_row("classification", "likely_failed_to_finish_count", classifications.get("FAILED_TO_FINISH_OR_NO_FINISH", 0)),
        summary_row("classification", "true_missing_count", true_missing, "", "UNKNOWN_SETTLEMENT_BLOCKER + RESULT_PARSE_GAP."),
        summary_row("classification", "blocker_rows", len(blocker_rows), DETAIL_OUT),
    ]

    for race_no in sorted(TARGET_RACES, key=int):
        rows.append(summary_row("unmatched_by_race", f"R{race_no}", unmatched_by_race.get(race_no, 0)))
    for issue_type, count in sorted(issue_types.items()):
        rows.append(summary_row("issue_type", issue_type, count))
    for classification, count in sorted(classifications.items()):
        rows.append(summary_row("classification_count", classification, count))
    for row in sorted(blocker_rows, key=lambda item: (int(str(item["race_no"])), str(item["horse"]))):
        rows.append(
            summary_row(
                "settlement_blocking_reason_by_horse",
                f"R{row['race_no']} {row['horse']}",
                row["classification"],
                DETAIL_OUT,
                str(row["settlement_blocking_reason"]),
            )
        )
    return rows


def main() -> None:
    targets = truth_targets()
    ra_index = index_ra_normalised()
    raw_finish = index_ra_raw_finish()
    sportsbet_index = index_by_target(SPORTSBET_FULL_DAY, ["horse"], ["horse_key"])
    final_capture_index = index_by_target(FINAL_CAPTURE, ["horse"], ["horse_key"])
    scratch_evidence, scanned_sources = build_scratch_evidence(targets)

    blocker_rows: list[dict[str, object]] = []
    for key, target in sorted(targets.items(), key=lambda item: (int(item[1]["race_no"]), item[1]["horse_key"])):
        row = classify_runner(
            target=target,
            ra_rows=ra_index.get(key, []),
            raw_finish=raw_finish.get(key, ""),
            sportsbet_rows=sportsbet_index.get(key, []),
            final_rows=final_capture_index.get(key, []),
            scratch_evidence=scratch_evidence.get(key, []),
        )
        if row:
            blocker_rows.append(row)

    summary_rows = build_summary(targets, ra_index, blocker_rows, scanned_sources, scratch_evidence)

    write_csv(DETAIL_OUT, blocker_rows, DETAIL_COLUMNS)
    write_csv(SUMMARY_OUT, summary_rows, SUMMARY_COLUMNS)

    print("=" * 96)
    print("RACING AUSTRALIA UNMATCHED RESULTS DIAGNOSTIC V1 - READ ONLY")
    print("=" * 96)
    for row in summary_rows:
        if row["section"] in {"input", "match", "scratchings", "classification"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print(f"wrote: {DETAIL_OUT}")
    print(f"wrote: {SUMMARY_OUT}")
    print("=" * 96)


if __name__ == "__main__":
    main()
