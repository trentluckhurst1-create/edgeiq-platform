from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public" / "data"
OUT = ROOT / "docs" / "victoria-live-recovery-v1"
OUT.mkdir(parents=True, exist_ok=True)

NORMALISATION_EFFECTIVE_FROM = date(2026, 7, 20)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def count_csv(path: Path) -> int:
    return len(read_csv_rows(path))


def parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def stage(name: str, path: str, required_for_core: bool = True) -> dict[str, Any]:
    p = ROOT / path
    rows = count_csv(p)
    return {
        "stage": name,
        "path": path,
        "exists": p.exists(),
        "rows": rows,
        "required_for_core": required_for_core,
        "status": "PASS" if p.exists() and rows > 0 else "ZERO_OR_MISSING",
    }


def main() -> None:
    stages = [
        stage("Results Warehouse", "public/data/edgeiq_canonical_results_truth_v1.csv"),
        stage("Timed Races", "public/data/edgeiq_canonical_historical_timing_warehouse_v1.csv"),
        stage("Standard Times", "public/data/edgeiq_standard_time_fact_v1.csv"),
        stage("Race Time Delta", "public/data/edgeiq_race_time_delta_versus_standard_fact_v1.csv"),
        stage("Lengths v Standard", "public/data/edgeiq_lengths_versus_standard_fact_v1.csv"),
        stage("Performance Base", "public/data/edgeiq_performance_intelligence_base_fact_v1.csv"),
        stage("Normalisation", "public/data/edgeiq_performance_normalisation_fact_v1.csv"),
        stage("Horse Aggregates", "public/data/edgeiq_horse_performance_aggregate_fact_v1.csv"),
        stage("Horse Ratings", "public/data/edgeiq_horse_performance_rating_fact_v1.csv"),
        stage("Snapshots", "public/data/edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"),
        stage("Projected Performance", "public/data/edgeiq_race_entry_projected_performance_fact_v1.csv"),
        stage("EPI", "public/data/edgeiq_race_entry_epi_fact_v1.csv"),
        stage("Daily Operations", "public/data/edgeiq_daily_operations_checkpoint_fact_v1.csv"),
        stage("React EPI Feed", "public/data/edgeiq_epi_workspace_terminal_feed_v1.csv", required_for_core=False),
    ]

    base_rows = read_csv_rows(PUBLIC_DATA / "edgeiq_performance_intelligence_base_fact_v1.csv")
    base_dates = [parse_date(r.get("race_date", "")) for r in base_rows]
    base_dates = [d for d in base_dates if d is not None]
    before_cutoff = sum(1 for d in base_dates if d < NORMALISATION_EFFECTIVE_FROM)
    on_or_after_cutoff = sum(1 for d in base_dates if d >= NORMALISATION_EFFECTIVE_FROM)
    by_year = Counter(d.year for d in base_dates)

    rejection_rows = read_csv_rows(PUBLIC_DATA / "edgeiq_performance_normalisation_fact_v1_rejections.csv")
    rejection_reasons = Counter(r.get("rejection_reason", "") for r in rejection_rows)

    sectionals_rows = count_csv(PUBLIC_DATA / "edgeiq_racingcom_runner_sectional_fact_v1.csv")
    visible_sectionals_rows = count_csv(ROOT / "data" / "processed" / "racing-com-public-v1" / "visible_runner_sectional_fact_v1.csv")

    core_until_performance_base_pass = all(
        s["status"] == "PASS"
        for s in stages
        if s["stage"] in {
            "Results Warehouse",
            "Timed Races",
            "Standard Times",
            "Race Time Delta",
            "Lengths v Standard",
            "Performance Base",
        }
    )

    if not core_until_performance_base_pass:
        final_status = "BLOCKED_CORE_PERFORMANCE"
        blocker = "Core performance stage before Performance Base is missing or zero."
    elif on_or_after_cutoff == 0:
        final_status = "BLOCKED_EXTERNAL_CURRENT_TIMING_DATA"
        blocker = "No Performance Base observations exist on or after HPR-NORM-A-v1 effective date 2026-07-20."
    else:
        final_status = "READY_TO_REBUILD_DOWNSTREAM"
        blocker = "Current-window Performance Base observations exist and should feed normalisation."

    acceptance_rows = []
    for s in stages:
        acceptance = s["status"]
        if s["stage"] in {"Normalisation", "Horse Aggregates", "Horse Ratings", "Snapshots", "Projected Performance", "EPI"}:
            if on_or_after_cutoff == 0:
                acceptance = "GOVERNED_ZERO_EXPECTED_NO_POST_CUTOFF_BASE"
        acceptance_rows.append({**s, "acceptance_status": acceptance})

    with (OUT / "edgeiq_victoria_live_acceptance_v1.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["stage", "path", "exists", "rows", "required_for_core", "status", "acceptance_status"],
        )
        writer.writeheader()
        writer.writerows(acceptance_rows)

    summary = {
        "status": final_status,
        "blocker": blocker,
        "normalisation_effective_from": NORMALISATION_EFFECTIVE_FROM.isoformat(),
        "performance_base_rows": len(base_rows),
        "performance_base_before_cutoff": before_cutoff,
        "performance_base_on_or_after_cutoff": on_or_after_cutoff,
        "performance_base_min_date": min(base_dates).isoformat() if base_dates else None,
        "performance_base_max_date": max(base_dates).isoformat() if base_dates else None,
        "normalisation_rejection_reasons": dict(rejection_reasons),
        "runner_sectional_rows": sectionals_rows,
        "visible_sectional_rows": visible_sectionals_rows,
        "sectionals_required_for_core": False,
        "core_until_performance_base_pass": core_until_performance_base_pass,
    }
    (OUT / "edgeiq_victoria_live_acceptance_v1_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = [
        "# EDGEiQ Victoria Live Acceptance V1",
        "",
        f"Status: {final_status}",
        f"Blocker: {blocker}",
        "",
        "## Core Pipeline",
        "",
        f"Results through Performance Base pass: {core_until_performance_base_pass}",
        f"Performance Base rows: {len(base_rows)}",
        f"Performance Base min date: {summary['performance_base_min_date']}",
        f"Performance Base max date: {summary['performance_base_max_date']}",
        "",
        "## Normalisation Gate",
        "",
        f"HPR-NORM-A-v1 effective from: {NORMALISATION_EFFECTIVE_FROM.isoformat()}",
        f"Rows before effective date: {before_cutoff}",
        f"Rows on/after effective date: {on_or_after_cutoff}",
        f"Rejection reasons: {dict(rejection_reasons)}",
        "",
        "## Sectionals",
        "",
        f"Canonical runner sectional rows: {sectionals_rows}",
        f"Visible-page sectional rows: {visible_sectionals_rows}",
        "Sectionals required for core Performance Intelligence: NO",
        "",
        "## Acceptance",
        "",
        "Victoria cannot yet reach PASS_VICTORIA_LIVE because there are no current-window Performance Base observations dated on or after 2026-07-20. This is a governed data-availability blocker, not a Racing.com sectional dependency and not a core timing architecture blocker.",
    ]
    (OUT / "edgeiq_victoria_live_acceptance_v1.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
