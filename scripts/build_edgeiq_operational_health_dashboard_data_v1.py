from pathlib import Path
import csv
from collections import Counter
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DRY = DATA / "edgeiq_active_build_chain_dry_run_v1.csv"
DRY_SUMMARY = DATA / "edgeiq_active_build_chain_dry_run_v1_summary.csv"
BLOCKERS = DATA / "edgeiq_current_source_blocker_register_v1.csv"
BLOCKER_SUMMARY = DATA / "edgeiq_current_source_blocker_register_v1_summary.csv"
INTEL = DATA / "edgeiq_intelligence_mode_engine_v2.csv"
DRAWER = DATA / "edgeiq_runner_drawer_feed_v3.csv"
MARKET = DATA / "edgeiq_market_alignment_engine_v1.csv"
GEAR = DATA / "edgeiq_gear_signal_engine_v1.csv"
MASTER_SUMMARY = DATA / "edgeiq_master_candidate_validation_v1_summary.csv"

OUT = DATA / "edgeiq_operational_health_dashboard_data_v1.csv"
SUMMARY = DATA / "edgeiq_operational_health_dashboard_data_v1_summary.csv"
REPORT = DATA / "edgeiq_operational_health_dashboard_data_v1_report.txt"


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def summary_dict(path):
    data = {}
    for r in read_csv(path):
        if "metric" in r and "value" in r:
            data[r["metric"]] = r["value"]
    return data


def write_csv(path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        keys = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def count_rows(path):
    return len(read_csv(path)) if path.exists() else 0


def value_count(path, column, value):
    rows = read_csv(path)
    return sum(1 for r in rows if str(r.get(column, "")).strip().upper() == value.upper()), len(rows)


def add(rows, area, status, severity, evidence, recommended_action):
    rows.append({
        "system_area": area,
        "status": status,
        "severity": severity,
        "evidence": evidence,
        "recommended_action": recommended_action,
        "production_changed": "NO",
        "pricing_changed": "NO",
        "probability_changed": "NO",
        "v6_1_changed": "NO",
        "v7_2g2_changed": "NO",
        "ui_changed": "NO",
    })


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    master = summary_dict(MASTER_SUMMARY)
    dry_summary = summary_dict(DRY_SUMMARY)
    blocker_summary = summary_dict(BLOCKER_SUMMARY)
    blockers = read_csv(BLOCKERS)
    rows = []

    master_status = master.get("status", "MISSING_MASTER_VALIDATION")
    master_sev = "OK" if master_status == "EDGEIQ_MASTER_CANDIDATE_VALIDATION_PASS" else "HIGH"
    add(rows, "master_candidate_status", master_status, master_sev, f"hash={master.get('manifest_hash_pass','?')}/{master.get('corrected_v2_payload_file_count','?')}; npm_build={master.get('npm_build_status','?')}; py_compile={master.get('python_compile_pass','?')}/{master.get('python_scripts_checked','?')}", "Keep master as clean reference until explicit cutover.")

    chain_status = dry_summary.get("status", "MISSING_DRY_RUN")
    chain_sev = "OK" if "PASS" in chain_status else "MEDIUM"
    add(rows, "active_build_chain_status", chain_status, chain_sev, f"steps={dry_summary.get('steps','?')}; scripts_missing={dry_summary.get('scripts_missing','?')}; source_blockers={dry_summary.get('source_blocker_rows','?')}", "Resolve source blockers before executing full production chain.")

    market_no, market_rows = value_count(MARKET, "market_alignment_band", "NO_MARKET_DATA")
    market_status = "CURRENT_MARKET_SOURCE_BLOCKED" if market_rows == 0 or market_no >= max(1, int(market_rows * 0.8)) else "MARKET_DATA_PARTIAL_OR_AVAILABLE"
    add(rows, "market_data_status", market_status, "HIGH" if "BLOCKED" in market_status else "MEDIUM", f"rows={market_rows}; NO_MARKET_DATA={market_no}", "Refresh current live market source before relying on market alignment.")

    gear_no, gear_rows = value_count(GEAR, "gear_signal_band", "NO_GEAR")
    gear_status = "CURRENT_GEAR_SOURCE_BLOCKED" if gear_rows == 0 or gear_no == gear_rows else "GEAR_DATA_PARTIAL_OR_AVAILABLE"
    add(rows, "gear_data_status", gear_status, "HIGH" if "BLOCKED" in gear_status else "MEDIUM", f"rows={gear_rows}; NO_GEAR={gear_no}", "Refresh RacingAustralia gear changes for current governed meetings.")

    intel_rows = read_csv(INTEL)
    if intel_rows:
        modes = Counter(r.get("intelligence_mode_v2", "UNKNOWN") for r in intel_rows)
        intel_status = "INTELLIGENCE_MODE_FEED_AVAILABLE"
        intel_evidence = f"rows={len(intel_rows)}; modes={dict(modes)}"
        intel_sev = "OK"
    else:
        intel_status = "INTELLIGENCE_MODE_FEED_MISSING"
        intel_evidence = "rows=0"
        intel_sev = "HIGH"
    add(rows, "intelligence_mode_status", intel_status, intel_sev, intel_evidence, "Rebuild after source refresh if blockers are resolved.")

    drawer_rows = count_rows(DRAWER)
    drawer_status = "RUNNER_DRAWER_FEED_AVAILABLE" if drawer_rows else "RUNNER_DRAWER_FEED_MISSING"
    add(rows, "runner_drawer_feed_status", drawer_status, "OK" if drawer_rows else "HIGH", f"rows={drawer_rows}", "Rebuild after gear/market refresh if drawer uses those statuses.")

    prod_safety = "PRODUCTION_SAFETY_CONFIRMED"
    add(rows, "production_safety_status", prod_safety, "OK", "No production/pricing/probability/V6.1/V7.2G2/UI changes made by this health build.", "Continue copy-only validation discipline.")

    blocker_count = int(blocker_summary.get("blocker_count", len(blockers)) or 0)
    high_blockers = int(blocker_summary.get("high_severity_blocker_count", 0) or 0)
    if master_status == "EDGEIQ_MASTER_CANDIDATE_VALIDATION_PASS" and high_blockers:
        overall = "OPERATIONAL_HEALTH_READY_WITH_SOURCE_BLOCKERS"
        next_action = "Keep original app live, keep master as reference, resolve current gear and market source blockers before feature/engine refresh."
    elif master_status == "EDGEIQ_MASTER_CANDIDATE_VALIDATION_PASS":
        overall = "OPERATIONAL_HEALTH_READY"
        next_action = "Continue with explicit cutover planning only if requested."
    else:
        overall = "OPERATIONAL_HEALTH_REVIEW_REQUIRED"
        next_action = "Fix master validation before any cutover planning."

    add(rows, "recommended_next_action", overall, "MEDIUM" if high_blockers else "OK", f"blockers={blocker_count}; high={high_blockers}", next_action)

    summary = [
        {"metric": "status", "value": overall},
        {"metric": "master_candidate_status", "value": master_status},
        {"metric": "active_build_chain_status", "value": chain_status},
        {"metric": "market_data_status", "value": market_status},
        {"metric": "gear_data_status", "value": gear_status},
        {"metric": "intelligence_mode_status", "value": intel_status},
        {"metric": "runner_drawer_feed_status", "value": drawer_status},
        {"metric": "production_safety_status", "value": prod_safety},
        {"metric": "blocker_count", "value": blocker_count},
        {"metric": "high_severity_blocker_count", "value": high_blockers},
        {"metric": "recommended_next_action", "value": next_action},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "ui_changed", "value": "NO"},
        {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
    ]

    write_csv(OUT, rows)
    write_csv(SUMMARY, summary, ["metric", "value"])
    REPORT.write_text("\n".join([
        "EDGEiQ Operational Health Dashboard Data V1",
        "============================================",
        f"Status: {overall}",
        f"Master candidate: {master_status}",
        f"Active build chain: {chain_status}",
        f"Market data: {market_status}",
        f"Gear data: {gear_status}",
        f"Intelligence mode: {intel_status}",
        f"Runner drawer: {drawer_status}",
        f"Blockers: {blocker_count} total, {high_blockers} high severity",
        f"Recommended next action: {next_action}",
        "Production changed: NO",
        "Pricing changed: NO",
        "Probability changed: NO",
        "V6.1 changed: NO",
        "V7.2G2 changed: NO",
        "UI changed: NO",
    ]) + "\n", encoding="utf-8")
    print(overall)


if __name__ == "__main__":
    main()
