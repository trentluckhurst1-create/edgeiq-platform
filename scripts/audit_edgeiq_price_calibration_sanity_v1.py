from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORY = DATA / "edgeiq_price_truth_history_v1.csv"
CALIBRATION = DATA / "edgeiq_price_calibration_engine_v1.csv"

OUT = DATA / "edgeiq_price_calibration_sanity_v1.csv"
SUMMARY = DATA / "edgeiq_price_calibration_sanity_v1_summary.csv"

DETAIL_COLUMNS = [
    "section",
    "snapshot_timestamp",
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "result_status",
    "won",
    "history_bucket",
    "edgeiq_price",
    "edgeiq_probability",
    "sportsbet_price",
    "overlay_pct",
    "metric",
    "value",
    "notes",
]

SUMMARY_COLUMNS = ["section", "metric", "value", "notes", "built_at"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def text(row: dict[str, str], *names: str) -> str:
    for name in names:
        if name in row and str(row.get(name, "")).strip():
            return str(row.get(name, "")).strip()
    return ""


def num(value: object) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.upper() in {"NA", "N/A", "NONE", "NULL", "SCR", "FF"}:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def yes(value: object) -> bool:
    return str(value).strip().upper() in {"TRUE", "YES", "Y", "1", "WON", "WINNER"}


def key(row: dict[str, str], include_snapshot: bool = True) -> tuple[str, ...]:
    base = (
        text(row, "race_date", "date"),
        text(row, "track"),
        text(row, "race_no", "race_number"),
        text(row, "horse_key") or re.sub(r"[^A-Z0-9]", "", text(row, "horse").upper()),
    )
    if include_snapshot:
        return (text(row, "snapshot_timestamp"),) + base
    return base


def srow(section: str, metric: str, value: object, notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "notes": notes,
        "built_at": now(),
    }


def drow(row: dict[str, str], section: str, metric: str, value: object, notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "snapshot_timestamp": text(row, "snapshot_timestamp"),
        "race_date": text(row, "race_date", "date"),
        "track": text(row, "track"),
        "race_no": text(row, "race_no", "race_number"),
        "horse": text(row, "horse"),
        "horse_key": text(row, "horse_key"),
        "result_status": text(row, "result_status"),
        "won": text(row, "won"),
        "history_bucket": text(row, "history_bucket"),
        "edgeiq_price": text(row, "edgeiq_price", "rated_price"),
        "edgeiq_probability": text(row, "edgeiq_probability", "rated_probability"),
        "sportsbet_price": text(row, "sportsbet_price"),
        "overlay_pct": text(row, "overlay_pct"),
        "metric": metric,
        "value": value,
        "notes": notes,
    }


def main() -> None:
    rows = read_csv(HISTORY)
    detail: list[dict[str, object]] = []
    summary: list[dict[str, object]] = []

    starters = [r for r in rows if text(r, "result_status").upper() in {"FINAL", "FAILED_TO_FINISH"}]
    scratched = [r for r in rows if text(r, "result_status").upper() == "CONFIRMED_SCRATCHED"]

    no_history = [
        r for r in starters
        if "NO_HISTORY" in text(r, "history_bucket").upper()
        or "BASELINE" in text(r, "history_bucket").upper()
    ]

    edge_prices = [(r, num(text(r, "edgeiq_price", "rated_price"))) for r in starters]
    sb_prices = [(r, num(text(r, "sportsbet_price"))) for r in starters]
    probs = [(r, num(text(r, "edgeiq_probability", "rated_probability"))) for r in starters]

    extreme_100 = [(r, p) for r, p in edge_prices if p is not None and p > 100]
    extreme_500 = [(r, p) for r, p in edge_prices if p is not None and p > 500]
    extreme_1000 = [(r, p) for r, p in edge_prices if p is not None and p > 1000]

    winners = [r for r in starters if yes(text(r, "won"))]
    winners_edge_100 = [(r, num(text(r, "edgeiq_price", "rated_price"))) for r in winners if (num(text(r, "edgeiq_price", "rated_price")) or 0) > 100]
    winners_sb_100 = [(r, num(text(r, "sportsbet_price"))) for r in winners if (num(text(r, "sportsbet_price")) or 0) > 100]

    snapshots = sorted({text(r, "snapshot_timestamp") for r in rows if text(r, "snapshot_timestamp")})
    races = sorted({(text(r, "race_date"), text(r, "track"), text(r, "race_no")) for r in rows})

    summary += [
        srow("overall", "history_rows", len(rows)),
        srow("overall", "starter_rows", len(starters)),
        srow("overall", "scratched_excluded", len(scratched)),
        srow("overall", "snapshots", len(snapshots)),
        srow("overall", "races", len(races)),
        srow("overall", "no_history_starters", len(no_history)),
        srow("extreme_price", "edgeiq_price_gt_100", len(extreme_100)),
        srow("extreme_price", "edgeiq_price_gt_500", len(extreme_500)),
        srow("extreme_price", "edgeiq_price_gt_1000", len(extreme_1000)),
        srow("extreme_winners", "winners_edgeiq_price_gt_100", len(winners_edge_100)),
        srow("extreme_winners", "winners_sportsbet_price_gt_100", len(winners_sb_100)),
    ]

    # History bucket price sanity
    bucket_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in starters:
        bucket_rows[text(r, "history_bucket") or "UNKNOWN"].append(r)

    for bucket, bucket_group in sorted(bucket_rows.items()):
        ep = [num(text(r, "edgeiq_price", "rated_price")) for r in bucket_group]
        sp = [num(text(r, "sportsbet_price")) for r in bucket_group]
        ep = [x for x in ep if x is not None]
        sp = [x for x in sp if x is not None]
        summary.append(srow("history_bucket", f"{bucket}_starter_rows", len(bucket_group)))
        summary.append(srow("history_bucket", f"{bucket}_avg_edgeiq_price", round(sum(ep) / len(ep), 6) if ep else ""))
        summary.append(srow("history_bucket", f"{bucket}_avg_sportsbet_price", round(sum(sp) / len(sp), 6) if sp else ""))

    # Per race probability sums
    by_snapshot_race_all: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    by_snapshot_race_starters: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)

    for r in rows:
        rk = (text(r, "snapshot_timestamp"), text(r, "race_date"), text(r, "track"), text(r, "race_no"))
        by_snapshot_race_all[rk].append(r)
        if text(r, "result_status").upper() in {"FINAL", "FAILED_TO_FINISH"}:
            by_snapshot_race_starters[rk].append(r)

    scratched_in_normalisation_flag = False

    for rk in sorted(by_snapshot_race_all.keys()):
        all_rows = by_snapshot_race_all[rk]
        starter_rows = by_snapshot_race_starters.get(rk, [])
        all_prob = sum(num(text(r, "edgeiq_probability", "rated_probability")) or 0 for r in all_rows)
        starter_prob = sum(num(text(r, "edgeiq_probability", "rated_probability")) or 0 for r in starter_rows)
        scratched_prob = all_prob - starter_prob

        if scratched_prob > 0.000001:
            scratched_in_normalisation_flag = True

        snapshot, race_date, track, race_no = rk
        summary.append(srow(
            "race_probability",
            f"{snapshot}|{race_date}|{track}|R{race_no}|all_runner_probability_sum",
            round(all_prob, 8),
        ))
        summary.append(srow(
            "race_probability",
            f"{snapshot}|{race_date}|{track}|R{race_no}|starter_probability_sum",
            round(starter_prob, 8),
        ))
        summary.append(srow(
            "race_probability",
            f"{snapshot}|{race_date}|{track}|R{race_no}|scratched_probability_sum",
            round(scratched_prob, 8),
        ))

    summary.append(srow(
        "normalisation",
        "scratched_included_in_probability_normalisation",
        "TRUE" if scratched_in_normalisation_flag else "FALSE",
        "TRUE means settled scratchings had non-zero pre-race probabilities in the all-runner book."
    ))

    # Snapshot weighted vs unique race calibration
    snapshot_expected = sum(p or 0 for _, p in probs)
    snapshot_winners = sum(1 for r in starters if yes(text(r, "won")))

    latest_by_runner: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for r in starters:
        latest_by_runner[key(r, include_snapshot=False)] = r

    unique_rows = list(latest_by_runner.values())
    unique_expected = sum(num(text(r, "edgeiq_probability", "rated_probability")) or 0 for r in unique_rows)
    unique_winners = sum(1 for r in unique_rows if yes(text(r, "won")))

    summary += [
        srow("calibration_weighting", "snapshot_weighted_rows", len(starters)),
        srow("calibration_weighting", "snapshot_weighted_expected_winners", round(snapshot_expected, 6)),
        srow("calibration_weighting", "snapshot_weighted_actual_winners", snapshot_winners),
        srow("calibration_weighting", "unique_runner_rows_latest_snapshot", len(unique_rows)),
        srow("calibration_weighting", "unique_race_expected_winners_latest_snapshot", round(unique_expected, 6)),
        srow("calibration_weighting", "unique_race_winners", unique_winners),
        srow(
            "calibration_weighting",
            "duplicate_snapshot_inflation_detected",
            "TRUE" if len(snapshots) > 1 and snapshot_winners > unique_winners else "FALSE",
            "Multiple snapshots of the same races repeat the same winners and should not be treated as independent races."
        ),
    ]

    # Detail rows for extremes and winners
    for r, p in extreme_100:
        detail.append(drow(r, "extreme_price", "edgeiq_price_gt_100", p))
    for r, p in winners_edge_100:
        detail.append(drow(r, "extreme_winner", "winner_edgeiq_price_gt_100", p))
    for r, p in winners_sb_100:
        detail.append(drow(r, "extreme_winner", "winner_sportsbet_price_gt_100", p))

    status = "CALIBRATION_SANITY_WARN"
    notes = []
    if scratched_in_normalisation_flag:
        notes.append("Scratched runners carried non-zero probabilities in the all-runner price book.")
    if len(snapshots) > 1:
        notes.append("Repeated snapshots inflate winner counts if treated as independent observations.")
    if len(unique_rows) < 500:
        notes.append("Unique starter sample is very small.")
    if not notes:
        status = "CALIBRATION_SANITY_PASS"

    summary.append(srow("status", "calibration_sanity_status", status, " | ".join(notes)))

    write_csv(OUT, detail, DETAIL_COLUMNS)
    write_csv(SUMMARY, summary, SUMMARY_COLUMNS)

    print("=" * 96)
    print("EDGEIQ PRICE CALIBRATION SANITY V1")
    print("=" * 96)
    print(f"wrote: {OUT}")
    print(f"wrote: {SUMMARY}")
    print("")
    for row in summary:
        if row["section"] in {"overall", "calibration_weighting", "normalisation", "status", "extreme_price", "extreme_winners"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print("=" * 96)


if __name__ == "__main__":
    main()
