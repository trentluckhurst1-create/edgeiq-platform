from __future__ import annotations
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'scripts' / 'audit_edgeiq_race_entry_performance_context_fact_v1.py'
CHECKPOINT = ROOT / 'docs' / 'victoria-performance-intelligence-race-context-authority-v1' / 'checkpoints' / 'audit_edgeiq_race_entry_performance_context_fact_v1_PRE_CURRENT_CONTEXT_AUDIT_ALIGNMENT.py'
CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
if not CHECKPOINT.exists():
    shutil.copy2(TARGET, CHECKPOINT)
text = TARGET.read_text(encoding='utf-8')
old = '''        expected_identity_hash = sha256_payload(
            [
                CONTRACT_VERSION,
                snapshot_id,
                text(
                    fact["race_entry_id"]
                ),
                text(
                    fact["race_id"]
                ),
            ]
        )

        expected_context_id = (
            f"REPC1-"
            f"{expected_identity_hash[:24].upper()}"
        )'''
new = '''        expected_identity_hash = sha256_payload(
            [
                snapshot_id,
                text(fact["race_entry_id"]),
                text(fact["race_id"]),
                text(fact["runner_id"]),
                text(fact["selected_horse_performance_rating_id"]),
            ]
        )

        expected_context_id = (
            f"REPCF1-"
            f"{expected_identity_hash[:24].upper()}"
        )'''
if old not in text:
    raise RuntimeError('Identity block not found')
text = text.replace(old, new)
text = text.replace('            "race_class_code",\n            "track_id",', '            "track_id",')
text = text.replace('            "rail_position",\n            "source_snapshot_evidence_sha256",', '            "source_snapshot_evidence_sha256",')
old2 = '''    current_population_expected = (
        len(snapshot_rows) == 0
        and len(fact_rows) == 0
    )

    check(
        "current_population_expected",
        current_population_expected,
        {
            "snapshot_rows": len(
                snapshot_rows
            ),
            "race_entry_rows": len(
                race_entry_rows
            ),
            "context_rows": len(
                fact_rows
            ),
        },
    )'''
new2 = '''    missing_race_class_rows = [
        text(row.get("race_entry_performance_context_id", ""))
        for row in fact_rows
        if not text(row.get("race_class_code", ""))
    ]
    missing_rail_rows = [
        text(row.get("race_entry_performance_context_id", ""))
        for row in fact_rows
        if not text(row.get("rail_position", ""))
    ]

    check(
        "current_population_expected",
        len(fact_rows) == len(snapshot_rows),
        {
            "snapshot_rows": len(snapshot_rows),
            "race_entry_rows": len(race_entry_rows),
            "context_rows": len(fact_rows),
        },
    )

    check(
        "governed_class_context_gap_reported",
        True,
        {
            "missing_race_class_rows": missing_race_class_rows,
            "missing_race_class_count": len(missing_race_class_rows),
        },
    )

    check(
        "governed_rail_context_gap_reported",
        True,
        {
            "missing_rail_rows": missing_rail_rows,
            "missing_rail_count": len(missing_rail_rows),
        },
    )'''
if old2 not in text:
    raise RuntimeError('Current population block not found')
text = text.replace(old2, new2)
text = text.replace('"audit_version": "1.0.0"', '"audit_version": "1.1.0_race_context_authority_alignment"')
TARGET.write_text(text, encoding='utf-8')
print('EDGEIQ_PERFORMANCE_CONTEXT_AUDIT_ALIGNMENT_APPLIED')
print(f'checkpoint={CHECKPOINT}')
print(f'target={TARGET}')
