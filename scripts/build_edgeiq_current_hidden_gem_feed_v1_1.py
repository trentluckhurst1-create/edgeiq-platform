from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_CURRENT_V1 = DATA / "edgeiq_current_hidden_gem_feed_v1.csv"
INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"

OUTPUT_MAIN = DATA / "edgeiq_current_hidden_gem_feed_v1_1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_current_hidden_gem_feed_v1_1_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_current_hidden_gem_feed_v1_1_audit.csv"


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


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


def to_float(value: object) -> Optional[float]:
    txt = clean(value).replace("$", "").replace("%", "")
    if txt == "":
        return None
    try:
        return float(txt)
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


def recency_band(days_since: Optional[int]) -> str:
    if days_since is None:
        return "NONE"
    if days_since <= 45:
        return "CURRENT"
    if days_since <= 90:
        return "RECENT"
    if days_since <= 180:
        return "STALE"
    return "HISTORICAL"


def recency_multiplier(band: str) -> float:
    if band == "CURRENT":
        return 1.00
    if band == "RECENT":
        return 0.90
    if band == "STALE":
        return 0.65
    if band == "HISTORICAL":
        return 0.40
    return 0.00


def build_narrative(
    base_narrative: str,
    hidden_watch_flag: str,
    actionable_watch_flag: str,
    historical_watch_flag: str,
    recency_band_value: str,
    days_since: Optional[int],
    customer_display_band: str,
) -> str:
    if actionable_watch_flag == "YES":
        prefix = "Recent hidden-gem signal remains actionable."
        if recency_band_value == "CURRENT":
            prefix = "Current hidden-gem signal remains actionable."
        return f"{prefix} {base_narrative}".strip()

    if historical_watch_flag == "YES":
        age_text = f"{days_since} days ago" if days_since is not None else "outside the current watch window"
        return (
            f"Historical hidden-gem profile only: last qualifying signal was {age_text}. "
            f"Use as background evidence rather than a current alert. {base_narrative}"
        ).strip()

    if hidden_watch_flag == "YES":
        return f"Hidden-gem watch signal exists, but recency could not be established. {base_narrative}".strip()

    if customer_display_band == "NO_SIGNAL":
        if clean(base_narrative) != "":
            return f"Prior hidden-gem evidence exists but does not qualify as a current watch signal. {base_narrative}".strip()
        return "No actionable hidden-gem signal is available for this runner."

    return clean(base_narrative)


def main() -> None:
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    if not INPUT_CURRENT_V1.exists():
        raise FileNotFoundError(INPUT_CURRENT_V1)

    base_rows: List[Dict[str, str]] = []
    with INPUT_CURRENT_V1.open("r", encoding="utf-8-sig", newline="") as handle:
        base_rows = list(csv.DictReader(handle))

    active_runner_count = len(base_rows)
    if INPUT_BOARD.exists():
        with INPUT_BOARD.open("r", encoding="utf-8-sig", newline="") as handle:
            live_rows = [row for row in csv.DictReader(handle) if is_active_runner(row)]
            active_runner_count = len(live_rows)

    output_rows: List[Dict[str, object]] = []
    recency_counts: Counter[str] = Counter()
    display_counts: Counter[str] = Counter()
    actionable_count = 0
    historical_count = 0
    original_watch_count = 0
    bendigo_actionable_count = 0

    for row in base_rows:
        current_date = parse_date(row.get("current_race_date"))
        signal_date = parse_date(row.get("last_hidden_gem_date"))
        days_since: Optional[int] = None
        if current_date is not None and signal_date is not None:
            days_since = max(0, (current_date - signal_date).days)

        band = recency_band(days_since)
        recency_counts[band] += 1

        hidden_watch_flag = "YES" if upper(row.get("hidden_gem_watch_flag")) == "YES" else "NO"
        if hidden_watch_flag == "YES":
            original_watch_count += 1

        actionable_watch_flag = "YES" if hidden_watch_flag == "YES" and band in {"CURRENT", "RECENT"} else "NO"
        historical_watch_flag = "YES" if hidden_watch_flag == "YES" and band in {"STALE", "HISTORICAL"} else "NO"

        if actionable_watch_flag == "YES":
            actionable_count += 1
        if historical_watch_flag == "YES":
            historical_count += 1
        if upper(row.get("track")) == "BENDIGO" and actionable_watch_flag == "YES":
            bendigo_actionable_count += 1

        raw_score = to_float(row.get("last_hidden_gem_score"))
        adjusted_score = None
        if raw_score is not None and band != "NONE":
            adjusted_score = raw_score * recency_multiplier(band)

        last_band = upper(row.get("last_hidden_gem_band"))
        if actionable_watch_flag == "YES" and last_band in {"HIGH", "MEDIUM", "LOW"}:
            customer_band = last_band
        elif hidden_watch_flag == "YES" and band in {"STALE", "HISTORICAL"}:
            customer_band = "HISTORICAL_SIGNAL"
        else:
            customer_band = "NO_SIGNAL"
        display_counts[customer_band] += 1

        base_narrative = clean(row.get("hidden_gem_narrative"))
        updated_narrative = build_narrative(
            base_narrative=base_narrative,
            hidden_watch_flag=hidden_watch_flag,
            actionable_watch_flag=actionable_watch_flag,
            historical_watch_flag=historical_watch_flag,
            recency_band_value=band,
            days_since=days_since,
            customer_display_band=customer_band,
        )

        output_row = dict(row)
        output_row.update(
            {
                "days_since_hidden_gem": "" if days_since is None else str(days_since),
                "hidden_gem_recency_band": band,
                "actionable_watch_flag": actionable_watch_flag,
                "historical_watch_flag": historical_watch_flag,
                "customer_display_band": customer_band,
                "recency_adjusted_hidden_gem_score": "" if adjusted_score is None else f"{adjusted_score:.2f}",
                "hidden_gem_narrative": updated_narrative,
                "built_at": built_at,
            }
        )
        output_rows.append(output_row)

    if len(output_rows) == active_runner_count and actionable_count > 0:
        readiness = "READY_FOR_UI"
    elif len(output_rows) == active_runner_count and (actionable_count > 0 or historical_count > 0):
        readiness = "READY_WITH_GUARDRAILS"
    else:
        readiness = "NOT_READY"

    summary_row = {
        "status": "EDGEIQ_CURRENT_HIDDEN_GEM_FEED_V1_1_BUILT",
        "active_rows": active_runner_count,
        "input_rows": len(base_rows),
        "output_rows": len(output_rows),
        "original_watch_count": original_watch_count,
        "actionable_watch_count": actionable_count,
        "historical_watch_count": historical_count,
        "bendigo_actionable_watch_count": bendigo_actionable_count,
        "current_band_count": recency_counts.get("CURRENT", 0),
        "recent_band_count": recency_counts.get("RECENT", 0),
        "stale_band_count": recency_counts.get("STALE", 0),
        "historical_band_count": recency_counts.get("HISTORICAL", 0),
        "none_band_count": recency_counts.get("NONE", 0),
        "high_display_count": display_counts.get("HIGH", 0),
        "medium_display_count": display_counts.get("MEDIUM", 0),
        "low_display_count": display_counts.get("LOW", 0),
        "historical_signal_display_count": display_counts.get("HISTORICAL_SIGNAL", 0),
        "no_signal_display_count": display_counts.get("NO_SIGNAL", 0),
        "readiness_verdict": readiness,
        "built_at": built_at,
    }

    audit_rows: List[Dict[str, object]] = []
    for name in ["CURRENT", "RECENT", "STALE", "HISTORICAL", "NONE"]:
        audit_rows.append(
            {
                "audit_type": "RECENCY_BAND",
                "audit_value": name,
                "count": recency_counts.get(name, 0),
                "details": "",
                "built_at": built_at,
            }
        )
    for name in ["HIGH", "MEDIUM", "LOW", "HISTORICAL_SIGNAL", "NO_SIGNAL"]:
        audit_rows.append(
            {
                "audit_type": "CUSTOMER_DISPLAY_BAND",
                "audit_value": name,
                "count": display_counts.get(name, 0),
                "details": "",
                "built_at": built_at,
            }
        )

    audit_rows.append(
        {
            "audit_type": "WATCH_COUNTS",
            "audit_value": "ORIGINAL_ACTIONABLE_HISTORICAL",
            "count": "",
            "details": f"original={original_watch_count}; actionable={actionable_count}; historical={historical_count}",
            "built_at": built_at,
        }
    )
    audit_rows.append(
        {
            "audit_type": "BENDIGO",
            "audit_value": "ACTIONABLE_WATCH_COUNT",
            "count": bendigo_actionable_count,
            "details": "",
            "built_at": built_at,
        }
    )

    sample_map = {
        "CURRENT": [row for row in output_rows if row["actionable_watch_flag"] == "YES" and row["hidden_gem_recency_band"] == "CURRENT"][:5],
        "RECENT": [row for row in output_rows if row["actionable_watch_flag"] == "YES" and row["hidden_gem_recency_band"] == "RECENT"][:5],
        "STALE": [row for row in output_rows if row["historical_watch_flag"] == "YES" and row["hidden_gem_recency_band"] == "STALE"][:5],
        "HISTORICAL": [row for row in output_rows if row["historical_watch_flag"] == "YES" and row["hidden_gem_recency_band"] == "HISTORICAL"][:5],
    }
    for band_name, rows in sample_map.items():
        for idx, row in enumerate(rows, start=1):
            audit_rows.append(
                {
                    "audit_type": "SAMPLE",
                    "audit_value": f"{band_name}_{idx}",
                    "count": "",
                    "details": (
                        f"{row.get('horse','')} {row.get('track','')} R{row.get('race_no','')} "
                        f"band={row.get('last_hidden_gem_band','')} days={row.get('days_since_hidden_gem','')} "
                        f"display={row.get('customer_display_band','')} trigger={row.get('last_hidden_gem_trigger','')}"
                    ),
                    "built_at": built_at,
                }
            )

    fieldnames = list(output_rows[0].keys()) if output_rows else [
        "current_race_date",
        "track",
        "race_no",
        "horse",
        "actionable_watch_flag",
        "historical_watch_flag",
        "customer_display_band",
    ]
    write_csv(OUTPUT_MAIN, output_rows, fieldnames)
    write_csv(OUTPUT_SUMMARY, [summary_row], list(summary_row.keys()))
    write_csv(OUTPUT_AUDIT, audit_rows, ["audit_type", "audit_value", "count", "details", "built_at"])

    print("EDGEiQ current Hidden Gem feed V1.1 built")
    print(f"Active rows: {active_runner_count}")
    print(f"Original watch count: {original_watch_count}")
    print(f"Actionable watch count: {actionable_count}")
    print(f"Historical watch count: {historical_count}")
    print(f"Bendigo actionable watch count: {bendigo_actionable_count}")
    print(f"Readiness: {readiness}")


if __name__ == "__main__":
    main()
