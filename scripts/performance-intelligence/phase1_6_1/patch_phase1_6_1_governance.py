from pathlib import Path

path = Path(
    r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
    r"\scripts\performance-intelligence\phase1_6_1"
    r"\build_edgeiq_corrected_performance_facts_phase1_6_1.py"
)

text = path.read_text(encoding="utf-8-sig")

old = '''                unit_state = clean(
                    contract.get(
                        "unit_state"
                    )
                )

                source_unit = clean(
                    contract.get(
                        "source_time_unit"
                    )
                )

                governed_seconds = clean(
                    contract.get(
                        "governed_time_seconds"
                    )
                )

                race_eligible = bool_value(
                    contract.get(
                        "benchmark_eligible"
                    )
                )'''

new = '''                profile_unit_state = clean(
                    contract.get(
                        "unit_state"
                    )
                )

                raw_time = clean(
                    row.get(
                        "raw_winning_time"
                    )
                )

                governed_seconds = clean(
                    row.get(
                        "governed_time_seconds"
                    )
                )

                distance_metres = clean(
                    row.get(
                        "distance_metres"
                    )
                )

                if (
                    consistency_state
                    in {
                        "CONSISTENT_COMPLETE",
                        "CONSISTENT_WITH_MISSING",
                    }
                    and raw_time
                    and governed_seconds
                    and distance_metres
                ):
                    unit_state = (
                        "CENTISECONDS_CONFIRMED"
                    )
                    source_unit = (
                        "CENTISECONDS"
                    )
                    race_eligible = True

                elif consistency_state == (
                    "NO_TIME_AVAILABLE"
                ):
                    unit_state = (
                        "TIME_UNAVAILABLE"
                    )
                    source_unit = ""
                    race_eligible = False

                elif consistency_state == (
                    "MULTIPLE_NON_BLANK_VALUES"
                ):
                    unit_state = (
                        "TIME_CONFLICT_QUARANTINED"
                    )
                    source_unit = ""
                    race_eligible = False

                else:
                    unit_state = (
                        profile_unit_state
                        or
                        "TIME_UNIT_UNAVAILABLE"
                    )
                    source_unit = ""
                    race_eligible = False'''

if old not in text:
    raise SystemExit("PHASE1_6_1_CONTRACT_BLOCK_NOT_FOUND")

text = text.replace(old, new, 1)

old = '''            performance_eligible = (
                source_quality_state == "COMPLETE"
                and race_eligible
                and consistency_state
                in {
                    "CONSISTENT_COMPLETE",
                    "CONSISTENT_WITH_MISSING",
                }
                and unit_state
                == "CENTISECONDS_CONFIRMED"
            )'''

new = '''            performance_eligible = bool(
                source_quality_state == "COMPLETE"
                and race_eligible
                and consistency_state
                in {
                    "CONSISTENT_COMPLETE",
                    "CONSISTENT_WITH_MISSING",
                }
                and unit_state
                == "CENTISECONDS_CONFIRMED"
                and clean(
                    row.get(
                        "distance_metres"
                    )
                )
                and clean(
                    row.get(
                        "governed_time_seconds"
                    )
                )
            )'''

if old not in text:
    raise SystemExit("PHASE1_6_1_ELIGIBILITY_BLOCK_NOT_FOUND")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("PHASE1_6_1_GOVERNANCE_PATCH_APPLIED")
