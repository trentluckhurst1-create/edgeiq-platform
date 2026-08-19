from __future__ import annotations
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'scripts' / 'build_edgeiq_race_entry_performance_context_fact_v1.py'
CHECKPOINT = ROOT / 'docs' / 'victoria-performance-intelligence-race-context-authority-v1' / 'checkpoints' / 'build_edgeiq_race_entry_performance_context_fact_v1_PRE_RACE_CONTEXT_AUTHORITY.py'
CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
if not CHECKPOINT.exists():
    shutil.copy2(TARGET, CHECKPOINT)
text = TARGET.read_text(encoding='utf-8')
text = text.replace(
    'BUILDER_VERSION = "edgeiq_race_entry_performance_context_fact_v1.1.0_current_schema_adapter"',
    'BUILDER_VERSION = "edgeiq_race_entry_performance_context_fact_v1.2.0_race_context_authority"'
)
text = text.replace(
    '    candidate_paths = [\n        DATA / "edgeiq_vic_three_day_race_fields.csv",',
    '    candidate_paths = [\n        DATA / "edgeiq_race_context_authority_fact_v1.csv",\n        DATA / "edgeiq_vic_three_day_race_fields.csv",'
)
text = text.replace(
    '            track = optional_first(row, ["track", "normalised_track", "canonical_track", "meeting_name"])',
    '            track = optional_first(row, ["track", "normalised_track", "canonical_track", "track_id", "meeting_name"])'
)
text = text.replace(
    '            race_no = optional_first(row, ["race_no", "race_number"])',
    '            race_no = optional_first(row, ["race_no", "race_number", "number"])'
)
text = text.replace(
    '                target["race_class_code"] = optional_first(row, ["race_class_code", "race_class", "class"])',
    '                target["race_class_code"] = optional_first(row, ["race_class_code", "race_class", "race_class_source_value", "class"])'
)
text = text.replace(
    '                target["rail_position"] = optional_first(row, ["rail_position", "rail", "rail_position_text"])',
    '                target["rail_position"] = optional_first(row, ["rail_position", "rail_source_value", "rail", "rail_position_text"])'
)
text = text.replace(
    '                target["track_condition"] = optional_first(row, ["track_condition", "condition", "track_rating"])',
    '                target["track_condition"] = optional_first(row, ["track_condition", "condition", "track_rating"])'
)
TARGET.write_text(text, encoding='utf-8')
print('EDGEIQ_PERFORMANCE_CONTEXT_RACE_CONTEXT_AUTHORITY_PATCH_APPLIED')
print(f'checkpoint={CHECKPOINT}')
print(f'target={TARGET}')
