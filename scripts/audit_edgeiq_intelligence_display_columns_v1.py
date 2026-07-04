from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "public" / "data"

RUNNER_BOARD_FILE = DATA_DIR / "edgeiq_live_runner_board_v1.csv"
RUNNER_INTEL_FILE = DATA_DIR / "edgeiq_runner_intelligence_v1.csv"
HORSE_DRAWER_FILE = DATA_DIR / "edgeiq_horse_intelligence_drawer_v1.csv"
BET_QUALITY_FILE = DATA_DIR / "edgeiq_live_bet_quality_v1_1.csv"
INTELLIGENCE_SCORE_FILE = DATA_DIR / "edgeiq_live_intelligence_score_v1.csv"
LIMITED_DATA_FILE = DATA_DIR / "edgeiq_limited_data_market_adjusted_v1.csv"

AUDIT_FILE = DATA_DIR / "edgeiq_intelligence_display_columns_audit_v1.csv"
SUMMARY_FILE = DATA_DIR / "edgeiq_intelligence_display_columns_summary_v1.csv"


def text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def to_float(value: object) -> Optional[float]:
    raw = text(value).replace("$", "").replace("%", "").replace(",", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def clean_track(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def clean_horse(value: object) -> str:
    raw = text(value).upper()
    stripped = []
    depth = 0
    for ch in raw:
        if ch == "(":
            depth += 1
            continue
        if ch == ")":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            stripped.append(ch)
    return "".join(ch for ch in "".join(stripped) if ch.isalnum())


def clean_horse_loose(value: object) -> str:
    key = clean_horse(value)
    for suffix in ("NZ", "GB", "IRE", "FR", "USA", "JPN", "AUS"):
        if key.endswith(suffix):
            return key[: -len(suffix)]
    return key


def race_date(row: Dict[str, str]) -> str:
    return text(row.get("race_date") or row.get("meeting_date") or row.get("date") or row.get("raceDate"))


def track(row: Dict[str, str]) -> str:
    return text(row.get("track") or row.get("meeting") or row.get("meeting_name"))


def race_no(row: Dict[str, str]) -> str:
    return text(row.get("race_no") or row.get("raceNo") or row.get("race_number") or row.get("race"))


def horse_name(row: Dict[str, str]) -> str:
    return text(row.get("horse") or row.get("horseName") or row.get("runner") or row.get("runner_name"))


def candidate_horse_keys(row: Dict[str, str]) -> List[str]:
    values = [
        clean_horse(row.get("horse_key", "")),
        clean_horse(row.get("horse_canon", "")),
        clean_horse(horse_name(row)),
        clean_horse_loose(row.get("horse_key", "")),
        clean_horse_loose(row.get("horse_canon", "")),
        clean_horse_loose(horse_name(row)),
    ]
    ordered: List[str] = []
    for value in values:
        if value and value not in ordered:
            ordered.append(value)
    return ordered


def row_keys(row: Dict[str, str]) -> List[str]:
    date = race_date(row)
    t = clean_track(track(row))
    r = race_no(row)
    return [f"{date}|{t}|{r}|{horse_key}" for horse_key in candidate_horse_keys(row)]


def load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_index(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    index: Dict[str, Dict[str, str]] = {}
    for row in rows:
        for key in row_keys(row):
            index.setdefault(key, row)
    return index


def find_match(index: Dict[str, Dict[str, str]], row: Dict[str, str]) -> Optional[Dict[str, str]]:
    for key in row_keys(row):
        if key in index:
            return index[key]
    return None


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def coalesce_num(*values: Optional[float]) -> Optional[float]:
    for value in values:
        if value is not None:
            return value
    return None


def is_scratched(row: Dict[str, str]) -> bool:
    blob = " ".join(
        [
            text(row.get("display_decision")),
            text(row.get("runner_status")),
            text(row.get("tab_fixed_betting_status")),
            text(row.get("scratch_status")),
            text(row.get("is_scratched")),
            text(row.get("execution_action")),
            text(row.get("decision")),
        ]
    ).upper()
    if "SCRATCH" in blob:
        return True
    return text(row.get("is_scratched")).upper() in {"YES", "Y", "TRUE", "1"}


def is_fallback(row: Dict[str, str]) -> bool:
    status = text(row.get("V6_1_RESEARCH_price_status")).upper()
    return "FALLBACK" in status


def win_pct(row: Dict[str, str]) -> Optional[float]:
    value = to_float(row.get("win_pct"))
    if value is not None:
        return value
    fair = to_float(row.get("fair_price"))
    if fair and fair > 0:
        return 100.0 / fair
    return None


def edge_pct(row: Dict[str, str]) -> Optional[float]:
    return coalesce_num(
        to_float(row.get("display_edge_pct")),
        to_float(row.get("edge_pct")),
        to_float(row.get("ui_edge_pct")),
    )


def first_num(row: Optional[Dict[str, str]], keys: List[str]) -> Optional[float]:
    if row is None:
        return None
    for key in keys:
        value = to_float(row.get(key))
        if value is not None:
            return value
    return None


def first_text(row: Optional[Dict[str, str]], keys: List[str]) -> str:
    if row is None:
        return ""
    for key in keys:
        value = text(row.get(key))
        if value:
            return value
    return ""


def score_label(score: float) -> str:
    if score >= 75:
        return "VERY HIGH"
    if score >= 60:
        return "HIGH"
    if score >= 45:
        return "MEDIUM"
    if score >= 30:
        return "LOW"
    return "VERY LOW"


def normalize_grade(label: str) -> str:
    upper = text(label).upper()
    if not upper or upper == "—":
        return ""
    if "SCRATCH" in upper:
        return "SCRATCHED"
    if "LOW DATA" in upper:
        return "LOW DATA"
    if "VERY HIGH" in upper:
        return "VERY HIGH"
    if "HIGH" in upper or "ELITE" in upper or "STRONG" in upper:
        return "HIGH"
    if "MEDIUM" in upper or "WATCH" in upper or "NEUTRAL" in upper:
        return "MEDIUM"
    if "LOW" in upper or "WEAK" in upper or "POOR" in upper or "NEGATIVE" in upper:
        return "LOW"
    if "PASS" in upper:
        return "MEDIUM"
    return upper


def compute_limited_score(
    row: Dict[str, str],
    limited_row: Optional[Dict[str, str]],
    bet_row: Optional[Dict[str, str]],
    intel_row: Optional[Dict[str, str]],
) -> tuple[str, str]:
    if is_scratched(row):
        return "", "SCRATCHED"

    raw_limited = (
        coalesce_num(
            first_num(limited_row, ["limited_data_factor_score_v1", "limited_data_score_v1", "limited_score"]),
            first_num(row, ["limited_data_factor_score_v1", "limited_data_score_v1", "limited_score"]),
        )
    )
    if raw_limited is not None:
        return str(int(clamp(round(raw_limited), 1, 100))), "LIMITED_DATA_CURRENT"

    bet_quality_score = first_num(bet_row, ["bet_quality_score_v1_1", "bet_quality_score"])
    if bet_quality_score is not None:
        return str(int(clamp(round(bet_quality_score), 1, 100))), "BET_QUALITY_CURRENT"

    intelligence_score = first_num(intel_row, ["intelligence_score_v1"])
    if intelligence_score is not None:
        return str(int(clamp(round(intelligence_score), 1, 100))), "INTELLIGENCE_SCORE_CURRENT"

    win_value = win_pct(row) or 0.0
    edge_value = edge_pct(row) or 0.0
    base = 35.0
    win_component = clamp(win_value * 1.8, 0, 25)
    edge_component = clamp(max(edge_value, 0.0) * 0.18, 0, 25)
    negative_penalty = clamp(abs(edge_value) * 0.12, 0, 20) if edge_value < 0 else 0.0
    fallback_penalty = 12.0 if is_fallback(row) else 0.0
    score = clamp(round(base + win_component + edge_component - negative_penalty - fallback_penalty), 1, 100)
    return str(int(score)), "COMPOSITE_FALLBACK"


def compute_grade(
    row: Dict[str, str],
    limited_score_value: str,
    limited_score_source: str,
    bet_row: Optional[Dict[str, str]],
) -> tuple[str, str]:
    if is_scratched(row):
        return "SCRATCHED", "SCRATCHED"

    bet_quality_score = first_num(bet_row, ["bet_quality_score_v1_1", "bet_quality_score"])
    if bet_quality_score is not None:
        return score_label(bet_quality_score), "BET_QUALITY_CURRENT"

    bet_quality_grade = normalize_grade(first_text(bet_row, ["bet_quality_grade_v1_1", "bet_quality_grade"]))
    if bet_quality_grade:
        return bet_quality_grade, "BET_QUALITY_CURRENT_GRADE"

    score = int(limited_score_value or "0")
    edge_value = edge_pct(row) or 0.0
    win_value = win_pct(row) or 0.0
    if is_fallback(row) and not (edge_value >= 50 and win_value >= 8):
        if score >= 45:
            return "MEDIUM", limited_score_source
        if score >= 30:
            return "LOW", limited_score_source
        return "VERY LOW", limited_score_source
    return score_label(score), limited_score_source


def compute_bet_quality(
    row: Dict[str, str],
    limited_score_value: str,
    bet_row: Optional[Dict[str, str]],
) -> tuple[str, str]:
    if is_scratched(row):
        return "SCRATCHED", "SCRATCHED"

    bet_quality_score = first_num(bet_row, ["bet_quality_score_v1_1", "bet_quality_score"])
    if bet_quality_score is not None:
        return score_label(bet_quality_score), "BET_QUALITY_CURRENT"

    bet_quality_grade = normalize_grade(first_text(bet_row, ["bet_quality_grade_v1_1", "bet_quality_grade"]))
    if bet_quality_grade:
        return bet_quality_grade, "BET_QUALITY_CURRENT_GRADE"

    score = int(limited_score_value or "0")
    return score_label(score), "LIMITED_SCORE_DERIVED"


def compute_bet(row: Dict[str, str]) -> str:
    if is_scratched(row):
        return "SCRATCHED"

    decision_value = text(row.get("display_decision") or row.get("execution_action") or row.get("decision")).upper()
    edge_value = edge_pct(row) or 0.0

    if decision_value in {"NO MODEL", "NO_MODEL", "NO MARKET", "NO_MARKET"}:
        return "WAIT"
    if decision_value == "WATCH" and edge_value >= 18:
        return "BET"
    if decision_value == "WATCH":
        return "WATCH"
    if decision_value == "LEAN":
        return "LEAN"
    if decision_value in {"PASS", "UNDERLAY"}:
        return "PASS"
    if not decision_value:
        return "WAIT"
    return decision_value


def compute_limited_decision(row: Dict[str, str], limited_row: Optional[Dict[str, str]], limited_score_value: str) -> tuple[str, str]:
    if is_scratched(row):
        return "SCRATCHED", "SCRATCHED"

    existing = first_text(limited_row, ["limited_data_decision_v1"]) or first_text(row, ["limited_data_decision_v1"])
    if existing:
        return existing.replace("_", " ").upper(), "LIMITED_DATA_CURRENT"

    score = int(limited_score_value or "0")
    edge_value = edge_pct(row) or 0.0

    if edge_value < 0:
        return "PASS", "SCORE_RULES"
    if score >= 65 and edge_value >= 18:
        return "MODEL", "SCORE_RULES"
    if score >= 50 and edge_value >= 10:
        return "WATCH", "SCORE_RULES"
    if is_fallback(row) and score < 60:
        return "LOW DATA", "SCORE_RULES"
    if score >= 40 and edge_value > 0:
        return "PASS", "SCORE_RULES"
    return "PASS", "SCORE_RULES"


def counter_string(counter: Counter, top_n: int = 10) -> str:
    parts = [f"{key}:{value}" for key, value in counter.most_common(top_n)]
    return "|".join(parts)


def main() -> None:
    runner_rows = load_csv(RUNNER_BOARD_FILE)
    runner_intel_rows = load_csv(RUNNER_INTEL_FILE)
    horse_drawer_rows = load_csv(HORSE_DRAWER_FILE)
    bet_quality_rows = load_csv(BET_QUALITY_FILE)
    intelligence_score_rows = load_csv(INTELLIGENCE_SCORE_FILE)
    limited_data_rows = load_csv(LIMITED_DATA_FILE)

    runner_intel_index = build_index(runner_intel_rows)
    horse_drawer_index = build_index(horse_drawer_rows)
    bet_quality_index = build_index(bet_quality_rows)
    intelligence_score_index = build_index(intelligence_score_rows)
    limited_data_index = build_index(limited_data_rows)
    runner_index = build_index(runner_rows)

    audit_rows: List[Dict[str, str]] = []

    for row in runner_rows:
        runner_intel = find_match(runner_intel_index, row)
        horse_drawer = find_match(horse_drawer_index, row)
        bet_quality = find_match(bet_quality_index, row)
        intelligence_score = find_match(intelligence_score_index, row)
        limited_data = find_match(limited_data_index, row)

        display_limited_score, limited_score_source = compute_limited_score(row, limited_data, bet_quality, intelligence_score)
        display_grade, grade_source = compute_grade(row, display_limited_score or "0", limited_score_source, bet_quality)
        display_bet_quality, bet_quality_source = compute_bet_quality(row, display_limited_score or "0", bet_quality)
        display_bet = compute_bet(row)
        display_limited_decision, limited_decision_source = compute_limited_decision(row, limited_data, display_limited_score or "0")

        audit_rows.append(
            {
                "race_date": race_date(row),
                "track": track(row),
                "race_no": race_no(row),
                "horse": horse_name(row),
                "horse_key": text(row.get("horse_key")),
                "runner_status": text(row.get("runner_status")),
                "display_decision": text(row.get("display_decision")),
                "win_pct": text(row.get("win_pct")),
                "fair_price": text(row.get("fair_price")),
                "live_price": text(row.get("live_price")),
                "display_edge_pct": text(row.get("display_edge_pct") or row.get("edge_pct") or row.get("ui_edge_pct")),
                "V6_1_RESEARCH_price_status": text(row.get("V6_1_RESEARCH_price_status")),
                "has_runner_intel": "YES" if runner_intel else "NO",
                "runner_confidence_score": text(runner_intel.get("confidence_score") if runner_intel else ""),
                "runner_sectional_weapon_score": text(runner_intel.get("sectional_weapon_score") if runner_intel else ""),
                "runner_late_power_index": text(runner_intel.get("late_power_index") if runner_intel else ""),
                "runner_projected_spd": text(runner_intel.get("projected_spd") if runner_intel else ""),
                "has_horse_drawer": "YES" if horse_drawer else "NO",
                "drawer_track_fit_score": text(horse_drawer.get("track_fit_score") if horse_drawer else ""),
                "drawer_track_fit_band": text(horse_drawer.get("track_fit_band") if horse_drawer else ""),
                "drawer_confidence_score": text(horse_drawer.get("confidence_score") if horse_drawer else ""),
                "drawer_late_power_index": text(horse_drawer.get("late_power_index") if horse_drawer else ""),
                "drawer_sectional_weapon_score": text(horse_drawer.get("sectional_weapon_score") if horse_drawer else ""),
                "has_bet_quality": "YES" if bet_quality else "NO",
                "bet_quality_score": text(first_num(bet_quality, ["bet_quality_score_v1_1", "bet_quality_score"])),
                "bet_quality_grade": text(first_text(bet_quality, ["bet_quality_grade_v1_1", "bet_quality_grade"])),
                "bet_quality_decision": text(first_text(bet_quality, ["bet_quality_status_v1_1", "execution_action", "decision"])),
                "has_intelligence_score": "YES" if intelligence_score else "NO",
                "intelligence_score": text(first_num(intelligence_score, ["intelligence_score_v1"])),
                "intelligence_score_band": text(first_text(intelligence_score, ["intelligence_band_v1"])),
                "display_bet": display_bet,
                "display_grade": display_grade,
                "display_limited_score": display_limited_score,
                "display_limited_decision": display_limited_decision,
                "display_bet_quality": display_bet_quality,
                "limited_score_source": limited_score_source,
                "grade_source": grade_source,
                "bet_quality_source": bet_quality_source,
                "limited_decision_source": limited_decision_source,
            }
        )

    with AUDIT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0].keys()) if audit_rows else [])
        if audit_rows:
            writer.writeheader()
            writer.writerows(audit_rows)

    total_rows = len(audit_rows)
    active_rows = sum(1 for row in audit_rows if text(row["runner_status"]).upper() == "ACTIVE")
    scratched_rows = sum(1 for row in audit_rows if "SCRATCH" in text(row["runner_status"]).upper())
    research_rated_rows = sum(1 for row in audit_rows if "RESEARCH_RATED" in text(row["V6_1_RESEARCH_price_status"]).upper())
    fallback_rows = sum(1 for row in audit_rows if "FALLBACK" in text(row["V6_1_RESEARCH_price_status"]).upper())

    limited_score_counter = Counter(row["display_limited_score"] for row in audit_rows if row["display_limited_score"])
    grade_counter = Counter(row["display_grade"] for row in audit_rows if row["display_grade"])
    bet_quality_counter = Counter(row["display_bet_quality"] for row in audit_rows if row["display_bet_quality"])
    limited_decision_counter = Counter(row["display_limited_decision"] for row in audit_rows if row["display_limited_decision"])

    rows_with_limited_score_70 = sum(1 for row in audit_rows if row["display_limited_score"] == "70")
    rows_using_confidence_score_70 = sum(
        1
        for row in audit_rows
        if row["display_limited_score"] == "70"
        and row["runner_confidence_score"] == "70"
    )
    rows_using_fallback_formula = sum(1 for row in audit_rows if row["limited_score_source"] == "COMPOSITE_FALLBACK")
    rows_using_real_bet_quality = sum(
        1
        for row in audit_rows
        if row["limited_score_source"] == "BET_QUALITY_CURRENT" or row["bet_quality_source"].startswith("BET_QUALITY_CURRENT")
    )

    stale_bet_quality_rows = sum(1 for row in bet_quality_rows if find_match(runner_index, row) is None)
    stale_intelligence_score_rows = sum(1 for row in intelligence_score_rows if find_match(runner_index, row) is None)

    summary_rows = [
        {"metric": "total_rows", "value": total_rows},
        {"metric": "active_rows", "value": active_rows},
        {"metric": "scratched_rows", "value": scratched_rows},
        {"metric": "research_rated_rows", "value": research_rated_rows},
        {"metric": "fallback_rows", "value": fallback_rows},
        {"metric": "limited_score_distinct_count", "value": len(limited_score_counter)},
        {"metric": "limited_score_top_values", "value": counter_string(limited_score_counter, top_n=15)},
        {"metric": "grade_distribution", "value": counter_string(grade_counter, top_n=15)},
        {"metric": "bet_quality_distribution", "value": counter_string(bet_quality_counter, top_n=15)},
        {"metric": "limited_decision_distribution", "value": counter_string(limited_decision_counter, top_n=15)},
        {"metric": "rows_with_limited_score_70", "value": rows_with_limited_score_70},
        {"metric": "rows_using_confidence_score_70", "value": rows_using_confidence_score_70},
        {"metric": "rows_using_fallback_formula", "value": rows_using_fallback_formula},
        {"metric": "rows_using_real_bet_quality", "value": rows_using_real_bet_quality},
        {"metric": "stale_bet_quality_rows", "value": stale_bet_quality_rows},
        {"metric": "stale_intelligence_score_rows", "value": stale_intelligence_score_rows},
    ]

    with SUMMARY_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(summary_rows)

    print("[EDGEIQ_INTELLIGENCE_DISPLAY_COLUMNS_AUDIT_V1] COMPLETE")
    print(f"total_rows={total_rows}")
    print(f"active_rows={active_rows}")
    print(f"scratched_rows={scratched_rows}")
    print(f"limited_score_distinct_count={len(limited_score_counter)}")
    print(f"rows_with_limited_score_70={rows_with_limited_score_70}")
    print(f"rows_using_confidence_score_70={rows_using_confidence_score_70}")
    print(f"rows_using_fallback_formula={rows_using_fallback_formula}")
    print(f"rows_using_real_bet_quality={rows_using_real_bet_quality}")
    print(f"stale_bet_quality_rows={stale_bet_quality_rows}")
    print(f"stale_intelligence_score_rows={stale_intelligence_score_rows}")
    print(f"wrote={AUDIT_FILE}")
    print(f"wrote={SUMMARY_FILE}")


if __name__ == "__main__":
    main()
