from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
INPUT_HIDDEN_GEM = DATA / "edgeiq_hidden_gem_engine_v1.csv"

OUTPUT_MAIN = DATA / "edgeiq_current_hidden_gem_feed_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_current_hidden_gem_feed_v1_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_current_hidden_gem_feed_v1_audit.csv"


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def clean_horse(value: object) -> str:
    txt = upper(value)
    return "".join(ch for ch in txt if ch.isalnum())


def parse_date(value: object) -> Optional[datetime]:
    txt = clean(value)
    if txt == "":
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(txt, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def is_active_runner(row: Dict[str, str]) -> bool:
    flags = [
        upper(row.get("is_scratched")),
        upper(row.get("scratch_status")),
        upper(row.get("runner_status")),
    ]
    return not any(flag in {"1", "TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHING"} for flag in flags)


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    if not INPUT_BOARD.exists():
        raise FileNotFoundError(INPUT_BOARD)
    if not INPUT_HIDDEN_GEM.exists():
        raise FileNotFoundError(INPUT_HIDDEN_GEM)

    board_rows = []
    with INPUT_BOARD.open("r", encoding="utf-8-sig", newline="") as handle:
        board_rows = [row for row in csv.DictReader(handle) if is_active_runner(row)]

    history_by_key: DefaultDict[str, List[Dict[str, str]]] = defaultdict(list)
    history_by_name: DefaultDict[str, List[Dict[str, str]]] = defaultdict(list)
    with INPUT_HIDDEN_GEM.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            band = clean(row.get("hidden_gem_band"))
            if band not in {"HIGH", "MEDIUM", "LOW"}:
                continue
            key = clean_horse(row.get("horse_key"))
            name_key = clean_horse(row.get("horse"))
            if key:
                history_by_key[key].append(row)
            if name_key:
                history_by_name[name_key].append(row)

    for bucket in list(history_by_key.values()) + list(history_by_name.values()):
        bucket.sort(key=lambda item: parse_date(item.get("race_date")) or datetime.min, reverse=True)

    output_rows: List[Dict[str, object]] = []
    band_counts: Counter[str] = Counter()
    watch_counts: Counter[str] = Counter()
    evidence_counts: Counter[str] = Counter()
    matched = 0

    for row in board_rows:
        current_date = parse_date(row.get("race_date"))
        horse = clean(row.get("horse"))
        horse_key = clean_horse(row.get("horse_key")) or clean_horse(horse)
        history = history_by_key.get(horse_key, [])
        match_method = "HORSE_KEY"
        if not history:
            history = history_by_name.get(clean_horse(horse), [])
            match_method = "HORSE_NAME"

        prior_rows = []
        for item in history:
            item_date = parse_date(item.get("race_date"))
            if current_date is None or item_date is None or item_date < current_date:
                prior_rows.append(item)

        significant_rows = [item for item in prior_rows if clean(item.get("next_start_watch_flag")) == "YES"]
        signal_rows = prior_rows

        selected = significant_rows[0] if significant_rows else signal_rows[0] if signal_rows else None
        if selected is not None:
            matched += 1

        last_band = clean(selected.get("hidden_gem_band")) if selected else "UNKNOWN"
        band_counts[last_band] += 1
        hidden_watch = "YES" if selected is not None and clean(selected.get("next_start_watch_flag")) == "YES" else "NO"
        watch_counts[hidden_watch] += 1

        if selected is None:
            status = "NO_SIGNAL_HISTORY"
        elif hidden_watch == "YES":
            status = "WATCH_SIGNAL"
        else:
            status = "LOW_SIGNAL_ONLY"
        evidence_counts[status] += 1

        triggers = [clean(selected.get("trigger_1")) if selected else "", clean(selected.get("trigger_2")) if selected else "", clean(selected.get("trigger_3")) if selected else ""]
        trigger_text = " | ".join([item for item in triggers if item])

        output_rows.append(
            {
                "current_race_date": clean(row.get("race_date")),
                "track": upper(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "horse": horse,
                "horse_key": horse_key,
                "last_hidden_gem_score": clean(selected.get("hidden_gem_score")) if selected else "",
                "last_hidden_gem_band": last_band if selected else "UNKNOWN",
                "last_hidden_gem_date": clean(selected.get("race_date")) if selected else "",
                "last_hidden_gem_track": upper(selected.get("track")) if selected else "",
                "last_hidden_gem_race_no": clean(selected.get("race_no")) if selected else "",
                "last_hidden_gem_trigger": trigger_text,
                "hidden_gem_watch_flag": hidden_watch,
                "hidden_gem_narrative": clean(selected.get("hidden_gem_narrative")) if selected else "No recent hidden-gem signal matched for this runner.",
                "evidence_status": status,
                "match_method": match_method if selected else "NO_MATCH",
                "built_at": built_at,
            }
        )

    bendigo_rows = [row for row in output_rows if row["track"] == "BENDIGO"]
    bendigo_watch = sum(1 for row in bendigo_rows if row["hidden_gem_watch_flag"] == "YES")

    output_coverage_complete = len(output_rows) == len(board_rows) and len(board_rows) > 0
    has_actionable_watchlist = watch_counts.get("YES", 0) > 0 and matched > 0

    if output_coverage_complete and has_actionable_watchlist:
        readiness = "READY_WITH_GUARDRAILS"
    elif output_coverage_complete and matched > 0:
        readiness = "READY_WITH_GUARDRAILS"
    else:
        readiness = "NOT_READY"

    summary_row = {
        "status": "EDGEIQ_CURRENT_HIDDEN_GEM_FEED_V1_BUILT",
        "active_rows": len(board_rows),
        "output_rows": len(output_rows),
        "matched_current_runners": matched,
        "coverage_pct": f"{(matched / len(board_rows) * 100.0):.3f}" if board_rows else "",
        "hidden_gem_watch_count": watch_counts.get("YES", 0),
        "high_count": band_counts.get("HIGH", 0),
        "medium_count": band_counts.get("MEDIUM", 0),
        "low_count": band_counts.get("LOW", 0),
        "unknown_count": band_counts.get("UNKNOWN", 0),
        "bendigo_rows": len(bendigo_rows),
        "bendigo_watch_count": bendigo_watch,
        "full_output_coverage_flag": "YES" if output_coverage_complete else "NO",
        "readiness_verdict": readiness,
        "built_at": built_at,
    }

    audit_rows: List[Dict[str, object]] = []
    for name, count in sorted(band_counts.items()):
        audit_rows.append({"audit_type": "LAST_SIGNAL_BAND", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(watch_counts.items()):
        audit_rows.append({"audit_type": "WATCH_FLAG", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(evidence_counts.items()):
        audit_rows.append({"audit_type": "EVIDENCE_STATUS", "audit_value": name, "count": count, "built_at": built_at})
    audit_rows.append({"audit_type": "BENDIGO", "audit_value": "WATCH_COUNT", "count": bendigo_watch, "built_at": built_at})

    watch_examples = [row for row in output_rows if row["hidden_gem_watch_flag"] == "YES"][:10]
    for idx, row in enumerate(watch_examples, start=1):
        audit_rows.append(
            {
                "audit_type": "WATCH_EXAMPLE",
                "audit_value": f"{idx}. {row['horse']} {row['track']} R{row['race_no']} {row['last_hidden_gem_band']} {row['last_hidden_gem_trigger']}",
                "count": "",
                "built_at": built_at,
            }
        )

    fields = list(output_rows[0].keys()) if output_rows else [
        "current_race_date",
        "track",
        "race_no",
        "horse",
        "last_hidden_gem_band",
        "hidden_gem_watch_flag",
        "evidence_status",
    ]
    write_csv(OUTPUT_MAIN, output_rows, fields)
    write_csv(OUTPUT_SUMMARY, [summary_row], list(summary_row.keys()))
    write_csv(OUTPUT_AUDIT, audit_rows, ["audit_type", "audit_value", "count", "built_at"])

    print("EDGEiQ current Hidden Gem feed V1 built")
    print(f"Active rows: {len(board_rows)}")
    print(f"Matched current runners: {matched}")
    print(f"Watch count: {watch_counts.get('YES', 0)}")
    print(f"Readiness: {readiness}")


if __name__ == "__main__":
    main()
