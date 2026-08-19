import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "audit_edgeiq_current_intelligence_pipeline_v1.py"

REPLACEMENTS = [
    (
        '        "file": DATA / "edgeiq_fair_price_v7_2.csv",\n'
        '        "builders": ["scripts/build_edgeiq_fair_price_v7_2.py", "src/services/marketPricingService.ts"],\n'
        '        "date_fields": ["race_date", "date"],\n'
        '        "track_fields": ["track", "meeting", "meeting_name"],\n'
        '        "race_fields": ["race_no", "race_number", "race"],\n'
        '        "runner_fields": ["horse", "runner", "runner_name", "horse_name"],\n'
        '        "metric_fields": [\n'
        '            "edgeiq_v7_2_preview_display_fair_price",\n'
        '            "edgeiq_display_fair_price_v7_2",\n'
        '            "ui_fair_price",\n'
        '            "display_fair_price",\n'
        '            "fair_price",\n'
        '            "rated_price",\n'
        '        ],\n',
        '        "file": DATA / "edgeiq_live_runner_board_governed_v1.csv",\n'
        '        "builders": ["scripts/build_edgeiq_probability_engine_v3.py", "scripts/build_edgeiq_live_runner_board_governed_v1.py", "src/services/marketPricingService.ts"],\n'
        '        "date_fields": ["race_date", "date"],\n'
        '        "track_fields": ["track", "meeting", "meeting_name"],\n'
        '        "race_fields": ["race_no", "race_number", "race"],\n'
        '        "runner_fields": ["horse", "runner", "runner_name", "horse_name", "horse_canon", "horse_key"],\n'
        '        "metric_fields": [\n'
        '            "edgeiq_v7_2_preview_display_fair_price",\n'
        '            "edgeiq_display_fair_price_v7_2",\n'
        '            "ui_fair_price",\n'
        '            "display_fair_price",\n'
        '            "display_fair_price_governed",\n'
        '            "fair_price_display",\n'
        '            "fair_price",\n'
        '            "fair_price_v7_2",\n'
        '            "rated_price",\n'
        '        ],\n',
    ),
    (
        '        "runner_fields": ["horse", "runner", "runner_name", "horse_name"],\n'
        '        "metric_fields": [\n'
        '            "projected_rating_v5_2",\n',
        '        "runner_fields": ["horse", "runner", "runner_name", "horse_name", "horse_canon", "horse_key"],\n'
        '        "metric_fields": [\n'
        '            "projected_rating_v5_2",\n',
    ),
    (
        '        "runner_fields": ["horse", "runner", "runner_name", "horse_name"],\n'
        '        "metric_fields": ["projected_speed", "projected_spd", "early_speed_rating"],\n',
        '        "runner_fields": ["horse", "runner", "runner_name", "horse_name", "horse_canon", "horse_key"],\n'
        '        "metric_fields": ["projected_speed", "projected_spd", "early_speed_rating"],\n',
    ),
    (
        '        "runner_fields": ["horse", "runner", "runner_name", "horse_name"],\n'
        '        "metric_fields": ["late_speed", "late_power_index", "late_power_score"],\n',
        '        "runner_fields": ["horse", "runner", "runner_name", "horse_name", "horse_canon", "horse_key"],\n'
        '        "metric_fields": ["late_speed", "late_power_index", "late_power_score"],\n',
    ),
    (
        '                    "runner_number": clean_text(runner.get("number")),\n'
        '                    "runner_name": clean_text(runner.get("name")),\n'
        '                    "runner_key": canonical_runner(runner.get("name")),\n',
        '                    "runner_number": clean_text(runner.get("runnerNumber") or runner.get("number")),\n'
        '                    "runner_name": clean_text(runner.get("runnerName") or runner.get("name")),\n'
        '                    "runner_key": canonical_runner(runner.get("normalisedRunnerName") or runner.get("runnerName") or runner.get("name")),\n',
    ),
]


def main():
    if not TARGET.exists():
        raise FileNotFoundError(TARGET)
    text = TARGET.read_text(encoding="utf-8")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"{TARGET.stem}_CHECKPOINT_BEFORE_AUDIT_KEY_PATCH_{stamp}{TARGET.suffix}")
    shutil.copy2(TARGET, backup)
    changed = 0
    for old, new in REPLACEMENTS:
        if old not in text:
            raise RuntimeError(f"Patch anchor not found after {changed} replacements:\n{old}")
        text = text.replace(old, new, 1)
        changed += 1
    TARGET.write_text(text, encoding="utf-8")
    print("EDGEIQ_CURRENT_INTELLIGENCE_AUDIT_KEY_PATCH_COMPLETE")
    print(f"checkpoint={backup}")
    print(f"replacements={changed}")


if __name__ == "__main__":
    main()
