from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from edgeiq_length_conversion_method_v1 import resolve_length_conversion


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard" / "edgeiq_length_conversion_method_v2_tests.json"


def assert_equal(name: str, actual: object, expected: object, failures: list[str]) -> None:
    if actual != expected:
        failures.append(f"{name}: expected {expected!r}; got {actual!r}")


def main() -> int:
    failures: list[str] = []
    expected_groups = {
        1: ("FIRM", "6.000000000"),
        2: ("FIRM", "6.000000000"),
        3: ("GOOD", "6.000000000"),
        4: ("GOOD", "6.000000000"),
        5: ("SOFT", "5.000000000"),
        6: ("SOFT", "5.000000000"),
        7: ("SOFT", "5.000000000"),
        8: ("HEAVY", "5.000000000"),
        9: ("HEAVY", "5.000000000"),
        10: ("HEAVY", "5.000000000"),
    }
    test_count = 0
    for condition, (group, lps) in expected_groups.items():
        test_count += 1
        resolved = resolve_length_conversion("TURF", condition)
        assert_equal(f"turf_{condition}_status", resolved["status"], "APPROVED_TURF_CONVERSION", failures)
        assert_equal(f"turf_{condition}_group", resolved["track_condition_group"], group, failures)
        assert_equal(f"turf_{condition}_lps", resolved["lengths_per_second"], lps, failures)
    for surface, condition in [
        ("AUSTRALIAN_SYNTHETIC", ""),
        ("Southside Pakenham Synthetic", None),
        ("Pakenham Synthetic", "GOOD 4"),
        ("Sportsbet Pakenham Synthetic", 9),
        ("Ballarat Synthetic", ""),
        ("Geelong Synthetic", ""),
    ]:
        test_count += 1
        resolved = resolve_length_conversion(surface, condition)
        assert_equal(f"{surface}_status", resolved["status"], "APPROVED_AUSTRALIAN_SYNTHETIC_CONVERSION", failures)
        assert_equal(f"{surface}_surface", resolved["surface_group"], "AUSTRALIAN_SYNTHETIC", failures)
        assert_equal(f"{surface}_group", resolved["track_condition_group"], "STANDARD_SYNTHETIC", failures)
        assert_equal(f"{surface}_lps", resolved["lengths_per_second"], "6.000000000", failures)
    for surface, condition, expected_status in [
        ("Pakenham Turf", 4, "APPROVED_TURF_CONVERSION"),
        ("USA Synthetic", "", "BLOCKED_AMBIGUOUS_SURFACE"),
        ("DIRT", "", "BLOCKED_UNSUPPORTED_SURFACE"),
        ("", "", "BLOCKED_UNSUPPORTED_SURFACE"),
        ("TURF", "", "BLOCKED_MISSING_TURF_CONDITION"),
    ]:
        test_count += 1
        resolved = resolve_length_conversion(surface, condition)
        assert_equal(f"{surface}_status", resolved["status"], expected_status, failures)
    test_count += 1
    synthetic = resolve_length_conversion("AUSTRALIAN_SYNTHETIC", "")
    assert_equal("precision_spl", synthetic["seconds_per_length"], f"{(Decimal('1') / Decimal('6')).quantize(Decimal('0.000000001'))}", failures)
    payload = {"method_version": synthetic["method_version"], "tests": test_count, "passed": len(failures) == 0, "failures": failures}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
