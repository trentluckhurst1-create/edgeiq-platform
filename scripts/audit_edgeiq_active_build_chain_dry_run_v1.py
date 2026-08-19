from pathlib import Path
import csv
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CHAIN = DATA / "edgeiq_active_build_chain_manifest_v1.csv"
OUTPUT = DATA / "edgeiq_active_build_chain_dry_run_v1.csv"
SUMMARY = DATA / "edgeiq_active_build_chain_dry_run_v1_summary.csv"
REPORT = DATA / "edgeiq_active_build_chain_dry_run_v1_report.txt"


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
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def split_refs(value):
    value = (value or "").strip()
    if not value:
        return []
    parts = re.split(r"[;|\n]+|,\s*", value)
    cleaned = []
    for part in parts:
        p = part.strip().strip('"').strip("'")
        if p:
            cleaned.append(p)
    return cleaned


def resolve_ref(ref):
    r = ref.strip()
    if not r or r.upper() in {"NA", "N/A", "NONE"}:
        return None
    if ".csv" not in r.lower() and ".txt" not in r.lower() and ".json" not in r.lower() and ".py" not in r.lower():
        return None
    p = Path(r)
    if p.is_absolute():
        return p
    if r.startswith("public/") or r.startswith("public\\") or r.startswith("scripts/") or r.startswith("scripts\\"):
        return ROOT / r
    if r.lower().endswith(".py"):
        return ROOT / "scripts" / r
    return DATA / r


def yn(value):
    return "YES" if str(value).strip().upper() == "YES" else "NO"


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    chain = read_csv(CHAIN)
    rows = []
    missing_input_count = 0
    missing_output_count = 0
    missing_script_count = 0
    source_blocker_count = 0

    for row in chain:
        script = (row.get("script") or "").strip()
        script_path = ROOT / "scripts" / script
        script_exists = script_path.exists()
        if not script_exists:
            missing_script_count += 1

        inputs = split_refs(row.get("input_files", ""))
        outputs = split_refs(row.get("output_files", ""))
        input_statuses = []
        output_statuses = []
        blocker = ""

        requires_market = yn(row.get("requires_market", ""))
        requires_gear = yn(row.get("requires_gear", ""))
        prod_critical = yn(row.get("production_critical", ""))

        if not inputs:
            input_statuses.append("NO_DECLARED_INPUTS")
        for item in inputs:
            path = resolve_ref(item)
            if path is None:
                input_statuses.append(f"{item}:EXTERNAL_OR_UNRESOLVED")
                if "market" in item.lower() or requires_market == "YES":
                    blocker = "MARKET_SOURCE_BLOCKER"
                    source_blocker_count += 1
                elif "gear" in item.lower() or requires_gear == "YES":
                    blocker = "GEAR_SOURCE_BLOCKER"
                    source_blocker_count += 1
                continue
            exists = path.exists()
            input_statuses.append(f"{item}:{'EXISTS' if exists else 'MISSING'}")
            if not exists:
                missing_input_count += 1
                if requires_gear == "YES" or "gear" in item.lower():
                    blocker = "GEAR_SOURCE_BLOCKER"
                elif requires_market == "YES" or "market" in item.lower() or "price" in item.lower():
                    blocker = "MARKET_SOURCE_BLOCKER"
                else:
                    blocker = "MISSING_ACTIVE_DEPENDENCY"

        if not outputs:
            output_statuses.append("NO_DECLARED_OUTPUTS")
        for item in outputs:
            path = resolve_ref(item)
            if path is None:
                output_statuses.append(f"{item}:EXTERNAL_OR_UNRESOLVED")
                continue
            exists = path.exists()
            output_statuses.append(f"{item}:{'EXISTS' if exists else 'MISSING'}")
            if not exists:
                missing_output_count += 1

        if not script_exists:
            row_status = "SCRIPT_MISSING"
        elif blocker:
            row_status = "SOURCE_BLOCKER_PRESENT"
        elif any(s.endswith(":MISSING") for s in input_statuses):
            row_status = "INPUT_MISSING"
        else:
            row_status = "DRY_RUN_OK"

        rows.append({
            "step_no": row.get("step_no", ""),
            "script": script,
            "script_path": str(script_path),
            "script_exists": "YES" if script_exists else "NO",
            "purpose": row.get("purpose", ""),
            "declared_inputs": row.get("input_files", ""),
            "input_check": " | ".join(input_statuses),
            "declared_outputs": row.get("output_files", ""),
            "output_check": " | ".join(output_statuses),
            "requires_market": requires_market,
            "requires_gear": requires_gear,
            "production_critical": prod_critical,
            "requires_rebuild_after_refresh": yn(row.get("requires_rebuild_after_refresh", "")),
            "current_blocker": blocker,
            "dry_run_status": row_status,
        })

    scripts_ok = sum(1 for r in rows if r["script_exists"] == "YES")
    blocker_rows = sum(1 for r in rows if r["current_blocker"])
    fail_rows = sum(1 for r in rows if r["dry_run_status"] == "SCRIPT_MISSING")
    if fail_rows:
        status = "ACTIVE_BUILD_CHAIN_DRY_RUN_REVIEW_REQUIRED"
    elif blocker_rows:
        status = "ACTIVE_BUILD_CHAIN_DRY_RUN_PASS_WITH_SOURCE_BLOCKERS"
    else:
        status = "ACTIVE_BUILD_CHAIN_DRY_RUN_PASS"

    summary = [
        {"metric": "status", "value": status},
        {"metric": "manifest", "value": str(CHAIN)},
        {"metric": "steps", "value": len(rows)},
        {"metric": "scripts_present", "value": scripts_ok},
        {"metric": "scripts_missing", "value": missing_script_count},
        {"metric": "missing_declared_input_refs", "value": missing_input_count},
        {"metric": "missing_declared_output_refs", "value": missing_output_count},
        {"metric": "source_blocker_rows", "value": blocker_rows},
        {"metric": "gear_blocker_rows", "value": sum(1 for r in rows if r["current_blocker"] == "GEAR_SOURCE_BLOCKER")},
        {"metric": "market_blocker_rows", "value": sum(1 for r in rows if r["current_blocker"] == "MARKET_SOURCE_BLOCKER")},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "full_build_chain_executed", "value": "NO"},
        {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
    ]

    write_csv(OUTPUT, rows)
    write_csv(SUMMARY, summary, ["metric", "value"])
    REPORT.write_text("\n".join([
        "EDGEiQ Active Build Chain Dry Run V1",
        "====================================",
        f"Status: {status}",
        f"Steps audited: {len(rows)}",
        f"Scripts present: {scripts_ok}",
        f"Scripts missing: {missing_script_count}",
        f"Missing declared input refs: {missing_input_count}",
        f"Missing declared output refs: {missing_output_count}",
        f"Source blocker rows: {blocker_rows}",
        "Full build chain executed: NO",
        "Production changed: NO",
        "Pricing changed: NO",
        "Probability changed: NO",
        "V6.1 changed: NO",
        "V7.2G2 changed: NO",
        "UI changed: NO",
    ]) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
