from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
MARKET = DATA / "edgeiq_market_terminal_feed_v1.csv"
MAP = DATA / "edgeiq_map_terminal_feed_v1.csv"
EPI = DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv"
INSIGHTS = DATA / "edgeiq_insights_terminal_feed_v1.csv"
OUT_JSON = DATA / "edgeiq_current_victorian_end_to_end_v2_audit.json"
OUT_TXT = DATA / "edgeiq_current_victorian_end_to_end_v2_audit.txt"


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"none", "null", "nan", "n/a", "na", "-", "missing"}:
        return ""
    return text


def normalise(value: Any) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


def number_text(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    try:
        n = float(text)
    except ValueError:
        return text
    return str(int(n)) if n.is_integer() else str(n)


def race_key(date: Any, track: Any, race_no: Any) -> str:
    return f"{clean(date)}|{normalise(track)}|{number_text(race_no)}"


def runner_name(runner: dict[str, Any]) -> str:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
    return clean(official.get("runner")) or clean(source.get("horseName")) or clean(source.get("runnerName")) or clean(source.get("horse"))


def runner_field(runner: dict[str, Any], *names: str) -> str:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
    for name in names:
        value = clean(official.get(name)) or clean(source.get(name))
        if value:
            return value
    return ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    market_rows = read_csv(MARKET)
    map_rows = read_csv(MAP)
    epi_rows = read_csv(EPI)
    insight_rows = read_csv(INSIGHTS)

    market_by_meeting: dict[str, int] = defaultdict(int)
    market_runner_keys = set()
    for row in market_rows:
        key = f"{clean(row.get('race_date'))}|{normalise(row.get('track'))}"
        if clean(row.get("market")):
            market_by_meeting[key] += 1
        market_runner_keys.add((clean(row.get("race_date")), normalise(row.get("track")), number_text(row.get("race_no")), normalise(row.get("horse"))))

    meetings = payload.get("meetings", []) if isinstance(payload, dict) else []
    selected = None
    selected_score = -1
    for meeting in meetings:
        if not isinstance(meeting, dict):
            continue
        key = f"{clean(meeting.get('date'))}|{normalise(meeting.get('meeting'))}"
        score = market_by_meeting.get(key, 0)
        if score > selected_score:
            selected = meeting
            selected_score = score
    if not isinstance(selected, dict):
        raise SystemExit("No selected meeting")

    date = clean(selected.get("date"))
    track = clean(selected.get("meeting"))
    meeting_key = f"{date}|{normalise(track)}"
    races = selected.get("races", []) or []
    runner_rows: list[dict[str, Any]] = []
    unavailable = Counter()
    mismatches: list[str] = []
    for race in races:
        if not isinstance(race, dict):
            continue
        race_no = number_text(race.get("raceNumber"))
        canonical_race_key = race_key(date, track, race_no)
        for runner in race.get("runners", []) or []:
            if not isinstance(runner, dict):
                continue
            horse = runner_name(runner)
            key = (date, normalise(track), race_no, normalise(horse))
            row = {
                "race_key": canonical_race_key,
                "race_no": race_no,
                "horse": horse,
                "saddlecloth": runner_field(runner, "no", "number", "runnerNumber", "runner_no", "saddlecloth"),
                "barrier": runner_field(runner, "barrier", "bar"),
                "weight": runner_field(runner, "weight", "weightKg", "carriedWeight"),
                "jockey": runner_field(runner, "jockey", "jockeyName"),
                "trainer": runner_field(runner, "trainer", "trainerName"),
                "market_available": key in market_runner_keys,
            }
            if not row["barrier"]:
                unavailable["barrier"] += 1
            if not row["weight"]:
                unavailable["weight"] += 1
            if not row["jockey"]:
                unavailable["jockey"] += 1
            if not row["trainer"]:
                unavailable["trainer"] += 1
            runner_rows.append(row)

    map_value_rows = sum(1 for row in map_rows if clean(row.get("race_date")) == date and normalise(row.get("track")) == normalise(track) and (clean(row.get("run_style")) or clean(row.get("map_lane")) or clean(row.get("early_speed"))))
    epi_value_rows = sum(1 for row in epi_rows if clean(row.get("race_date")) == date and normalise(row.get("track")) == normalise(track) and clean(row.get("current_epi")))
    insight_value_rows = sum(1 for row in insight_rows if clean(row.get("race_date")) == date and normalise(row.get("track")) == normalise(track) and (clean(row.get("title")) or clean(row.get("body")) or clean(row.get("insight"))))
    market_value_rows = sum(1 for row in market_rows if clean(row.get("race_date")) == date and normalise(row.get("track")) == normalise(track) and clean(row.get("market")))
    edgeiq_price_rows = sum(1 for row in market_rows if clean(row.get("race_date")) == date and normalise(row.get("track")) == normalise(track) and clean(row.get("edgeiq_price")))

    if len(runner_rows) == 0:
        mismatches.append("SELECTED_MEETING_HAS_NO_RUNNERS")

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    audit = {
        "marker": "EDGEIQ_CURRENT_VICTORIAN_END_TO_END_V2_AUDIT_PASS" if not mismatches else "EDGEIQ_CURRENT_VICTORIAN_END_TO_END_V2_AUDIT_FAIL",
        "generated_at": generated_at,
        "selected_meeting": {"date": date, "track": track, "meeting_key": meeting_key, "market_score": selected_score},
        "races": len(races),
        "runners": len(runner_rows),
        "identity": {
            "race_numbers": sorted({row["race_no"] for row in runner_rows}, key=lambda x: int(x) if x.isdigit() else 999),
            "runner_identity_rows": len(runner_rows),
            "market_identity_rows": len([row for row in runner_rows if row["market_available"]]),
        },
        "coverage": {
            "market": market_value_rows,
            "edgeiq_price": edgeiq_price_rows,
            "epi": epi_value_rows,
            "map": map_value_rows,
            "insights": insight_value_rows,
        },
        "unavailable_reasons": {
            **dict(unavailable),
            "edgeiq_price": "No current governed EDGEiQ price source matched the active catalogue.",
            "epi": "Current EPI source is stale against active catalogue.",
            "map": "Current map evidence source is stale against active catalogue.",
            "insights": "Current intelligence source is stale against active catalogue.",
            "results": "No governed current result rows for active catalogue races.",
        },
        "mismatches": mismatches,
        "sample_runners": runner_rows[:10],
    }
    OUT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                audit["marker"],
                f"selected_meeting={date}|{track}",
                f"races={len(races)}",
                f"runners={len(runner_rows)}",
                f"market_rows={market_value_rows}",
                f"edgeiq_price_rows={edgeiq_price_rows}",
                f"epi_rows={epi_value_rows}",
                f"map_rows={map_value_rows}",
                f"insight_rows={insight_value_rows}",
                f"mismatches={'; '.join(mismatches) if mismatches else 'none'}",
            ]
        ),
        encoding="utf-8",
    )
    print(audit["marker"])
    if mismatches:
        raise SystemExit("; ".join(mismatches))


if __name__ == "__main__":
    main()
