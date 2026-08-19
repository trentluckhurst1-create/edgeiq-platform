from pathlib import Path
import csv
from collections import Counter
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DRY_RUN = DATA / "edgeiq_active_build_chain_dry_run_v1.csv"
GOVERNED = DATA / "edgeiq_live_runner_board_governed_v1.csv"
GEAR = DATA / "edgeiq_gear_signal_engine_v1.csv"
MARKET = DATA / "edgeiq_market_alignment_engine_v1.csv"

OUT = DATA / "edgeiq_current_source_blocker_register_v1.csv"
SUMMARY = DATA / "edgeiq_current_source_blocker_register_v1_summary.csv"
REPORT = DATA / "edgeiq_current_source_blocker_register_v1_report.txt"
GEAR_PLAN = DATA / "EDGEIQ_CURRENT_GEAR_REFRESH_PLAN_V2.txt"


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        keys = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def unique_meetings(rows):
    seen = []
    for r in rows:
        race_date = (r.get("race_date") or r.get("current_race_date") or "").strip()
        track = (r.get("track") or "").strip().upper()
        if race_date and track and (race_date, track) not in seen:
            seen.append((race_date, track))
    return seen


def count_value(rows, column, value):
    return sum(1 for r in rows if str(r.get(column, "")).strip().upper() == value.upper())


def add_blocker(rows, blocker_id, system_area, severity, current_status, impact, safe_fallback, resolution_path, rerun_sequence, production_risk):
    rows.append({
        "blocker_id": blocker_id,
        "system_area": system_area,
        "severity": severity,
        "current_status": current_status,
        "impact": impact,
        "safe_fallback": safe_fallback,
        "resolution_path": resolution_path,
        "rerun_sequence": rerun_sequence,
        "production_risk": production_risk,
    })


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    governed = read_csv(GOVERNED)
    gear = read_csv(GEAR)
    market = read_csv(MARKET)
    dry = read_csv(DRY_RUN)
    blockers = []

    meetings = unique_meetings(governed)
    meeting_text = "; ".join([f"{d} {t}" for d, t in meetings])

    gear_no_count = count_value(gear, "gear_signal_band", "NO_GEAR") if gear else 0
    gear_rows = len(gear)
    gear_all_no = gear_rows > 0 and gear_no_count == gear_rows
    market_no_count = count_value(market, "market_alignment_band", "NO_MARKET_DATA") if market else 0
    market_rows = len(market)
    market_most_no = market_rows > 0 and market_no_count >= max(1, int(market_rows * 0.8))

    add_blocker(
        blockers,
        "CURRENT_GEAR_SOURCE_20260625_20260627",
        "GEAR",
        "HIGH",
        f"Current governed meetings require current gear source refresh. Meetings: {meeting_text}",
        "Gear-specific positives/negatives cannot be asserted for current runners.",
        "Treat NO_GEAR as source unavailable or no listed change only; do not treat as negative.",
        "Fetch current RacingAustralia gear changes for each governed date/track using GearChanges.aspx URL pattern, then rebuild gear live join.",
        "build_edgeiq_current_gear_live_join_v1.py > apply_edgeiq_current_gear_to_governed_board_v1.py > build_edgeiq_gear_profile_engine_v1.py > build_edgeiq_gear_signal_engine_v1.py > build_edgeiq_intelligence_mode_engine_v2.py > build_edgeiq_runner_drawer_feed_v3.py",
        "LOW if treated as missing source; HIGH if interpreted as a negative horse signal.",
    )

    if gear_all_no:
        add_blocker(
            blockers,
            "GEAR_SIGNAL_ALL_NO_GEAR_CURRENT",
            "GEAR",
            "HIGH",
            f"edgeiq_gear_signal_engine_v1.csv rows={gear_rows}, NO_GEAR={gear_no_count}",
            "Gear signal engine is active but effectively source-blocked for current meetings.",
            "Suppress customer inference from gear until current gear source is refreshed.",
            "Refresh source, then rerun gear/intelligence/drawer sequence.",
            "build_edgeiq_gear_signal_engine_v1.py after current gear source refresh",
            "LOW while labelled as source blocker; MEDIUM if surfaced without caveat.",
        )

    add_blocker(
        blockers,
        "CURRENT_MARKET_PRICE_ROWS_MISSING",
        "MARKET",
        "HIGH",
        f"edgeiq_market_alignment_engine_v1.csv rows={market_rows}, NO_MARKET_DATA={market_no_count}",
        "Current market alignment is safe but unable to assess most live runners.",
        "Show/source-state NO_MARKET_DATA; do not force market edge signals.",
        "Refresh current TAB/live price source and rerun governed board and market alignment.",
        "run_edgeiq_vic_master_orchestrator.py > build_edgeiq_live_terminal_feed_v1.py > build_edgeiq_live_runner_board_from_terminal_v1.py > build_edgeiq_live_runner_board_governed_v1.py > build_edgeiq_market_alignment_engine_v1.py",
        "LOW if treated as missing source; HIGH if stale prices are used.",
    )

    if market_most_no:
        add_blocker(
            blockers,
            "MARKET_ALIGNMENT_NO_CURRENT_ROWS",
            "MARKET",
            "MEDIUM",
            f"Market rows are present but mostly NO_MARKET_DATA ({market_no_count}/{market_rows}).",
            "Market confidence and value/risk reads are not available for most current runners.",
            "Keep model/price calculations unchanged and mark market data unavailable.",
            "Refresh current live market feed before relying on market alignment.",
            "build_edgeiq_market_alignment_engine_v1.py after current market source refresh",
            "LOW if hidden/flagged as missing; MEDIUM if shown as zero evidence.",
        )

    dry_missing = [r for r in dry if r.get("dry_run_status") in {"SCRIPT_MISSING", "INPUT_MISSING", "SOURCE_BLOCKER_PRESENT"} or r.get("current_blocker")]
    for idx, row in enumerate(dry_missing, start=1):
        blocker = row.get("current_blocker") or row.get("dry_run_status")
        if blocker in {"GEAR_SOURCE_BLOCKER", "MARKET_SOURCE_BLOCKER"}:
            severity = "MEDIUM"
        elif blocker == "SCRIPT_MISSING":
            severity = "HIGH"
        else:
            severity = "MEDIUM"
        add_blocker(
            blockers,
            f"ACTIVE_BUILD_CHAIN_{idx:03d}",
            "ACTIVE_BUILD_CHAIN",
            severity,
            f"Step {row.get('step_no')} {row.get('script')} dry-run status {row.get('dry_run_status')} blocker {blocker}",
            "Active chain may need source refresh before full rebuild. Full chain was not executed in this audit.",
            "Do not run production chain until blockers are resolved or explicitly accepted.",
            "Resolve missing source or manifest declaration, then rerun dry-run audit.",
            row.get("script", ""),
            "LOW while dry-run only; MEDIUM/HIGH if ignored before production rebuild.",
        )

    counts = Counter(r["severity"] for r in blockers)
    status = "CURRENT_SOURCE_BLOCKERS_REGISTERED" if blockers else "NO_CURRENT_SOURCE_BLOCKERS_FOUND"
    summary = [
        {"metric": "status", "value": status},
        {"metric": "blocker_count", "value": len(blockers)},
        {"metric": "high_severity_blocker_count", "value": counts.get("HIGH", 0)},
        {"metric": "medium_severity_blocker_count", "value": counts.get("MEDIUM", 0)},
        {"metric": "low_severity_blocker_count", "value": counts.get("LOW", 0)},
        {"metric": "governed_rows", "value": len(governed)},
        {"metric": "governed_meetings", "value": len(meetings)},
        {"metric": "governed_meeting_list", "value": meeting_text},
        {"metric": "gear_rows", "value": gear_rows},
        {"metric": "gear_no_gear_rows", "value": gear_no_count},
        {"metric": "market_rows", "value": market_rows},
        {"metric": "market_no_market_data_rows", "value": market_no_count},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "ui_changed", "value": "NO"},
        {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
    ]

    write_csv(OUT, blockers)
    write_csv(SUMMARY, summary, ["metric", "value"])
    REPORT.write_text("\n".join([
        "EDGEiQ Current Source Blocker Register V1",
        "==========================================",
        f"Status: {status}",
        f"Blocker count: {len(blockers)}",
        f"High severity blockers: {counts.get('HIGH', 0)}",
        f"Governed meetings: {meeting_text}",
        f"Gear rows / NO_GEAR: {gear_rows}/{gear_no_count}",
        f"Market rows / NO_MARKET_DATA: {market_rows}/{market_no_count}",
        "Production changed: NO",
        "Pricing changed: NO",
        "Probability changed: NO",
        "V6.1 changed: NO",
        "V7.2G2 changed: NO",
        "UI changed: NO",
    ]) + "\n", encoding="utf-8")

    gear_plan_lines = [
        "EDGEiQ Current Gear Refresh Plan V2",
        "====================================",
        "Status: CURRENT_GEAR_SOURCE_REFRESH_REQUIRED",
        "",
        "Known URL Pattern",
        "-----------------",
        "https://www.racingaustralia.horse/FreeFields/GearChanges.aspx?Key=YYYYMonDD,STATE,Track",
        "",
        "Current Governed Dates/Tracks",
        "-----------------------------",
    ]
    for d, t in meetings:
        gear_plan_lines.append(f"- {d} {t}")
    gear_plan_lines.extend([
        "",
        "Required Output Schema",
        "----------------------",
        "race_date, track, race_no, horse, horse_key, trainer, jockey, gear_change, gear_change_type, first_time_flag, removed_flag, source_url, captured_at, source_status",
        "",
        "Safe Join Keys",
        "--------------",
        "Primary: race_date + cleanTrack(track) + race_no + cleanHorse(horse)",
        "Fallback diagnostic only: race_date + cleanTrack(track) + cleanHorse(horse)",
        "Do not use loose horse-only joins for production gear signals.",
        "",
        "No Fake Data Rule",
        "-----------------",
        "Do not infer gear changes. If the source is missing or stale, keep source status missing and do not treat NO_GEAR as a negative signal.",
        "",
        "Rerun Sequence After Refresh",
        "----------------------------",
        "python .\\scripts\\build_edgeiq_current_gear_live_join_v1.py",
        "python .\\scripts\\apply_edgeiq_current_gear_to_governed_board_v1.py",
        "python .\\scripts\\build_edgeiq_gear_profile_engine_v1.py",
        "python .\\scripts\\build_edgeiq_gear_signal_engine_v1.py",
        "python .\\scripts\\build_edgeiq_intelligence_mode_engine_v2.py",
        "python .\\scripts\\build_edgeiq_runner_drawer_feed_v3.py",
        "",
        "Production changed: NO",
        "Pricing changed: NO",
        "Probability changed: NO",
        "V6.1 changed: NO",
        "V7.2G2 changed: NO",
        "UI changed: NO",
    ])
    GEAR_PLAN.write_text("\n".join(gear_plan_lines) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
