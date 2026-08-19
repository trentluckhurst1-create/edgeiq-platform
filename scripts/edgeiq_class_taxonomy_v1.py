from __future__ import annotations

import math
import re
from typing import Iterable


def norm(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def normalized_class_text(value: object) -> str:
    text = norm(value)
    if not text:
        return ""
    text = text.replace("’", "'")
    text = text.replace("&", " & ")
    text = text.replace("/", " ")
    text = text.replace("-", " ")
    text = text.replace("(", " ")
    text = text.replace(")", " ")
    text = re.sub(r"[,:;]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strip_qualifiers(text: str) -> str:
    cleaned = f" {text} "
    qualifier_patterns = [
        r"\b\dYO\b",
        r"\b\dY\b",
        r"\b\dUP\b",
        r"\b\d\s*&\s*\dYO\b",
        r"\b\d\s*&\s*UP\b",
        r"\bAGE\b",
        r"\bOPEN\s+AGE\b",
        r"\bCOLTS\b",
        r"\bGELDINGS\b",
        r"\bENTIRES\b",
        r"\bFILLIES\b",
        r"\bMARES\b",
        r"\bF&M\b",
        r"\bF \& M\b",
        r"\bC&G\b",
        r"\bC \& G\b",
        r"\bCG&E\b",
        r"\bCG \& E\b",
        r"\bF\b",
        r"\bM\b",
    ]
    for pattern in qualifier_patterns:
        cleaned = re.sub(pattern, " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def canonicalize_race_class(value: object) -> tuple[str, str]:
    text = normalized_class_text(value)
    if not text:
        return "UNKNOWN", "EMPTY_CLASS"

    benchmark_match = re.search(r"\bBM\s*(\d{2,3})\b", text)
    if benchmark_match:
        return f"BM{benchmark_match.group(1)}", "BENCHMARK_SIGNAL"

    rating_band_match = re.search(r"\b(?:0|O)\s*(?:TO|-)\s*(\d{2,3})\b", text)
    if rating_band_match:
        return f"BM{rating_band_match.group(1)}", "RATING_BAND_SIGNAL"

    if text in {"MDN", "MAIDEN", "2YO MDN", "3YO MDN", "2YO MAIDEN", "3YO MAIDEN"} or "MAIDEN" in text:
        return "MAIDEN", "MAIDEN_SIGNAL"

    class_match = re.search(r"\b(?:CLASS|CL|C)\s*([1-6])\b", text)
    if class_match:
        return f"CLASS {class_match.group(1)}", "CLASS_SIGNAL"

    group_match = re.search(r"\bGROUP\s*([123])\b|\bG([123])\b", text)
    if group_match:
        group_no = group_match.group(1) or group_match.group(2)
        return f"GROUP {group_no}", "GROUP_SIGNAL"

    if "LISTED" in text:
        return "LISTED", "LISTED_SIGNAL"

    if re.search(r"\bSET\s*WEIGHTS(?:\s*AND\s*PENALTIES)?\b|\bSWP\b|\bSW\b", text):
        return "SET WEIGHTS", "SET_WEIGHTS_SIGNAL"

    if re.search(r"\bHANDICAP\b|\bHCP\b", text):
        return "HANDICAP", "HANDICAP_SIGNAL"

    if re.search(r"\bOPEN\b", text):
        return "OPEN", "OPEN_SIGNAL"

    for restricted_class in ["HIGHWAY", "MIDWAY", "COUNTRY", "PROVINCIAL", "WESTSPEED"]:
        if restricted_class in text:
            return restricted_class, f"{restricted_class}_SIGNAL"

    stripped = _strip_qualifiers(text)
    if stripped == "UNKNOWN":
        return "HANDICAP", "UNKNOWN_FALLBACK_TO_HANDICAP"
    if not stripped:
        return "UNKNOWN", "QUALIFIER_STRIPPED_TO_EMPTY"
    if stripped != text:
        return stripped, "QUALIFIER_STRIPPED_FALLBACK"
    return text, "RAW_FALLBACK"


def canonical_class_family(value: object) -> str:
    clean = norm(value)
    if clean in {"GROUP 1", "GROUP 2", "GROUP 3", "LISTED"}:
        return "BLACKTYPE"
    if clean.startswith("BM"):
        return "JUMPS_OR_HIGHWEIGHT" if clean == "BM120" else "BENCHMARK"
    if clean.startswith("CLASS "):
        return "CLASS"
    if clean == "MAIDEN":
        return "MAIDEN"
    if clean in {"HIGHWAY", "MIDWAY", "COUNTRY", "PROVINCIAL", "WESTSPEED"}:
        return "REGIONAL_RESTRICTED"
    if clean in {"HANDICAP", "UNKNOWN"}:
        return "UNRESOLVED"
    return "OTHER"


def canonicalization_confidence(raw_value: object, canonical_value: str, reason: str) -> str:
    raw_text = normalized_class_text(raw_value)
    if reason in {
        "BENCHMARK_SIGNAL",
        "RATING_BAND_SIGNAL",
        "MAIDEN_SIGNAL",
        "CLASS_SIGNAL",
        "GROUP_SIGNAL",
        "LISTED_SIGNAL",
        "SET_WEIGHTS_SIGNAL",
        "HANDICAP_SIGNAL",
        "OPEN_SIGNAL",
        "HIGHWAY_SIGNAL",
        "MIDWAY_SIGNAL",
        "COUNTRY_SIGNAL",
        "PROVINCIAL_SIGNAL",
        "WESTSPEED_SIGNAL",
    }:
        return "UNCHANGED" if raw_text == canonical_value else "HIGH"
    if reason in {"RAW_FALLBACK", "QUALIFIER_STRIPPED_FALLBACK"}:
        return "MEDIUM"
    return "LOW"


def class_par_lookup(par_classes: Iterable[object]) -> set[str]:
    return {canonicalize_race_class(value)[0] for value in par_classes if norm(value)}


def class_par_match_status(canonical_class: str, available_par_classes: set[str]) -> str:
    if not available_par_classes:
        return "CLASS_PARS_UNAVAILABLE"
    if canonical_class in available_par_classes:
        return "MATCHED_CLASS_PAR"
    if canonical_class == "HANDICAP" and "BM70" in available_par_classes:
        return "FALLBACK_CLASS_PAR_AVAILABLE_FROM_BM70"
    return "MISSING_CLASS_PAR"
