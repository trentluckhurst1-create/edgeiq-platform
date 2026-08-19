from __future__ import annotations

from decimal import Decimal, getcontext
from typing import Any


getcontext().prec = 28

METHOD_VERSION = "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2"


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _condition_number(value: Any) -> int | None:
    raw = _text(value).upper()
    if not raw:
        return None
    for token in ["FIRM", "GOOD", "SOFT", "HEAVY", "SLOW", "DEAD", "TRACK", "(", ")", "-"]:
        raw = raw.replace(token, " ")
    parts = [part for part in raw.replace("/", " ").split() if part]
    for part in parts:
        try:
            return int(float(part))
        except ValueError:
            continue
    try:
        return int(float(raw))
    except ValueError:
        return None


def _normalise_surface(surface_group: Any) -> str:
    raw = _text(surface_group).upper().replace("-", " ").replace("_", " ")
    if not raw:
        return ""
    if "AUSTRALIAN" in raw and "SYNTH" in raw:
        return "AUSTRALIAN_SYNTHETIC"
    if any(token in raw for token in ["PAKENHAM SYNTHETIC", "SOUTHSIDE PAKENHAM SYNTHETIC", "SPORTSBET PAKENHAM SYNTHETIC", "BALLARAT SYNTHETIC", "GEELONG SYNTHETIC"]):
        return "AUSTRALIAN_SYNTHETIC"
    if "SYNTH" in raw or "POLY" in raw or "TAPETA" in raw or "FIBRE" in raw or "FIBER" in raw or "ALL WEATHER" in raw:
        if any(token in raw for token in ["USA", "UK", "IRELAND", "IRE", "FRANCE", "JAPAN", "OVERSEAS"]):
            return "UNKNOWN_SYNTHETIC"
        return "AUSTRALIAN_SYNTHETIC"
    if "DIRT" in raw:
        return "DIRT"
    if "TURF" in raw or "GRASS" in raw:
        return "TURF"
    return raw


def _result(surface_group: str, condition_group: str, lps: Decimal, status: str, reason: str) -> dict[str, str]:
    spl = Decimal("1") / lps if lps else Decimal("0")
    return {
        "method_version": METHOD_VERSION,
        "surface_group": surface_group,
        "track_condition_group": condition_group,
        "lengths_per_second": f"{lps:.9f}" if lps else "",
        "seconds_per_length": f"{spl:.9f}" if lps else "",
        "status": status,
        "reason": reason,
    }


def resolve_length_conversion(surface_group: Any, track_condition_number: Any = None) -> dict[str, str]:
    surface = _normalise_surface(surface_group)
    if not surface:
        return _result("", "", Decimal("0"), "BLOCKED_UNSUPPORTED_SURFACE", "MISSING_SURFACE")
    if surface == "AUSTRALIAN_SYNTHETIC":
        return _result("AUSTRALIAN_SYNTHETIC", "STANDARD_SYNTHETIC", Decimal("6.0"), "APPROVED_AUSTRALIAN_SYNTHETIC_CONVERSION", "")
    if surface != "TURF":
        status = "BLOCKED_AMBIGUOUS_SURFACE" if surface == "UNKNOWN_SYNTHETIC" else "BLOCKED_UNSUPPORTED_SURFACE"
        return _result(surface, "", Decimal("0"), status, "UNSUPPORTED_SURFACE")
    condition_number = _condition_number(track_condition_number)
    if condition_number is None:
        return _result("TURF", "", Decimal("0"), "BLOCKED_MISSING_TURF_CONDITION", "MISSING_TRACK_CONDITION_NUMBER")
    if condition_number < 1 or condition_number > 10:
        return _result("TURF", "", Decimal("0"), "BLOCKED_UNSUPPORTED_SURFACE", "INVALID_TRACK_CONDITION_NUMBER")
    if condition_number <= 2:
        return _result("TURF", "FIRM", Decimal("6.0"), "APPROVED_TURF_CONVERSION", "")
    if condition_number <= 4:
        return _result("TURF", "GOOD", Decimal("6.0"), "APPROVED_TURF_CONVERSION", "")
    if condition_number <= 7:
        return _result("TURF", "SOFT", Decimal("5.0"), "APPROVED_TURF_CONVERSION", "")
    return _result("TURF", "HEAVY", Decimal("5.0"), "APPROVED_TURF_CONVERSION", "")
