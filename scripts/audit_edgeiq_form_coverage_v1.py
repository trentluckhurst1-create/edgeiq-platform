import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
FORM_V2 = DATA / "edgeiq_form_intelligence_v2.csv"
HISTORY_DETAIL = DATA / "edgeiq_runner_history_detail_v1.csv"
RUNNER_HISTORY = DATA / "runner_form_history.csv"
HISTORY_MASTER = DATA / "edgeiq_historical_run_ratings_master_v1.csv"

OUT = DATA / "edgeiq_form_coverage_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_form_coverage_summary_v1.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def text(value: object) -> str:
    return str(value or "").strip()


def clean(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def canonical_horse(value: object) -> str:
    raw = text(value).upper()
    while "(" in raw and ")" in raw:
        start = raw.find("(")
        end = raw.find(")", start)
        if end < 0:
            break
        raw = raw[:start] + raw[end + 1 :]
    return clean(raw)


def loose_horse(value: object) -> str:
    key = canonical_horse(value)
    for suffix in ["NZ", "AUS", "GB", "IRE", "FR", "USA", "JPN"]:
        if key.endswith(suffix) and len(key) > len(suffix) + 2:
            return key[: -len(suffix)]
    return key


def race_date(row: dict[str, str]) -> str:
    return text(row.get("current_race_date") or row.get("race_date") or row.get("date"))


def race_no(row: dict[str, str]) -> str:
    return text(row.get("race_no") or row.get("race_number") or row.get("race"))


def horse(row: dict[str, str]) -> str:
    return text(row.get("horse") or row.get("runner") or row.get("runner_name"))


def is_scratched(row: dict[str, str]) -> bool:
    blob = " ".join(text(row.get(key)).upper() for key in ["display_decision", "runner_status", "scratch_status", "is_scratched"])
    return "SCRATCH" in blob or text(row.get("is_scratched")).upper() in {"YES", "Y", "TRUE", "1"}


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (race_date(row), clean(row.get("track")), race_no(row), canonical_horse(row.get("horse_key") or horse(row)))


def history_name(row: dict[str, str]) -> str:
    return text(row.get("horse") or row.get("recovery_horse") or row.get("runner") or row.get("horse_name"))


def main() -> None:
    active = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    form_rows = {runner_key(row): row for row in read_csv(FORM_V2)}

    strict_history: defaultdict[str, int] = defaultdict(int)
    loose_history: defaultdict[str, int] = defaultdict(int)
    history_names_by_loose: defaultdict[str, set[str]] = defaultdict(set)
    for source in [read_csv(HISTORY_DETAIL), read_csv(RUNNER_HISTORY), read_csv(HISTORY_MASTER)]:
        for row in source:
            name = history_name(row)
            strict = canonical_horse(row.get("horse_key") or name)
            loose = loose_horse(row.get("horse_key") or name)
            if strict:
                strict_history[strict] += 1
            if loose:
                loose_history[loose] += 1
                if name:
                    history_names_by_loose[loose].add(name)

    audit_rows: list[dict[str, object]] = []
    cause_counts: Counter[str] = Counter()
    usable_count = 0
    canonical_opportunity_count = 0

    for runner in active:
        strict_key = canonical_horse(runner.get("horse_key") or horse(runner))
        loose_key = loose_horse(runner.get("horse_key") or horse(runner))
        form = form_rows.get(runner_key(runner), {})
        form_runs = int(text(form.get("recent_runs_found")) or 0)
        strict_count = strict_history.get(strict_key, 0)
        loose_count = loose_history.get(loose_key, 0)

        usable = max(form_runs, strict_count) > 0
        if usable:
            usable_count += 1

        if strict_count == 0 and loose_count > 0:
            root_cause = "HORSE_NAME_MISMATCH"
            canonical_opportunity_count += 1
        elif strict_count == 0 and loose_count == 0:
            root_cause = "HISTORICAL_COVERAGE_GAP"
        elif form_runs == 0 and strict_count > 0:
            root_cause = "JOIN_KEY_GAP"
            canonical_opportunity_count += 1
        else:
            root_cause = "USABLE_FORM_HISTORY"
        cause_counts[root_cause] += 1

        audit_rows.append(
            {
                "race_date": race_date(runner),
                "track": text(runner.get("track")),
                "race_no": race_no(runner),
                "horse": horse(runner),
                "horse_key": text(runner.get("horse_key")),
                "canonical_horse": strict_key,
                "loose_horse": loose_key,
                "form_v2_recent_runs": form_runs,
                "strict_history_rows": strict_count,
                "loose_history_rows": loose_count,
                "usable_form_history_flag": "YES" if usable else "NO",
                "canonicalisation_opportunity": "YES" if root_cause in {"HORSE_NAME_MISMATCH", "JOIN_KEY_GAP"} else "NO",
                "example_history_names": " | ".join(sorted(history_names_by_loose.get(loose_key, set()))[:3]),
                "root_cause": root_cause,
            }
        )

    write_csv(
        OUT,
        audit_rows,
        [
            "race_date",
            "track",
            "race_no",
            "horse",
            "horse_key",
            "canonical_horse",
            "loose_horse",
            "form_v2_recent_runs",
            "strict_history_rows",
            "loose_history_rows",
            "usable_form_history_flag",
            "canonicalisation_opportunity",
            "example_history_names",
            "root_cause",
        ],
    )
    target = 300
    summary = [
        {"metric": "active_runner_rows", "value": len(active)},
        {"metric": "usable_form_history_rows", "value": usable_count},
        {"metric": "target_usable_form_history_rows", "value": target},
        {"metric": "target_gap_rows", "value": max(target - usable_count, 0)},
        {"metric": "canonicalisation_opportunity_rows", "value": canonical_opportunity_count},
    ]
    for cause, count in sorted(cause_counts.items()):
        summary.append({"metric": f"root_cause::{cause}", "value": count})
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(audit_rows)} rows)")
    print(f"Wrote {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
