#!/usr/bin/env python3
"""Build Issue #10 governed pre-2022 all-runner PIT partition.

This script deliberately avoids the mixed-year consolidated warehouse because
that file is known to contain sealed 2025-2026 rows. It only reads explicitly
selected monthly GraphQL result files whose filename year is <= 2021.

No model fitting, scoring, market features, production writes, or sealed-year
file access occur here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable


SOURCE_PATTERN = re.compile(r"^edgeiq_graphql_[a-z]+_(\d{4})_results_v1\.csv$", re.I)
JUMP_RE = re.compile(r"HDLE|HURDLE|STPL|STEEP|CHASE|JUMP|JMPR", re.I)
PICNIC_RE = re.compile(r"PICNIC|(?:^|[\s-])PIC(?:-|\s|$)", re.I)
FORBIDDEN_TERMS = (
    "sp",
    "bsp",
    "starting_price",
    "odds",
    "price",
    "market",
    "bet",
    "stake",
    "return",
)

REQUIRED_COLUMNS = (
    "race_date",
    "race_id",
    "runner_id",
    "race_class",
    "horse",
    "trainer",
    "jockey",
    "finish",
)

OPTIONAL_COLUMNS = (
    "track",
    "venue_name",
    "state",
    "race_no",
    "race_status",
    "race_name",
    "distance",
    "race_time_utc",
    "track_condition",
    "track_rating",
    "rail_position",
    "weather",
    "runner_id",
    "race_entry_number",
    "horse_code",
    "trainer_code",
    "jockey_code",
    "barrier",
    "live_barrier",
    "weight",
    "scratched",
    "finish_abv",
    "margin",
    "margin_l",
    "gear_changes",
    "source",
)

RUNNER_OUTPUT_COLUMNS = (
    "race_date",
    "year",
    "source_race_id",
    "source_runner_id",
    "race_key",
    "runner_key",
    "horse_key",
    "horse_key_method",
    "horse",
    "horse_code",
    "trainer_key",
    "trainer_key_method",
    "trainer",
    "trainer_code",
    "jockey_key",
    "jockey_key_method",
    "jockey",
    "jockey_code",
    "track",
    "venue_name",
    "state",
    "race_no",
    "race_status",
    "race_name",
    "race_class",
    "race_type_classification",
    "distance_metres",
    "race_time_utc",
    "track_condition",
    "track_rating",
    "rail_position",
    "weather",
    "race_entry_number",
    "barrier",
    "live_barrier",
    "weight",
    "scratched",
    "finish_position",
    "winner",
    "top3",
    "margin_lengths",
    "gear_changes",
    "source_file",
    "race_eligible",
    "race_exclusion_reasons",
)

PIT_OUTPUT_COLUMNS = (
    "race_date",
    "year",
    "race_key",
    "runner_key",
    "horse_key",
    "trainer_key",
    "jockey_key",
    "y",
    "field_size",
    "barrier",
    "barrier_position_pct",
    "distance_metres",
    "weight",
    "horse_prior_starts",
    "horse_prior_wins",
    "horse_prior_top3",
    "horse_prior_win_rate",
    "horse_prior_top3_rate",
    "horse_prior_finish_mean",
    "horse_days_since_last_run",
    "horse_no_prior_history",
    "trainer_id_missing",
    "trainer_prior_starts",
    "trainer_prior_wins",
    "trainer_prior_top3",
    "trainer_prior_win_rate",
    "trainer_prior_top3_rate",
    "trainer_no_prior_history",
    "jockey_id_missing",
    "jockey_prior_starts",
    "jockey_prior_wins",
    "jockey_prior_top3",
    "jockey_prior_win_rate",
    "jockey_prior_top3_rate",
    "jockey_no_prior_history",
)


@dataclass
class EntityStats:
    starts: int = 0
    wins: int = 0
    top3: int = 0
    finish_sum: float = 0.0
    finish_n: int = 0
    last_date: date | None = None

    def snapshot(self, prefix: str, target_date: date) -> dict[str, object]:
        win_rate = self.wins / self.starts if self.starts else ""
        top3_rate = self.top3 / self.starts if self.starts else ""
        finish_mean = self.finish_sum / self.finish_n if self.finish_n else ""
        days_since = (target_date - self.last_date).days if self.last_date else ""
        return {
            f"{prefix}_prior_starts": self.starts,
            f"{prefix}_prior_wins": self.wins,
            f"{prefix}_prior_top3": self.top3,
            f"{prefix}_prior_win_rate": win_rate,
            f"{prefix}_prior_top3_rate": top3_rate,
            f"{prefix}_prior_finish_mean": finish_mean,
            f"{prefix}_days_since_last_run": days_since,
            f"{prefix}_no_prior_history": int(self.starts == 0),
        }

    def update(self, row: dict) -> None:
        self.starts += 1
        self.wins += int(row["winner"] == 1)
        self.top3 += int(row["top3"] == 1)
        if row["finish_position"] is not None:
            self.finish_sum += float(row["finish_position"])
            self.finish_n += 1
        d = row["race_date_obj"]
        if self.last_date is None or d > self.last_date:
            self.last_date = d


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalise_key(value: object) -> str:
    text = clean(value).upper()
    return re.sub(r"[^A-Z0-9]+", "_", text).strip("_")


def parse_date(value: object) -> date | None:
    try:
        return date.fromisoformat(clean(value)[:10])
    except ValueError:
        return None


def parse_float(value: object) -> float | None:
    text = clean(value)
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def parse_bool(value: object) -> bool:
    return clean(value).lower() in {"1", "true", "yes", "y", "scratched"}


def classify_race_type(race_class: object) -> str:
    text = clean(race_class)
    if not text:
        return "UNCLASSIFIED"
    if JUMP_RE.search(text):
        return "JUMPS"
    if PICNIC_RE.search(text):
        return "PICNIC"
    return "FLAT_PROVISIONAL"


def is_market_column(column: str) -> bool:
    lower = column.lower()
    return lower in {"sp", "bsp"} or any(term in lower for term in FORBIDDEN_TERMS)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def select_source_files(source_dir: Path, cutoff_year: int) -> list[Path]:
    files = []
    for path in source_dir.glob("edgeiq_graphql_*_results_v1.csv"):
        m = SOURCE_PATTERN.match(path.name)
        if not m:
            continue
        year = int(m.group(1))
        if year < cutoff_year:
            files.append(path)
    return sorted(files, key=lambda p: p.name.lower())


def source_file_inventory(source_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(source_dir.glob("edgeiq_graphql_*_results_v1.csv"), key=lambda p: p.name.lower()):
        m = SOURCE_PATTERN.match(path.name)
        rows.append(
            {
                "file_name": path.name,
                "year": int(m.group(1)) if m else "",
                "bytes": path.stat().st_size,
                "selected_for_pre2022_export": bool(m and int(m.group(1)) <= 2021),
                "empty_like": path.stat().st_size <= 100,
            }
        )
    return rows


def key_with_method(code: str, label: str, prefix: str) -> tuple[str, str]:
    code_key = normalise_key(code)
    if code_key:
        return f"{prefix}CODE_{code_key}", "CODE"
    label_key = normalise_key(label)
    if label_key:
        return f"{prefix}NAME_{label_key}", "NORMALISED_NAME"
    return "", "MISSING"


def race_reason(rows: list[dict]) -> list[str]:
    reasons = []
    dates = {r["race_date"] for r in rows}
    if len(dates) != 1:
        reasons.append("RACE_ID_DATE_COLLISION")
    types = {r["race_type_classification"] for r in rows}
    if types != {"FLAT_PROVISIONAL"}:
        reasons.append("NOT_FLAT_PROVISIONAL")
    starters = [r for r in rows if not r["scratched"]]
    if not starters:
        reasons.append("NO_STARTERS")
    runner_keys = [r["runner_key"] for r in starters]
    if len(runner_keys) != len(set(runner_keys)):
        reasons.append("DUPLICATE_RUNNER_KEY_IN_RACE")
    winners = [r for r in starters if r["winner"] == 1]
    if len(winners) != 1:
        reasons.append("NOT_EXACTLY_ONE_WINNER")
    if any(not r["horse_key"] for r in starters):
        reasons.append("MISSING_HORSE_IDENTITY")
    return reasons


def write_csv(path: Path, rows: Iterable[dict], fieldnames: Iterable[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def compute_strict_prior_features(rows: list[dict]) -> list[dict]:
    """Compute entity aggregates using only dates strictly before target date."""
    horse_stats: dict[str, EntityStats] = defaultdict(EntityStats)
    trainer_stats: dict[str, EntityStats] = defaultdict(EntityStats)
    jockey_stats: dict[str, EntityStats] = defaultdict(EntityStats)
    out = []
    rows_sorted = sorted(rows, key=lambda r: (r["race_date_obj"], r["race_key"], r["runner_key"]))
    by_date: dict[date, list[dict]] = defaultdict(list)
    for row in rows_sorted:
        by_date[row["race_date_obj"]].append(row)
    for d in sorted(by_date):
        date_rows = by_date[d]
        for row in date_rows:
            field_size = row["field_size"]
            barrier = row["barrier"]
            barrier_pct = ""
            if barrier is not None and field_size and field_size > 1:
                barrier_pct = (float(barrier) - 1.0) / (field_size - 1.0)
            hs = horse_stats[row["horse_key"]].snapshot("horse", d)
            trainer_missing = int(not row["trainer_key"])
            jockey_missing = int(not row["jockey_key"])
            ts = trainer_stats[row["trainer_key"]].snapshot("trainer", d) if row["trainer_key"] else {
                "trainer_prior_starts": 0,
                "trainer_prior_wins": 0,
                "trainer_prior_top3": 0,
                "trainer_prior_win_rate": "",
                "trainer_prior_top3_rate": "",
                "trainer_no_prior_history": 0,
            }
            js = jockey_stats[row["jockey_key"]].snapshot("jockey", d) if row["jockey_key"] else {
                "jockey_prior_starts": 0,
                "jockey_prior_wins": 0,
                "jockey_prior_top3": 0,
                "jockey_prior_win_rate": "",
                "jockey_prior_top3_rate": "",
                "jockey_no_prior_history": 0,
            }
            feature_row = {
                "race_date": row["race_date"],
                "year": row["year"],
                "race_key": row["race_key"],
                "runner_key": row["runner_key"],
                "horse_key": row["horse_key"],
                "trainer_key": row["trainer_key"],
                "jockey_key": row["jockey_key"],
                "y": row["winner"],
                "field_size": field_size,
                "barrier": barrier if barrier is not None else "",
                "barrier_position_pct": barrier_pct,
                "distance_metres": row["distance_metres"] if row["distance_metres"] is not None else "",
                "weight": row["weight"] if row["weight"] is not None else "",
                "trainer_id_missing": trainer_missing,
                "jockey_id_missing": jockey_missing,
                **hs,
                **ts,
                **js,
            }
            out.append(feature_row)
        for row in date_rows:
            horse_stats[row["horse_key"]].update(row)
            if row["trainer_key"]:
                trainer_stats[row["trainer_key"]].update(row)
            if row["jockey_key"]:
                jockey_stats[row["jockey_key"]].update(row)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        default=r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\data",
        help="Directory containing edgeiq_graphql_*_results_v1.csv monthly files.",
    )
    parser.add_argument(
        "--out",
        default="outputs/research/issue10_pre2022_partition",
        help="Output directory for local partition artifacts.",
    )
    parser.add_argument("--cutoff-date", default="2022-01-01")
    parser.add_argument(
        "--allow-local-pre2022-monthly-export",
        action="store_true",
        help="Required acknowledgement: read only filename-year <=2021 monthly files, never the mixed warehouse.",
    )
    args = parser.parse_args()

    if not args.allow_local_pre2022_monthly_export:
        raise SystemExit("STOP: pass --allow-local-pre2022-monthly-export to use the documented monthly-file partition method")

    source_dir = Path(args.source_dir)
    out_dir = Path(args.out)
    cutoff = date.fromisoformat(args.cutoff_date)
    if cutoff != date(2022, 1, 1):
        raise SystemExit("STOP: Issue #10 permits only the fixed 2022-01-01 cutoff")
    if not source_dir.is_dir():
        raise SystemExit(f"STOP: source directory not found: {source_dir}")

    selected = select_source_files(source_dir, cutoff.year)
    if not selected:
        raise SystemExit("STOP: no <=2021 monthly GraphQL source files found")
    if any(int(SOURCE_PATTERN.match(p.name).group(1)) >= cutoff.year for p in selected):
        raise SystemExit("STOP: selected file set contains >=2022 source")

    out_dir.mkdir(parents=True, exist_ok=True)
    source_inventory = source_file_inventory(source_dir)
    write_csv(out_dir / "ISSUE10_SOURCE_FILE_INVENTORY.csv", source_inventory, source_inventory[0].keys())

    selected_manifest_rows = []
    skipped_source_files = []
    race_rows: dict[str, list[dict]] = defaultdict(list)
    row_quarantine = []
    row_counts_by_year = Counter()
    source_rows = 0
    post_cutoff_in_selected = 0
    invalid_date_rows = 0
    headers_seen = set()

    allowed_columns = set(REQUIRED_COLUMNS) | set(OPTIONAL_COLUMNS)
    if any(is_market_column(c) for c in allowed_columns):
        raise SystemExit("STOP: requested output column set includes market-like column")

    for file_index, path in enumerate(selected, start=1):
        file_year = int(SOURCE_PATTERN.match(path.name).group(1))
        file_bytes = path.stat().st_size
        file_hash = sha256_file(path)
        with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            if len(header) != len(set(header)):
                raise SystemExit(f"STOP: duplicate header columns in {path.name}")
            missing = [c for c in REQUIRED_COLUMNS if c not in header]
            if missing:
                if file_bytes <= 100:
                    skipped_source_files.append(
                        {
                            "file_name": path.name,
                            "year": file_year,
                            "bytes": file_bytes,
                            "sha256": file_hash,
                            "skip_reason": "EMPTY_LIKE_OR_SCHEMALESS_MONTHLY_FILE",
                            "missing_required_columns": ",".join(missing),
                        }
                    )
                    selected_manifest_rows.append(
                        {
                            "file_name": path.name,
                            "year": file_year,
                            "bytes": file_bytes,
                            "sha256": file_hash,
                            "status": "SKIPPED_EMPTY_LIKE",
                        }
                    )
                    continue
                raise SystemExit(f"STOP: missing required columns in {path.name}: {','.join(missing)}")
            selected_manifest_rows.append(
                {
                    "file_name": path.name,
                    "year": file_year,
                    "bytes": file_bytes,
                    "sha256": file_hash,
                    "status": "READ",
                }
            )
            headers_seen.add(tuple(header))
            for row_number, row in enumerate(reader, start=2):
                source_rows += 1
                d = parse_date(row.get("race_date"))
                if d is None:
                    invalid_date_rows += 1
                    row_quarantine.append({"source_file": path.name, "row_number": row_number, "reason": "INVALID_RACE_DATE"})
                    continue
                if d >= cutoff:
                    post_cutoff_in_selected += 1
                    row_quarantine.append({"source_file": path.name, "row_number": row_number, "reason": "POST_CUTOFF_ROW_IN_SELECTED_SOURCE"})
                    continue
                year = d.year
                row_counts_by_year[year] += 1
                race_id = clean(row.get("race_id"))
                runner_id = clean(row.get("runner_id"))
                horse_key, horse_method = key_with_method(row.get("horse_code"), row.get("horse"), "HORSE_")
                trainer_key, trainer_method = key_with_method(row.get("trainer_code"), row.get("trainer"), "TRAINER_")
                jockey_key, jockey_method = key_with_method(row.get("jockey_code"), row.get("jockey"), "JOCKEY_")
                if not race_id or not runner_id or not horse_key:
                    row_quarantine.append(
                        {
                            "source_file": path.name,
                            "row_number": row_number,
                            "reason": "MISSING_CORE_IDENTITY",
                            "race_id": race_id,
                            "runner_id": runner_id,
                            "horse": clean(row.get("horse")),
                            "horse_code": clean(row.get("horse_code")),
                        }
                    )
                    continue
                finish_position = parse_float(row.get("finish"))
                scratched = parse_bool(row.get("scratched"))
                runner = {
                    "race_date_obj": d,
                    "race_date": d.isoformat(),
                    "year": year,
                    "source_race_id": race_id,
                    "source_runner_id": runner_id,
                    "race_key": race_id,
                    "runner_key": runner_id,
                    "horse_key": horse_key,
                    "horse_key_method": horse_method,
                    "horse": clean(row.get("horse")),
                    "horse_code": clean(row.get("horse_code")),
                    "trainer_key": trainer_key,
                    "trainer_key_method": trainer_method,
                    "trainer": clean(row.get("trainer")),
                    "trainer_code": clean(row.get("trainer_code")),
                    "jockey_key": jockey_key,
                    "jockey_key_method": jockey_method,
                    "jockey": clean(row.get("jockey")),
                    "jockey_code": clean(row.get("jockey_code")),
                    "track": clean(row.get("track")),
                    "venue_name": clean(row.get("venue_name")),
                    "state": clean(row.get("state")),
                    "race_no": clean(row.get("race_no")),
                    "race_status": clean(row.get("race_status")),
                    "race_name": clean(row.get("race_name")),
                    "race_class": clean(row.get("race_class")),
                    "race_type_classification": classify_race_type(row.get("race_class")),
                    "distance_metres": parse_float(row.get("distance")),
                    "race_time_utc": clean(row.get("race_time_utc")),
                    "track_condition": clean(row.get("track_condition")),
                    "track_rating": clean(row.get("track_rating")),
                    "rail_position": clean(row.get("rail_position")),
                    "weather": clean(row.get("weather")),
                    "race_entry_number": clean(row.get("race_entry_number")),
                    "barrier": parse_float(row.get("barrier")),
                    "live_barrier": parse_float(row.get("live_barrier")),
                    "weight": parse_float(row.get("weight")),
                    "scratched": int(scratched),
                    "finish_position": finish_position,
                    "winner": int((not scratched) and finish_position == 1.0),
                    "top3": int((not scratched) and finish_position is not None and finish_position <= 3.0),
                    "margin_lengths": parse_float(row.get("margin_l")),
                    "gear_changes": clean(row.get("gear_changes")),
                    "source_file": path.name,
                }
                race_rows[race_id].append(runner)

    if post_cutoff_in_selected:
        raise SystemExit("STOP: selected <=2021 source files contained post-cutoff rows")

    write_csv(out_dir / "ISSUE10_SELECTED_SOURCE_FILES.csv", selected_manifest_rows, selected_manifest_rows[0].keys())
    if skipped_source_files:
        write_csv(out_dir / "ISSUE10_SKIPPED_SOURCE_FILES.csv", skipped_source_files, skipped_source_files[0].keys())
    else:
        write_csv(out_dir / "ISSUE10_SKIPPED_SOURCE_FILES.csv", [], ("file_name", "year", "bytes", "sha256", "skip_reason", "missing_required_columns"))
    if row_quarantine:
        write_csv(out_dir / "ISSUE10_ROW_QUARANTINE.csv", row_quarantine, sorted({k for r in row_quarantine for k in r}))
    else:
        write_csv(out_dir / "ISSUE10_ROW_QUARANTINE.csv", [], ("source_file", "row_number", "reason"))

    runner_rows = []
    eligible_rows = []
    race_audit = []
    race_exclusion_counts = Counter()
    field_sizes = {}
    for race_key in sorted(race_rows):
        rows = race_rows[race_key]
        reasons = race_reason(rows)
        eligible = not reasons
        starters = [r for r in rows if not r["scratched"]]
        field_sizes[race_key] = len(starters)
        for reason in reasons:
            race_exclusion_counts[reason] += 1
        race_audit.append(
            {
                "race_key": race_key,
                "race_date": rows[0]["race_date"],
                "year": rows[0]["year"],
                "race_type_classification": "|".join(sorted({r["race_type_classification"] for r in rows})),
                "source_rows": len(rows),
                "starters": len(starters),
                "scratched_rows": sum(r["scratched"] for r in rows),
                "winner_count": sum(r["winner"] for r in starters),
                "duplicate_runner_keys": len([k for k, v in Counter(r["runner_key"] for r in starters).items() if v > 1]),
                "race_eligible": int(eligible),
                "race_exclusion_reasons": "|".join(reasons),
            }
        )
        for row in rows:
            row["race_eligible"] = int(eligible)
            row["race_exclusion_reasons"] = "|".join(reasons)
            runner_rows.append(row)
            if eligible and not row["scratched"]:
                row["field_size"] = field_sizes[race_key]
                eligible_rows.append(row)

    pit_rows = compute_strict_prior_features(eligible_rows)

    runner_count = write_csv(out_dir / "ISSUE10_PRE2022_RUNNER_PARTITION.csv", runner_rows, RUNNER_OUTPUT_COLUMNS)
    eligible_count = write_csv(out_dir / "ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv", pit_rows, PIT_OUTPUT_COLUMNS)
    write_csv(out_dir / "ISSUE10_RACE_AUDIT.csv", race_audit, race_audit[0].keys())

    year_summary = []
    for year in sorted(row_counts_by_year):
        races = [r for r in race_audit if int(r["year"]) == year]
        eligible_races = [r for r in races if int(r["race_eligible"]) == 1]
        year_summary.append(
            {
                "year": year,
                "source_rows": row_counts_by_year[year],
                "races": len(races),
                "eligible_races": len(eligible_races),
                "eligible_starters": sum(int(r["starters"]) for r in eligible_races),
                "missing_or_sparse_flag": year in {2011, 2016, 2017},
            }
        )
    write_csv(out_dir / "ISSUE10_YEAR_COUNTS.csv", year_summary, year_summary[0].keys())

    manifest = {
        "status": "PASS_REVIEW_READY_NOT_MODEL_AUTHORISED",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model_fitting": "NO",
        "model_scoring": "NO",
        "market_access": "NO",
        "sealed_2025_2026_file_access": "NO",
        "source_method": "Monthly GraphQL files selected by filename year <= 2021; consolidated mixed-year warehouse not scanned.",
        "source_dir": str(source_dir),
        "cutoff_date": cutoff.isoformat(),
        "source_files_selected": len(selected),
        "source_files_read": sum(1 for r in selected_manifest_rows if r["status"] == "READ"),
        "source_files_skipped_empty_like": len(skipped_source_files),
        "headers_seen": len(headers_seen),
        "source_rows_read": source_rows,
        "invalid_date_rows": invalid_date_rows,
        "post_cutoff_rows_in_selected_files": post_cutoff_in_selected,
        "runner_partition_rows": runner_count,
        "eligible_pit_rows": eligible_count,
        "races_total": len(race_audit),
        "eligible_races": sum(int(r["race_eligible"]) for r in race_audit),
        "race_exclusion_counts": dict(sorted(race_exclusion_counts.items())),
        "year_counts": year_summary,
        "missing_year_flags": {
            "2011": "all monthly files empty-like",
            "2017": "all monthly files empty-like",
            "2016": "only January/February non-empty in source inventory",
        },
        "identity_status": {
            "runner_identity": "PASS_INTERNAL_SOURCE_RACE_ID_RUNNER_ID_UNIQUENESS_FOR_ELIGIBLE_RACES",
            "horse_identity": "SOURCE_HORSE_CODE_ELSE_NORMALISED_NAME; CANONICAL_EDGEIQ_HORSE_ID_NOT_PROVEN",
            "trainer_identity": "SOURCE_TRAINER_CODE_ELSE_NORMALISED_NAME; MISSING_ID_DISTINGUISHED",
            "jockey_identity": "SOURCE_JOCKEY_CODE_ELSE_NORMALISED_NAME; MISSING_ID_DISTINGUISHED",
        },
        "pit_status": "STRICT_RACE_DATE_LT_TARGET_DATE_ENTITY_AGGREGATES_BUILT",
        "permissible_use_status": "REQUIRES_GROK_AND_OWNER_REVIEW_BEFORE_MODEL_USE",
        "large_outputs_not_for_commit": [
            "ISSUE10_PRE2022_RUNNER_PARTITION.csv",
            "ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv",
        ],
        "outputs": {
            "runner_partition": str(out_dir / "ISSUE10_PRE2022_RUNNER_PARTITION.csv"),
            "pit_feature_matrix": str(out_dir / "ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv"),
            "race_audit": str(out_dir / "ISSUE10_RACE_AUDIT.csv"),
            "year_counts": str(out_dir / "ISSUE10_YEAR_COUNTS.csv"),
            "row_quarantine": str(out_dir / "ISSUE10_ROW_QUARANTINE.csv"),
        },
    }
    for key, rel in {
        "runner_partition_sha256": "ISSUE10_PRE2022_RUNNER_PARTITION.csv",
        "pit_feature_matrix_sha256": "ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv",
        "race_audit_sha256": "ISSUE10_RACE_AUDIT.csv",
        "year_counts_sha256": "ISSUE10_YEAR_COUNTS.csv",
    }.items():
        manifest[key] = sha256_file(out_dir / rel)

    (out_dir / "ISSUE10_BUILD_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("status", "source_rows_read", "eligible_races", "eligible_pit_rows", "permissible_use_status")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
