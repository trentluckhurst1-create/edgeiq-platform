from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOC = ROOT / "docs" / "engineering" / "EDGEIQ_CURRENT_IDENTITY_MATCHING_FORENSIC_20260715.md"
OUT_TXT = DATA / "edgeiq_current_identity_matching_v1_audit.txt"
OUT_JSON = DATA / "edgeiq_current_identity_matching_v1_audit.json"
MARKER = "EDGEIQ_CURRENT_IDENTITY_MATCHING_V1_AUDIT_PASS"

CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
FORM = DATA / "edgeiq_form_guide_enriched_v2.json"

TERMINAL_FEEDS = {
    "MAP": DATA / "edgeiq_map_terminal_feed_v1.csv",
    "Insights": DATA / "edgeiq_insights_terminal_feed_v1.csv",
    "Performance/EPI": DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv",
    "Market": DATA / "edgeiq_market_terminal_feed_v1.csv",
}


def text(value: Any) -> str:
    if value is None:
        return ""
    output = str(value).strip()
    if output.lower() in {"", "-", "none", "null", "undefined", "n/a", "na"}:
        return ""
    return output


def normalise_track(value: Any) -> str:
    return re.sub(
        r"[^A-Z0-9]+",
        "",
        re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|THE|RACECOURSE|RACING|TRACK)\b", " ", text(value).upper()),
    )


def normalise_runner(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def race_no(value: Any) -> str:
    found = re.search(r"\d+", text(value))
    return found.group(0) if found else ""


def canonical_race_key(date: Any, track: Any, race_number: Any) -> str:
    return "|".join([text(date), normalise_track(track), race_no(race_number)])


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def runner_name(runner: dict[str, Any]) -> str:
    official = runner.get("official") or {}
    source = runner.get("source") or {}
    return text(official.get("runner")) or text(source.get("horseName")) or text(source.get("runnerName")) or text(source.get("horse"))


def runner_no(runner: dict[str, Any], index: int) -> str:
    official = runner.get("official") or {}
    source = runner.get("source") or {}
    return (
        text(official.get("no"))
        or text(official.get("number"))
        or text(source.get("runnerNumber"))
        or text(source.get("runner_no"))
        or text(source.get("saddlecloth"))
        or str(index + 1)
    )


def flatten_catalog() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = load_json(CATALOG)
    races: list[dict[str, Any]] = []
    runners: list[dict[str, Any]] = []
    for meeting in payload.get("meetings", []) or []:
        for race in meeting.get("races", []) or []:
            race_key = text(race.get("raceKey"))
            canonical = canonical_race_key(meeting.get("date"), meeting.get("meeting"), race.get("raceNumber"))
            race_row = {
                "race_key": race_key,
                "canonical": canonical,
                "meeting_key": text(meeting.get("meetingKey")),
                "date": text(meeting.get("date")),
                "track": text(meeting.get("meeting")),
                "race_no": race_no(race.get("raceNumber")),
                "runner_count": len(race.get("runners", []) or []),
            }
            races.append(race_row)
            for index, runner in enumerate(race.get("runners", []) or []):
                name = runner_name(runner)
                runners.append(
                    {
                        **race_row,
                        "no": runner_no(runner, index),
                        "runner": name,
                        "runner_norm": normalise_runner(name),
                        "raw": runner,
                    }
                )
    return races, runners


def race_match_summary(rows: list[dict[str, str]], catalog_races: list[dict[str, Any]]) -> dict[str, Any]:
    catalog_exact = {race["race_key"] for race in catalog_races}
    catalog_canonical = {race["canonical"] for race in catalog_races}
    feed_exact = {text(row.get("race_key")) for row in rows if text(row.get("race_key"))}
    feed_canonical = {canonical_race_key(row.get("race_date"), row.get("track"), row.get("race_no")) for row in rows if text(row.get("race_date"))}
    exact_matches = feed_exact & catalog_exact
    canonical_matches = feed_canonical & catalog_canonical
    exact_only_misses = sorted(list(feed_exact - catalog_exact))[:20]
    canonical_only_misses = sorted(list(feed_canonical - catalog_canonical))[:20]
    return {
        "feed_rows": len(rows),
        "feed_races_exact": len(feed_exact),
        "feed_races_canonical": len(feed_canonical),
        "catalog_races": len(catalog_races),
        "exact_race_matches": len(exact_matches),
        "canonical_race_matches": len(canonical_matches),
        "exact_race_misses": len(feed_exact - catalog_exact),
        "canonical_race_misses": len(feed_canonical - catalog_canonical),
        "sample_exact_misses": exact_only_misses,
        "sample_canonical_misses": canonical_only_misses,
    }


def runner_match_summary(rows: list[dict[str, str]], catalog_runners: list[dict[str, Any]]) -> dict[str, Any]:
    by_race: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for runner in catalog_runners:
        by_race[runner["race_key"]].append(runner)

    matched_by_name = 0
    matched_by_no = 0
    unmatched = 0
    unmatched_reasons = Counter()
    duplicate_keys = Counter((row.get("race_key", ""), row.get("no", ""), normalise_runner(row.get("horse"))) for row in rows)
    duplicate_count = sum(1 for count in duplicate_keys.values() if count > 1)

    runner_rows = [row for row in rows if text(row.get("horse")) or text(row.get("no"))]
    for row in runner_rows:
        race_key = text(row.get("race_key"))
        catalog = by_race.get(race_key, [])
        if not catalog:
            unmatched += 1
            unmatched_reasons["RACE_KEY_NOT_IN_CATALOG"] += 1
            continue
        horse = normalise_runner(row.get("horse"))
        no = text(row.get("no"))
        if horse and any(candidate["runner_norm"] == horse for candidate in catalog):
            matched_by_name += 1
        elif no and any(str(candidate["no"]) == no for candidate in catalog):
            matched_by_no += 1
        else:
            unmatched += 1
            if not horse and not no:
                unmatched_reasons["MISSING_RUNNER_IDENTITY"] += 1
            else:
                unmatched_reasons["RUNNER_NOT_IN_CATALOG_RACE"] += 1

    return {
        "runner_rows": len(runner_rows),
        "runner_matches": matched_by_name + matched_by_no,
        "matched_by_name": matched_by_name,
        "matched_by_no": matched_by_no,
        "runner_unmatched": unmatched,
        "unmatched_reasons": dict(unmatched_reasons),
        "duplicate_identity_rows": duplicate_count,
    }


def count_present(rows: list[dict[str, str]], fields: list[str]) -> int:
    return sum(1 for row in rows if any(text(row.get(field)) for field in fields))


def form_enriched_summary(catalog_runners: list[dict[str, Any]]) -> dict[str, Any]:
    payload = load_json(FORM)
    races = payload.get("races", []) if isinstance(payload, dict) else []
    form_by_key = {text(race.get("raceKey")): race for race in races if isinstance(race, dict)}
    form_by_canonical = {
        canonical_race_key(race.get("raceDate"), race.get("meeting"), race.get("raceNumber")): race
        for race in races
        if isinstance(race, dict)
    }
    coverage = Counter()
    totals = Counter()
    unmatched = Counter()
    for runner in catalog_runners:
        totals["catalog_runners"] += 1
        race = form_by_key.get(runner["canonical"]) or form_by_canonical.get(runner["canonical"])
        if not race:
            unmatched["FORM_RACE_NOT_FOUND"] += 1
            continue
        form_runners = race.get("runners", []) or []
        found = None
        for form_runner in form_runners:
            if normalise_runner(form_runner.get("runnerName")) == runner["runner_norm"]:
                found = form_runner
                break
            if text(form_runner.get("runnerNumber")) and text(form_runner.get("runnerNumber")) == runner["no"]:
                found = form_runner
                break
        if not found:
            unmatched["FORM_RUNNER_NOT_FOUND"] += 1
            continue
        coverage["form_runner_matches"] += 1
        field_map = {
            "EPI": ["epi", "rating"],
            "Suitability": ["suitability"],
            "Form Momentum": ["formMomentum"],
            "Early Speed": ["earlySpeed"],
            "Late Speed": ["lateSpeed"],
            "EDGEiQ Price": ["edgeiqPrice"],
            "Market": ["marketPrice"],
        }
        for label, keys in field_map.items():
            if any(source_value_present(found.get(key)) for key in keys):
                coverage[label] += 1
    return {
        "form_races": len(races),
        "catalog_runners": totals["catalog_runners"],
        "form_runner_matches": coverage["form_runner_matches"],
        "coverage": dict(coverage),
        "unmatched": dict(unmatched),
    }


def source_value_present(value: Any) -> bool:
    if isinstance(value, dict) and "value" in value:
        return bool(text(value.get("value")))
    return bool(text(value))


def historical_epi_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    start_fields = [f"start_{index}" for index in range(1, 11)]
    covered_rows = sum(1 for row in rows if any(text(row.get(field)) for field in start_fields))
    total_tiles = sum(1 for row in rows for field in start_fields if text(row.get(field)))
    current_epi_rows = count_present(rows, ["current_epi"])
    return {
        "rows": len(rows),
        "current_epi_rows": current_epi_rows,
        "rows_with_historical_tiles": covered_rows,
        "historical_tiles": total_tiles,
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def main() -> None:
    failures: list[str] = []
    catalog_races, catalog_runners = flatten_catalog()
    if not catalog_races or not catalog_runners:
        failures.append("Current product catalogue is empty or unavailable")

    feed_reports: dict[str, Any] = {}
    for name, path in TERMINAL_FEEDS.items():
        rows = load_csv(path)
        race_summary = race_match_summary(rows, catalog_races)
        runner_summary = runner_match_summary(rows, catalog_runners)
        report = {**race_summary, **runner_summary}
        if name == "MAP":
            report["speed_value_rows"] = count_present(rows, ["early_speed", "projected_position", "run_style"])
            report["run_style_rows"] = count_present(rows, ["run_style"])
        elif name == "Insights":
            report["insight_value_rows"] = count_present(rows, ["key_insight", "edge", "card_value", "card_detail"])
        elif name == "Performance/EPI":
            report.update(historical_epi_summary(rows))
        elif name == "Market":
            report["market_rows"] = count_present(rows, ["market"])
            report["edgeiq_price_rows"] = count_present(rows, ["edgeiq_price"])
            report["move_rows"] = count_present(rows, ["move"])
        feed_reports[name] = report

    form_summary = form_enriched_summary(catalog_runners)

    rows_for_doc = []
    for name, report in feed_reports.items():
        rows_for_doc.append(
            [
                name,
                report["feed_rows"],
                report["exact_race_matches"],
                report["canonical_race_matches"],
                report["runner_matches"],
                report["runner_unmatched"],
                json.dumps(report.get("unmatched_reasons", {}), ensure_ascii=True),
            ]
        )

    metric_rows = [
        ["MAP speed/map values", feed_reports["MAP"].get("speed_value_rows", 0), feed_reports["MAP"].get("runner_rows", 0), "terminal feed fields: run_style/early_speed/projected_position"],
        ["Insights", feed_reports["Insights"].get("insight_value_rows", 0), feed_reports["Insights"].get("feed_rows", 0), "terminal feed cards/runner insight values"],
        ["Historical EPI tiles", feed_reports["Performance/EPI"].get("historical_tiles", 0), feed_reports["Performance/EPI"].get("rows", 0), "start_10..start_1 tile values"],
        ["Market", feed_reports["Market"].get("market_rows", 0), feed_reports["Market"].get("runner_rows", 0), "market field"],
        ["EPI", form_summary["coverage"].get("EPI", 0), form_summary["catalog_runners"], "form-guide enriched runner epi/rating"],
        ["Suitability", form_summary["coverage"].get("Suitability", 0), form_summary["catalog_runners"], "form-guide enriched suitability"],
        ["Form Momentum", form_summary["coverage"].get("Form Momentum", 0), form_summary["catalog_runners"], "form-guide enriched formMomentum"],
        ["Early Speed", form_summary["coverage"].get("Early Speed", 0), form_summary["catalog_runners"], "form-guide enriched earlySpeed"],
        ["Late Speed", form_summary["coverage"].get("Late Speed", 0), form_summary["catalog_runners"], "form-guide enriched lateSpeed"],
    ]

    doc_text = "\n".join(
        [
            "# EDGEiQ Current Identity Matching Forensic",
            "",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "This audit documents identity alignment only. It does not modify UI, feeds, formulas or governed values.",
            "",
            "## Catalogue Universe",
            "",
            f"- Current races: {len(catalog_races)}",
            f"- Current runners: {len(catalog_runners)}",
            f"- Race key style: exact catalogue key such as `{catalog_races[0]['race_key'] if catalog_races else ''}`",
            f"- Canonical key style: `{catalog_races[0]['canonical'] if catalog_races else ''}`",
            "",
            "## Feed Identity Match Summary",
            "",
            markdown_table(["Feed", "Rows", "Exact race matches", "Canonical race matches", "Runner matches", "Runner unmatched", "Unmatched reasons"], rows_for_doc),
            "",
            "## Required Coverage Counts",
            "",
            markdown_table(["Metric", "Covered / Value Rows", "Eligible / Rows", "Evidence field"], metric_rows),
            "",
            "## Exact Mismatch Findings",
            "",
            "- Terminal feeds for MAP, Market, Insights and EPI are keyed by exact catalogue-style `race_key`.",
            "- Form Guide enrichment is keyed by canonical `raceDate|normalised track|raceNumber` and then runner identity.",
            "- Identity matching can pass while governed evidence remains empty; this is visible in MAP and Insights pending rows.",
            "- Historical EPI tile matching is separate from current EPI matching; current EPI rows can exist while `start_10..start_1` tiles are empty.",
            "",
            "## Feed Samples Of Race-Key Misses",
            "",
            json.dumps({name: report.get("sample_exact_misses", []) for name, report in feed_reports.items()}, indent=2),
            "",
        ]
    )

    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(doc_text, encoding="utf-8")

    if failures:
        marker = "EDGEIQ_CURRENT_IDENTITY_MATCHING_V1_AUDIT_FAIL"
        status = "FAIL"
    else:
        marker = MARKER
        status = "PASS"

    payload = {
        "marker": marker,
        "status": status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "catalog": {"races": len(catalog_races), "runners": len(catalog_runners)},
        "feeds": feed_reports,
        "form_enriched": form_summary,
        "failures": failures,
    }

    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        marker,
        f"status={status}",
        f"catalog_races={len(catalog_races)}",
        f"catalog_runners={len(catalog_runners)}",
    ]
    for name, report in feed_reports.items():
        lines.append(
            f"{name}: rows={report['feed_rows']} exact_race_matches={report['exact_race_matches']} canonical_race_matches={report['canonical_race_matches']} runner_matches={report['runner_matches']} runner_unmatched={report['runner_unmatched']}"
        )
    lines.append(f"form_enriched_runner_matches={form_summary['form_runner_matches']}/{form_summary['catalog_runners']}")
    lines.append("metric_coverage:")
    for metric, covered, eligible, _evidence in metric_rows:
        lines.append(f"- {metric}: {covered}/{eligible}")
    if failures:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in failures)
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("\n".join(lines))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
