from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "build_edgeiq_race_entry_context_adjustment_fact_v1.py"
CHECKPOINT = ROOT / "docs" / "victoria-performance-intelligence-completion-v1" / "checkpoints" / "build_edgeiq_race_entry_context_adjustment_fact_v1_PRE_EMPTY_INPUT_GUARD.py"
CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
if not CHECKPOINT.exists():
    CHECKPOINT.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
text = TARGET.read_text(encoding="utf-8")
text = text.replace(
    'BUILDER_VERSION = (\n    "edgeiq_race_entry_context_adjustment_fact_v1.0.0"\n)',
    'BUILDER_VERSION = (\n    "edgeiq_race_entry_context_adjustment_fact_v1.0.1_empty_input_guard"\n)',
)
old = """    context_fields, context_rows = read_csv(
        CONTEXT_PATH
    )

    parameter_fields, parameter_rows = read_csv(
        PARAMETER_PATH
    )

    require_fields(
        CONTEXT_PATH,
        context_fields,
        [
"""
new = """    context_fields, context_rows = read_csv(
        CONTEXT_PATH
    )

    has_selected_parameter = any(
        text(row.get("context_parameter_selection_decision", "")) == PARAMETER_SELECTED
        for row in selection_rows
    )

    if has_selected_parameter:
        parameter_fields, parameter_rows = read_csv(
            PARAMETER_PATH
        )
    else:
        parameter_fields, parameter_rows = [], []

    require_fields(
        CONTEXT_PATH,
        context_fields,
        [
"""
if old not in text:
    raise RuntimeError("expected context/parameter read block not found")
text = text.replace(old, new)
old2 = """    require_fields(
        PARAMETER_PATH,
        parameter_fields,
        [
            "context_parameter_id",
            *ADJUSTMENT_FIELDS,
            "parameter_status",
            "context_parameter_evidence_sha256",
            "builder_version",
            "contract_version",
        ],
    )
"""
new2 = """    if has_selected_parameter:
        require_fields(
            PARAMETER_PATH,
            parameter_fields,
            [
                "context_parameter_id",
                *ADJUSTMENT_FIELDS,
                "parameter_status",
                "context_parameter_evidence_sha256",
                "builder_version",
                "contract_version",
            ],
        )
"""
if old2 not in text:
    raise RuntimeError("expected parameter require_fields block not found")
text = text.replace(old2, new2)
TARGET.write_text(text, encoding="utf-8")
print(f"checkpoint={CHECKPOINT}")
print(f"rewritten={TARGET}")
