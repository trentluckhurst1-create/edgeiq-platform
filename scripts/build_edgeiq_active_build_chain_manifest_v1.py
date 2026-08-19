from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

DATA = Path("public/data")
OUT = DATA / "edgeiq_active_build_chain_manifest_v1.csv"
REPORT = DATA / "edgeiq_active_build_chain_manifest_v1_report.txt"

STEPS = [
    (1, "run_edgeiq_vic_master_orchestrator.py", "Master orchestration for VIC current meeting build", "raw/current meeting sources", "terminal/live board feeds", "YES", "YES", "NO", "YES"),
    (2, "build_edgeiq_live_terminal_feed_v1.py", "Build live terminal feed", "edgeiq_vic_three_day_meeting_universe.csv", "edgeiq_live_terminal_feed_v1.csv", "YES", "YES", "NO", "YES"),
    (3, "build_edgeiq_live_runner_board_from_terminal_v1.py", "Build live runner board from terminal feed", "edgeiq_live_terminal_feed_v1.csv", "edgeiq_live_runner_board_v1.csv", "YES", "YES", "NO", "YES"),
    (4, "build_edgeiq_live_runner_board_governed_v1.py", "Apply governance to live runner board", "edgeiq_live_runner_board_v1.csv", "edgeiq_live_runner_board_governed_v1.csv", "YES", "YES", "NO", "YES"),
    (5, "build_edgeiq_market_alignment_engine_v1.py", "Build market alignment intelligence", "edgeiq_live_runner_board_governed_v1.csv", "edgeiq_market_alignment_engine_v1.csv", "NO", "YES", "NO", "YES"),
    (6, "build_edgeiq_dynamic_confidence_engine_v1.py", "Build dynamic confidence layer", "edgeiq_live_runner_board_governed_v1.csv", "dynamic confidence outputs if present", "NO", "YES", "NO", "YES"),
    (7, "build_edgeiq_debutant_intelligence_engine_v1.py", "Build debutant intelligence", "edgeiq_live_runner_board_governed_v1.csv|historical results", "edgeiq_debutant_intelligence_engine_v1.csv", "NO", "NO", "NO", "YES"),
    (8, "build_edgeiq_current_gear_live_join_v1.py", "Join refreshed current gear to governed universe candidate", "edgeiq_live_runner_board_governed_v1.csv|gear_changes.csv", "edgeiq_current_gear_live_join_v1.csv", "NO", "NO", "YES", "YES"),
    (9, "apply_edgeiq_current_gear_to_governed_board_v1.py", "Apply safe gear fields to governed board after checkpoint", "edgeiq_current_gear_live_join_v1.csv|edgeiq_live_runner_board_governed_v1.csv", "edgeiq_live_runner_board_governed_v1.csv|edgeiq_live_runner_board_governed_v1_gear_join_audit.csv", "YES", "NO", "YES", "YES"),
    (10, "build_edgeiq_gear_profile_engine_v1.py", "Build historical gear profile reads for live runners", "edgeiq_historical_results_warehouse_v2_graphql.csv|edgeiq_live_runner_board_governed_v1.csv", "edgeiq_gear_profile_engine_v1.csv", "NO", "NO", "YES", "YES"),
    (11, "build_edgeiq_gear_signal_engine_v1.py", "Build runner-level gear signal engine", "edgeiq_gear_profile_engine_v1.csv|edgeiq_live_runner_board_governed_v1.csv", "edgeiq_gear_signal_engine_v1.csv", "NO", "NO", "YES", "YES"),
    (12, "build_edgeiq_intelligence_mode_engine_v2.py", "Build race-level intelligence mode with gear/debutant/market context", "edgeiq_intelligence_mode_engine_v1.csv|edgeiq_gear_signal_engine_v1.csv|edgeiq_debutant_intelligence_engine_v1.csv|edgeiq_market_alignment_engine_v1.csv|edgeiq_live_runner_board_governed_v1.csv", "edgeiq_intelligence_mode_engine_v2.csv", "NO", "YES", "YES", "YES"),
    (13, "build_edgeiq_runner_drawer_feed_v3.py", "Build backend runner drawer feed with gear/debutant/mode panels", "edgeiq_live_runner_board_governed_v1.csv|edgeiq_gear_signal_engine_v1.csv|edgeiq_debutant_intelligence_engine_v1.csv|edgeiq_intelligence_mode_engine_v2.csv", "edgeiq_runner_drawer_feed_v3.csv", "NO", "NO", "YES", "YES"),
]
rows=[]
for step_no, script, purpose, inputs, outputs, prod, market, gear, rebuild in STEPS:
    path = Path("scripts") / script
    rows.append({
        "step_no": step_no,
        "script": script,
        "script_exists": "YES" if path.exists() else "NO",
        "purpose": purpose,
        "input_files": inputs,
        "output_files": outputs,
        "production_critical": prod,
        "requires_market": market,
        "requires_gear": gear,
        "requires_rebuild_after_refresh": rebuild,
    })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
missing = df[df["script_exists"] == "NO"]["script"].tolist()
REPORT.write_text("\n".join([
    "EDGEIQ_ACTIVE_BUILD_CHAIN_MANIFEST_V1",
    "======================================",
    f"Manifest steps: {len(df)}",
    f"Scripts present: {int((df['script_exists'] == 'YES').sum())}",
    f"Scripts missing: {len(missing)}",
    "Missing scripts:",
    *(f"- {m}" for m in missing),
    "",
    "Notes:",
    "- This is an audit/manifest only; no production data was rebuilt.",
    "- Gear-dependent steps must be rerun after current gear source refresh.",
    "- Do not promote refreshed gear until join audit confirms safe current matches.",
    "",
    "Production changed: NO",
    "Pricing changed: NO",
    "Probability changed: NO",
    "V6.1 changed: NO",
    "V7.2G2 changed: NO",
    "UI changed: NO",
    f"Built at: {datetime.now(timezone.utc).isoformat()}",
]) + "\n", encoding="utf-8")
print("ACTIVE_BUILD_CHAIN_MANIFEST_COMPLETE", len(df), len(missing))
