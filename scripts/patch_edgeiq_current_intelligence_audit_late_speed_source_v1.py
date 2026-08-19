import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "audit_edgeiq_current_intelligence_pipeline_v1.py"

OLD = '''    "Late Speed": {
        "file": DATA / "edgeiq_live_runner_board_governed_v1.csv",
        "builders": ["scripts/build_edgeiq_live_runner_board_governed_v1.py", "src/services/runnerMetricsService.ts"],
        "date_fields": ["race_date", "date"],
        "track_fields": ["track", "meeting", "meeting_name"],
        "race_fields": ["race_no", "race_number", "race"],
        "runner_fields": ["horse", "runner", "runner_name", "horse_name", "horse_canon", "horse_key"],
        "metric_fields": ["late_speed", "late_power_index", "late_power_score"],
    },
'''

NEW = '''    "Late Speed": {
        "file": DATA / "live_speed_map_v3.csv",
        "builders": ["scripts/build_live_speed_map_engine_v3.py", "scripts/build_edgeiq_live_runner_board_governed_v1.py", "src/services/runnerMetricsService.ts"],
        "date_fields": ["race_date", "date"],
        "track_fields": ["track", "meeting", "meeting_name"],
        "race_fields": ["race_no", "race_number", "race"],
        "runner_fields": ["horse_key", "horse", "runner", "runner_name", "horse_canon"],
        "metric_fields": ["late_speed", "late_power_index", "late_power_score"],
    },
'''


def main():
    text = TARGET.read_text(encoding="utf-8")
    if OLD not in text:
        raise RuntimeError("Late Speed contract anchor not found.")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"{TARGET.stem}_CHECKPOINT_BEFORE_LATE_SPEED_AUDIT_SOURCE_{stamp}{TARGET.suffix}")
    shutil.copy2(TARGET, backup)
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("EDGEIQ_CURRENT_INTELLIGENCE_AUDIT_LATE_SPEED_SOURCE_PATCH_COMPLETE")
    print(f"checkpoint={backup}")


if __name__ == "__main__":
    main()
