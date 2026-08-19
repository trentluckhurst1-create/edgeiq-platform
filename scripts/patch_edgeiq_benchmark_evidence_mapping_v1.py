from __future__ import annotations

import re
from pathlib import Path


ROOT = Path.cwd()

OBSERVATION_BUILDER = (
    ROOT
    / "scripts"
    / "build_edgeiq_benchmark_observation_fact_v1.py"
)

ELIGIBILITY_BUILDER = (
    ROOT
    / "scripts"
    / "build_edgeiq_benchmark_eligibility_fact_v1.py"
)

ELIGIBILITY_SPEC = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "EDGEIQ_BENCHMARK_ELIGIBILITY_FACT_V1_SPEC.md"
)

ELIGIBILITY_CONTRACT = (
    ROOT
    / "contracts"
    / "performance-intelligence"
    / "edgeiq_benchmark_eligibility_fact_v1_contract.json"
)

ELIGIBILITY_GENERATOR = (
    ROOT
    / "scripts"
    / "create_edgeiq_benchmark_eligibility_fact_v1.py"
)


def replace_function(
    text: str,
    function_name: str,
    replacement: str,
) -> str:
    pattern = re.compile(
        rf"^def {re.escape(function_name)}\("
        rf".*?"
        rf"(?=^def |\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )

    replacement_text = replacement.rstrip() + "\n\n"

    updated, count = pattern.subn(
        lambda _match: replacement_text,
        text,
        count=1,
    )

    if count != 1:
        raise RuntimeError(
            f"Expected exactly one function named "
            f"{function_name}; replaced {count}."
        )

    return updated


def patch_observation_builder() -> None:
    text = OBSERVATION_BUILDER.read_text(
        encoding="utf-8-sig"
    )

    original = text

    marker_function = r'''
def marker_metres(row: dict[str, str]) -> int | None:
    """
    Return the exact governed distance-to-finish marker.

    Canonical Runner Sectional Fact V2.1 stores this as
    distance_to_finish_metres. distance_marker is retained only as a
    deterministic fallback for compatible historical rows.
    """
    direct = parse_int(
        first_value(
            row,
            (
                "distance_to_finish_metres",
                "sectional_marker_metres",
                "marker_metres",
            ),
        )
    )

    if direct is not None:
        return direct

    label = first_value(
        row,
        (
            "distance_marker",
            "sectional_marker",
            "sectional",
        ),
    )

    match = re.search(r"(\d+)", label)

    if not match:
        return None

    return int(match.group(1))
'''

    sectional_time_function = r'''
def sectional_time(row: dict[str, str]) -> str:
    """
    Return the canonical cumulative time from the marker to the finish.

    Canonical Runner Sectional Fact V2.1 stores this as
    cumulative_time_to_finish_seconds.
    """
    return canonical_decimal(
        first_value(
            row,
            (
                "cumulative_time_to_finish_seconds",
                "sectional_time_seconds",
                "time_seconds",
                "sectional_time",
                "time",
            ),
        )
    )
'''

    governed_distance_function = r'''
def governed_official_distance(
    winner: dict[str, str] | None,
) -> str:
    """
    Resolve official race distance only from governed full-race evidence.

    For FULL_RACE rows, the winner's reconciled split window begins at the
    race distance and finishes at zero. Partial timing windows must not be
    represented as complete official race distances.
    """
    if winner is None:
        return ""

    coverage_type = first_value(
        winner,
        ("split_coverage_type",),
    ).upper()

    full_race_flag = first_value(
        winner,
        ("full_race_split_coverage",),
    ).lower()

    start_marker = parse_int(
        first_value(
            winner,
            ("split_window_start_marker_metres",),
        )
    )

    finish_marker = parse_int(
        first_value(
            winner,
            ("split_window_finish_marker_metres",),
        )
    )

    window_distance = parse_int(
        first_value(
            winner,
            ("split_window_distance_metres",),
        )
    )

    if coverage_type != "FULL_RACE":
        return ""

    if full_race_flag not in {"true", "1", "yes"}:
        return ""

    if finish_marker != 0:
        return ""

    if window_distance is None or window_distance <= 0:
        return ""

    if (
        start_marker is not None
        and start_marker != window_distance
    ):
        return ""

    return canonical_decimal(window_distance)
'''

    text = replace_function(
        text,
        "marker_metres",
        marker_function,
    )

    text = replace_function(
        text,
        "sectional_time",
        sectional_time_function,
    )

    insertion_anchor = "def deterministic_id(race_key: str) -> str:"

    if "def governed_official_distance(" not in text:
        anchor_index = text.find(insertion_anchor)

        if anchor_index < 0:
            raise RuntimeError(
                "Could not locate deterministic_id insertion anchor."
            )

        text = (
            text[:anchor_index]
            + governed_distance_function.strip()
            + "\n\n\n"
            + text[anchor_index:]
        )

    distance_pattern = re.compile(
        r'''
        (?P<indent>[ \t]*)
        "official_distance_metres"
        \s*:\s*
        canonical_decimal
        \(
            .*?
        \)
        \s*,
        (?P<newline>\r?\n)
        (?P=indent)
        "surface"
        \s*:
        ''',
        flags=re.DOTALL | re.VERBOSE,
    )

    distance_replacement = (
        r'\g<indent>"official_distance_metres": '
        r'governed_official_distance(winner),'
        r'\g<newline>'
        r'\g<indent>"surface":'
    )

    text, distance_count = distance_pattern.subn(
        distance_replacement,
        text,
        count=1,
    )

    if distance_count != 1:
        raise RuntimeError(
            "Could not replace the official_distance_metres "
            f"output block; replacements={distance_count}."
        )

    if text == original:
        raise RuntimeError(
            "Observation builder patch produced no changes."
        )

    OBSERVATION_BUILDER.write_text(
        text,
        encoding="utf-8",
    )


def patch_eligibility_builder() -> None:
    text = ELIGIBILITY_BUILDER.read_text(
        encoding="utf-8-sig"
    )

    original_block = '''    if distance is None:
        reasons.append("MISSING_OFFICIAL_DISTANCE")
    elif distance <= 0:
        reasons.append("NON_POSITIVE_OFFICIAL_DISTANCE")
'''

    replacement_block = '''    if coverage == "FULL_RACE":
        if distance is None:
            reasons.append("MISSING_OFFICIAL_DISTANCE")
        elif distance <= 0:
            reasons.append("NON_POSITIVE_OFFICIAL_DISTANCE")
'''

    if original_block not in text:
        raise RuntimeError(
            "Could not locate universal distance eligibility block."
        )

    text = text.replace(
        original_block,
        replacement_block,
        1,
    )

    ELIGIBILITY_BUILDER.write_text(
        text,
        encoding="utf-8",
    )


def patch_eligibility_spec() -> None:
    text = ELIGIBILITY_SPEC.read_text(
        encoding="utf-8-sig"
    )

    old = '''- official distance greater than zero
- winner identity present
- winner race time greater than zero
- runner count at least 2
- unresolved runner coverage count = 0
- at least one exact winner closing sectional is available
'''

    new = '''- governed partial split-window identity is present
- winner identity present
- winner race time greater than zero
- runner count at least 2
- unresolved runner coverage count = 0
- at least one exact winner closing sectional is available

A complete official race distance is not required for
SECTIONAL_REFERENCE_ONLY classification. A partial timing window must never be
represented as the complete official race distance.
'''

    if old not in text:
        raise RuntimeError(
            "Could not locate sectional eligibility requirements "
            "in specification."
        )

    text = text.replace(old, new, 1)

    ELIGIBILITY_SPEC.write_text(
        text,
        encoding="utf-8",
    )


def patch_contract() -> None:
    import json

    payload = json.loads(
        ELIGIBILITY_CONTRACT.read_text(
            encoding="utf-8-sig"
        )
    )

    section = payload[
        "sectional_reference_eligibility"
    ]

    section[
        "requires_positive_official_distance"
    ] = False

    section[
        "requires_governed_partial_window_identity"
    ] = True

    ELIGIBILITY_CONTRACT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def patch_generator() -> None:
    text = ELIGIBILITY_GENERATOR.read_text(
        encoding="utf-8-sig"
    )

    old_contract = '''        "requires_positive_official_distance": True,
        "requires_positive_winner_race_time": True,
'''

    new_contract = '''        "requires_positive_official_distance": False,
        "requires_governed_partial_window_identity": True,
        "requires_positive_winner_race_time": True,
'''

    occurrences = text.count(old_contract)

    if occurrences < 1:
        raise RuntimeError(
            "Could not locate eligibility contract source block."
        )

    # Only the sectional contract is the second occurrence in the generated
    # source. Replace the final occurrence, preserving the full-race rule.
    position = text.rfind(old_contract)

    text = (
        text[:position]
        + new_contract
        + text[position + len(old_contract):]
    )

    old_logic = '''    if distance is None:
        reasons.append("MISSING_OFFICIAL_DISTANCE")
    elif distance <= 0:
        reasons.append("NON_POSITIVE_OFFICIAL_DISTANCE")
'''

    new_logic = '''    if coverage == "FULL_RACE":
        if distance is None:
            reasons.append("MISSING_OFFICIAL_DISTANCE")
        elif distance <= 0:
            reasons.append("NON_POSITIVE_OFFICIAL_DISTANCE")
'''

    if old_logic not in text:
        raise RuntimeError(
            "Could not locate generated eligibility distance logic."
        )

    text = text.replace(
        old_logic,
        new_logic,
        1,
    )

    old_spec = '''- official distance greater than zero
- winner identity present
- winner race time greater than zero
- runner count at least 2
- unresolved runner coverage count = 0
- at least one exact winner closing sectional is available
'''

    new_spec = '''- governed partial split-window identity is present
- winner identity present
- winner race time greater than zero
- runner count at least 2
- unresolved runner coverage count = 0
- at least one exact winner closing sectional is available

A complete official race distance is not required for
SECTIONAL_REFERENCE_ONLY classification. A partial timing window must never be
represented as the complete official race distance.
'''

    if old_spec not in text:
        raise RuntimeError(
            "Could not locate generated eligibility specification block."
        )

    text = text.replace(
        old_spec,
        new_spec,
        1,
    )

    ELIGIBILITY_GENERATOR.write_text(
        text,
        encoding="utf-8",
    )


patch_observation_builder()
patch_eligibility_builder()
patch_eligibility_spec()
patch_contract()
patch_generator()

print("Patched:")
print(
    "  scripts/build_edgeiq_benchmark_observation_fact_v1.py"
)
print(
    "  scripts/build_edgeiq_benchmark_eligibility_fact_v1.py"
)
print(
    "  docs/performance-intelligence/"
    "EDGEIQ_BENCHMARK_ELIGIBILITY_FACT_V1_SPEC.md"
)
print(
    "  contracts/performance-intelligence/"
    "edgeiq_benchmark_eligibility_fact_v1_contract.json"
)
print(
    "  scripts/create_edgeiq_benchmark_eligibility_fact_v1.py"
)
