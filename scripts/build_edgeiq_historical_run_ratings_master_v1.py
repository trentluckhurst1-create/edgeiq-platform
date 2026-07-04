from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

WAREHOUSE_PATH = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"
TRACK_ALIAS_PATH = DATA / "edgeiq_track_alias_bridge_v1.csv"
PERF_V61_PATH = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
RUN_V3_PATH = DATA / "edgeiq_historical_run_rating_v3.csv"
RUN_RATINGS_V1_PATH = DATA / "run_ratings_v1.csv"
ALL_RUNS_RATED_PATH = DATA / "all_horse_runs_rated.csv"
RACE_STRENGTH_PATH = DATA / "edgeiq_race_strength_history_v1.csv"

OUT_PATH = DATA / "edgeiq_historical_run_ratings_master_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_historical_run_ratings_master_v1_summary.csv"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper_text(value: object) -> str:
    return safe_text(value).upper()


def normalize_spaces(value: object) -> str:
    return re.sub(r"\s+", " ", safe_text(value)).strip()


def compact(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", upper_text(value))


def normalize_horse(value: object) -> str:
    text = upper_text(value)
    text = re.sub(r"\([^)]*\)", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalize_track_basic(value: object) -> str:
    text = upper_text(value)
    if not text:
        return ""
    replacements = {
        "SPORTSBET-": "",
        "SPORTSBET ": "",
        "BET365 ": "",
        "LADBROKES ": "",
        "TAB ": "",
        "THE VALLEY": "MOONEE VALLEY",
        "MT V": "MOONEE VALLEY",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return normalize_spaces(text)


def parse_float(value: object) -> float | None:
    text = safe_text(value)
    if not text:
        return None
    text = text.replace("$", "").replace(",", "").replace("KG", "").replace("kg", "")
    if upper_text(text) in {"-", "--", "N/A", "SCR", "DNS", "DNF"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        number = float(match.group(0))
    except ValueError:
        return None
    return None if math.isnan(number) else number


def normalize_distance(value: object) -> str:
    number = parse_float(value)
    return "" if number is None else str(int(round(number)))


def normalize_race_no(value: object) -> str:
    text = safe_text(value)
    if not text:
        return ""
    match = re.search(r"\d+", text)
    return match.group(0) if match else text.upper()


def normalize_finish(value: object) -> str:
    text = upper_text(value)
    if not text:
        return ""
    if text in {"SCR", "SCRATCHED", "LATE SCRATCHED", "LATESCRATCHED", "DNS", "VAC"}:
        return text
    match = re.search(r"\d+", text)
    return match.group(0) if match else text


def numeric_finish(value: object) -> int | None:
    text = normalize_finish(value)
    if not text or text in {"SCR", "SCRATCHED", "LATE SCRATCHED", "LATESCRATCHED", "DNS", "VAC"}:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def canonical_condition(value: object) -> str:
    text = upper_text(value)
    if not text:
        return ""
    if text.startswith("GOOD"):
        return text.replace("GOOD ", "GOOD")
    if text.startswith("SOFT"):
        return text.replace("SOFT ", "SOFT")
    if text.startswith("HEAVY"):
        return text.replace("HEAVY ", "HEAVY")
    if "SYNTH" in text or "POLY" in text or "TAPETA" in text:
        return "SYNTH"
    if text.startswith("FIRM"):
        return text.replace("FIRM ", "FIRM")
    return normalize_spaces(text)


def parse_inrun_positions(value: object) -> tuple[str, str, float | None, float | None]:
    text = safe_text(value)
    if not text:
        return "", "", None, None
    parts = [part.strip() for part in text.split("/") if part.strip()]
    if len(parts) < 2:
        return "", "", None, None
    pos_800 = parts[0]
    pos_400 = parts[1]
    return pos_800, pos_400, parse_float(pos_800), parse_float(pos_400)


def load_track_alias_map() -> dict[str, str]:
    if not TRACK_ALIAS_PATH.exists():
        return {}
    df = pd.read_csv(TRACK_ALIAS_PATH, dtype=str).fillna("")
    alias_map: dict[str, str] = {}
    for row in df.to_dict("records"):
        chosen = upper_text(row.get("chosen"))
        if chosen not in {"", "YES", "TRUE", "1"}:
            continue
        alias_key = compact(row.get("alias_key"))
        canonical = upper_text(row.get("canonical_track"))
        if alias_key and canonical:
            alias_map[alias_key] = canonical
    return alias_map


def canonical_track(value: object, alias_map: dict[str, str]) -> str:
    raw = upper_text(value)
    if not raw:
        return ""
    for candidate in [compact(raw), compact(normalize_track_basic(raw))]:
        if candidate and candidate in alias_map:
            return alias_map[candidate]
    return normalize_track_basic(raw) or raw


def canonical_class_name(value: object) -> str:
    text = upper_text(value)
    if not text:
        return "UNKNOWN"
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)

    if "GROUP 1" in text or re.search(r"\bG1\b", text):
        return "GROUP 1"
    if "GROUP 2" in text or re.search(r"\bG2\b", text):
        return "GROUP 2"
    if "GROUP 3" in text or re.search(r"\bG3\b", text):
        return "GROUP 3"
    if "LISTED" in text:
        return "LISTED"
    if "WEIGHT FOR AGE" in text or re.search(r"\bWFA\b", text):
        return "WEIGHT FOR AGE"
    if "SET WEIGHTS AND PENALTIES" in text or re.search(r"\bSWP\b", text):
        return "SET WEIGHTS & PENALTIES"
    if "SET WEIGHTS" in text or re.search(r"\bSW\b", text):
        return "SET WEIGHTS"

    bm = re.search(r"\bBM\s?(\d{2,3})\b", text) or re.search(r"\bBENCHMARK\s?(\d{2,3})\b", text)
    if bm:
        return f"BM{bm.group(1)}"

    rtg = re.search(r"\bRTG\s?(\d{2,3})\b", text) or re.search(r"\bRATING\s?(\d{2,3})\b", text)
    if rtg:
        return f"RTG{rtg.group(1)}"

    cl = re.search(r"\bCLASS\s?(\d)\b", text) or re.search(r"\bCL\s?(\d)\b", text) or re.search(r"\bC\s?(\d)\b", text)
    if cl:
        return f"CLASS {cl.group(1)}"

    if "MAIDEN" in text or " MDN" in f" {text} ":
        return "MAIDEN"
    if "HANDICAP" in text or re.search(r"\bHCP\b", text):
        return "HANDICAP"
    if "OPEN" in text:
        return "OPEN"
    if "CONDITIONS" in text:
        return "CONDITIONS"

    return normalize_spaces(text) or "UNKNOWN"


def class_strength_base(class_name: str) -> float:
    text = upper_text(class_name)
    if text == "GROUP 1":
        return 90.0
    if text == "GROUP 2":
        return 86.0
    if text == "GROUP 3":
        return 82.0
    if text == "LISTED":
        return 78.0
    if text == "WEIGHT FOR AGE":
        return 76.0
    if text == "SET WEIGHTS & PENALTIES":
        return 74.0
    if text == "SET WEIGHTS":
        return 72.0
    if text == "OPEN":
        return 70.0
    if text == "CONDITIONS":
        return 68.0
    if text == "HANDICAP":
        return 66.0
    if text == "MAIDEN":
        return 50.0

    bm = re.search(r"BM(\d{2,3})", text)
    if bm:
        number = float(bm.group(1))
        return max(54.0, min(72.0, 32.0 + (number * 0.45)))

    rtg = re.search(r"RTG(\d{2,3})", text)
    if rtg:
        number = float(rtg.group(1))
        return max(53.0, min(71.0, 32.0 + (number * 0.43)))

    cl = re.search(r"CLASS (\d)", text)
    if cl:
        number = float(cl.group(1))
        return max(56.0, min(70.0, 56.0 + (number * 2.5)))

    return 60.0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def rating_band(score: float) -> str:
    if score >= 85:
        return "ELITE"
    if score >= 75:
        return "STRONG"
    if score >= 65:
        return "POSITIVE"
    if score >= 55:
        return "NEUTRAL"
    if score >= 45:
        return "NEGATIVE"
    return "POOR"


def build_unique_exact_maps(
    df: pd.DataFrame,
    source_name: str,
    rating_col: str,
    date_col: str,
    track_col: str,
    distance_col: str,
    horse_col: str,
    finish_col: str,
    alias_map: dict[str, str],
    race_no_col: str = "",
) -> dict[str, dict[str, dict[str, str]]]:
    if df.empty:
        return {"primary": {}, "secondary": {}}

    work = df.copy().fillna("")
    work["horse_name_norm"] = work[horse_col].map(normalize_horse)
    work["race_date_norm"] = work[date_col].map(safe_text)
    work["track_norm"] = work[track_col].map(lambda value: compact(canonical_track(value, alias_map)))
    work["distance_norm"] = work[distance_col].map(normalize_distance)
    work["finish_norm"] = work[finish_col].map(normalize_finish)
    work["rating_num"] = work[rating_col].map(parse_float)
    work["race_no_norm"] = work[race_no_col].map(normalize_race_no) if race_no_col else ""
    work = work[
        work["horse_name_norm"].astype(str).str.strip().ne("")
        & work["race_date_norm"].astype(str).str.strip().ne("")
        & work["track_norm"].astype(str).str.strip().ne("")
        & work["distance_norm"].astype(str).str.strip().ne("")
        & work["finish_norm"].astype(str).str.strip().ne("")
        & work["rating_num"].notna()
    ].copy()

    if work.empty:
        return {"primary": {}, "secondary": {}}

    work["key_primary"] = work.apply(
        lambda row: "|".join(
            [
                safe_text(row["horse_name_norm"]),
                safe_text(row["race_date_norm"]),
                safe_text(row["track_norm"]),
                safe_text(row["race_no_norm"]),
                safe_text(row["distance_norm"]),
                safe_text(row["finish_norm"]),
            ]
        ),
        axis=1,
    )
    work["key_secondary"] = work.apply(
        lambda row: "|".join(
            [
                safe_text(row["horse_name_norm"]),
                safe_text(row["race_date_norm"]),
                safe_text(row["track_norm"]),
                safe_text(row["distance_norm"]),
                safe_text(row["finish_norm"]),
            ]
        ),
        axis=1,
    )

    def dedupe(key_col: str) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        for key, group in work.groupby(key_col, dropna=False):
            key_text = safe_text(key)
            if not key_text:
                continue
            ratings = group["rating_num"].dropna().round(4).unique().tolist()
            if len(ratings) != 1:
                continue
            best = group.iloc[0].to_dict()
            result[key_text] = {
                "rating": f"{float(best['rating_num']):.2f}",
                "source": source_name,
            }
        return result

    return {
        "primary": dedupe("key_primary"),
        "secondary": dedupe("key_secondary"),
    }


def load_race_strength_maps(alias_map: dict[str, str]) -> dict[str, dict[str, dict[str, str]]]:
    if not RACE_STRENGTH_PATH.exists():
        return {"exact": {}, "secondary": {}}
    df = pd.read_csv(RACE_STRENGTH_PATH, dtype=str).fillna("")
    if df.empty:
        return {"exact": {}, "secondary": {}}

    df["track_norm"] = df["track"].map(lambda value: compact(canonical_track(value, alias_map)))
    df["race_no_norm"] = df["race_no"].map(normalize_race_no)
    df["distance_norm"] = df["distance"].map(normalize_distance)
    df["race_strength_num"] = df["race_strength"].map(parse_float)
    df["field_strength_num"] = df["field_strength"].map(parse_float)
    df = df[df["race_strength_num"].notna()].copy()

    exact: dict[str, dict[str, str]] = {}
    secondary: dict[str, dict[str, str]] = {}
    for row in df.to_dict("records"):
        exact_key = "|".join(
            [
                safe_text(row.get("race_date")),
                safe_text(row.get("track_norm")),
                safe_text(row.get("race_no_norm")),
                safe_text(row.get("distance_norm")),
            ]
        )
        secondary_key = "|".join(
            [
                safe_text(row.get("race_date")),
                safe_text(row.get("track_norm")),
                safe_text(row.get("distance_norm")),
            ]
        )
        payload = {
            "race_strength": safe_text(row.get("race_strength")),
            "field_strength": safe_text(row.get("field_strength")),
            "source": safe_text(row.get("source_file")) or "edgeiq_race_strength_history_v1.csv",
        }
        if exact_key.count("|") == 3 and exact_key not in exact:
            exact[exact_key] = payload
        if secondary_key.count("|") == 2 and secondary_key not in secondary:
            secondary[secondary_key] = payload
    return {"exact": exact, "secondary": secondary}


def compute_race_metrics(group: pd.DataFrame, race_strength_maps: dict[str, dict[str, dict[str, str]]]) -> dict[str, str]:
    first = group.iloc[0]
    field_size = int(len(group))
    class_name = safe_text(first.get("class_name"))
    class_base = class_strength_base(class_name)
    field_size_adj = clamp((field_size - 8) * 0.7, -3.0, 7.0)

    sp_series = pd.to_numeric(group["sp_num"], errors="coerce")
    sp_valid = sp_series[sp_series > 1]
    if len(sp_valid) >= max(4, math.ceil(field_size * 0.5)):
        favourite_sp = float(sp_valid.min())
        top4_avg = float(sp_valid.nsmallest(min(4, len(sp_valid))).mean())
        market_depth_adj = 0.0
        if favourite_sp <= 2.5:
            market_depth_adj += 1.5
        elif favourite_sp <= 4.0:
            market_depth_adj += 0.75
        if top4_avg <= 8.0:
            market_depth_adj += 1.0
        elif top4_avg >= 18.0:
            market_depth_adj -= 0.5
    else:
        market_depth_adj = 0.0

    second_margin_series = pd.to_numeric(
        group.loc[group["finish_pos_num"] == 2, "margin_num"],
        errors="coerce",
    ).dropna()
    second_margin = float(second_margin_series.iloc[0]) if not second_margin_series.empty else None
    if second_margin is None:
        margin_quality_adj = 0.0
    elif second_margin <= 0.2:
        margin_quality_adj = 1.5
    elif second_margin <= 0.75:
        margin_quality_adj = 1.0
    elif second_margin <= 1.5:
        margin_quality_adj = 0.5
    elif second_margin >= 7.0:
        margin_quality_adj = -1.0
    elif second_margin >= 4.0:
        margin_quality_adj = -0.5
    else:
        margin_quality_adj = 0.0

    field_strength_calc = round(clamp(class_base + field_size_adj + market_depth_adj, 35.0, 95.0), 2)
    race_strength_calc = round(clamp(field_strength_calc + margin_quality_adj, 35.0, 98.0), 2)

    exact_key = "|".join(
        [
            safe_text(first.get("race_date")),
            safe_text(first.get("track_norm")),
            safe_text(first.get("race_no_norm")),
            safe_text(first.get("distance_norm")),
        ]
    )
    secondary_key = "|".join(
        [
            safe_text(first.get("race_date")),
            safe_text(first.get("track_norm")),
            safe_text(first.get("distance_norm")),
        ]
    )
    joined = race_strength_maps["exact"].get(exact_key) or race_strength_maps["secondary"].get(secondary_key)
    race_strength = parse_float(joined.get("race_strength")) if joined else None
    field_strength = parse_float(joined.get("field_strength")) if joined else None

    return {
        "race_strength": f"{(race_strength if race_strength is not None else race_strength_calc):.2f}",
        "field_strength": f"{(field_strength if field_strength is not None else field_strength_calc):.2f}",
        "race_strength_source": joined.get("source") if joined else "COMPUTED_WAREHOUSE",
        "class_strength_base": f"{class_base:.2f}",
    }


def choose_exact_rating(
    row: pd.Series,
    exact_sources: list[tuple[str, dict[str, dict[str, dict[str, str]]]]],
) -> tuple[float | None, str]:
    key_primary = "|".join(
        [
            safe_text(row.get("horse_name_norm")),
            safe_text(row.get("race_date")),
            safe_text(row.get("track_norm")),
            safe_text(row.get("race_no_norm")),
            safe_text(row.get("distance_norm")),
            safe_text(row.get("finish_pos")),
        ]
    )
    key_secondary = "|".join(
        [
            safe_text(row.get("horse_name_norm")),
            safe_text(row.get("race_date")),
            safe_text(row.get("track_norm")),
            safe_text(row.get("distance_norm")),
            safe_text(row.get("finish_pos")),
        ]
    )
    for method, source_maps in exact_sources:
        payload = source_maps["primary"].get(key_primary) or source_maps["secondary"].get(key_secondary)
        if payload:
            rating = parse_float(payload.get("rating"))
            if rating is not None:
                return rating, method
    return None, ""


def formula_rating(row: pd.Series) -> tuple[float, str, float, float, float]:
    race_strength = parse_float(row.get("race_strength")) or 60.0
    field_size = max(1, int(parse_float(row.get("field_size")) or 1))
    finish_pos = int(parse_float(row.get("finish_pos")) or field_size)
    margin = parse_float(row.get("margin")) or 0.0
    distance = parse_float(row.get("distance")) or 1400.0

    finish_share = 1.0 if field_size <= 1 else 1.0 - ((finish_pos - 1) / max(1, field_size - 1))
    result_score = 50.0 + (finish_share * 40.0)

    if finish_pos == 1:
        margin_penalty = 0.0
        winner_bonus = 2.0
    else:
        if distance <= 1200:
            scale = 1.25
        elif distance <= 1600:
            scale = 1.05
        elif distance <= 2000:
            scale = 0.90
        else:
            scale = 0.75
        margin_penalty = min(18.0, margin * scale)
        winner_bonus = 0.0

    finish_sp_rank = parse_float(row.get("sp_rank"))
    sp_count = parse_float(row.get("sp_count"))
    if finish_sp_rank is not None and sp_count is not None and sp_count > 1:
        market_share = 1.0 - ((finish_sp_rank - 1.0) / max(1.0, sp_count - 1.0))
        market_adj = clamp((finish_share - market_share) * 8.0, -4.0, 4.0)
    else:
        market_adj = 0.0

    pos_800_num = parse_float(row.get("pos_800_num"))
    pos_400_num = parse_float(row.get("pos_400_num"))
    if pos_800_num is not None and pos_400_num is not None:
        late_move = pos_800_num - pos_400_num
        inrun_adj = clamp(late_move * 0.35, -1.5, 1.5)
    else:
        inrun_adj = 0.0

    rating = (0.58 * race_strength) + (0.42 * result_score) + winner_bonus + market_adj + inrun_adj - margin_penalty
    rating = clamp(rating, 25.0, 96.0)
    return round(rating, 2), f"{result_score:.2f}", round(margin_penalty, 2), round(market_adj, 2), round(inrun_adj, 2)


def rating_confidence(method: str, row: pd.Series) -> str:
    if method in {"EXACT_V6_1", "EXACT_HISTORICAL_V3"}:
        return "HIGH"
    if method in {"EXACT_RUN_RATINGS_V1", "EXACT_ALL_RUNS_RATED"}:
        return "MEDIUM"
    evidence_points = 0
    if safe_text(row.get("race_strength_source")) != "COMPUTED_WAREHOUSE":
        evidence_points += 1
    if parse_float(row.get("sp_num")) is not None:
        evidence_points += 1
    if parse_float(row.get("pos_800_num")) is not None and parse_float(row.get("pos_400_num")) is not None:
        evidence_points += 1
    if upper_text(row.get("class_name")) != "UNKNOWN":
        evidence_points += 1
    if evidence_points >= 3:
        return "MEDIUM"
    return "LOW"


def load_warehouse(alias_map: dict[str, str]) -> pd.DataFrame:
    usecols = [
        "meeting_date",
        "track",
        "race_no",
        "distance",
        "raceClass",
        "trackCondition",
        "finishPosition",
        "horseNo",
        "horseName",
        "horseKey",
        "barrier",
        "trainer",
        "jockey",
        "weight",
        "inRun",
        "margin",
        "sp",
        "stab",
        "source_batch_file_v1",
    ]
    df = pd.read_csv(
        WAREHOUSE_PATH,
        dtype=str,
        usecols=lambda c: c in usecols,
        keep_default_na=False,
        low_memory=False,
    ).fillna("")

    df["race_date"] = df["meeting_date"].map(safe_text)
    df["track"] = df["track"].map(lambda value: canonical_track(value, alias_map))
    df["track_norm"] = df["track"].map(compact)
    df["race_no"] = df["race_no"].map(normalize_race_no)
    df["distance"] = df["distance"].map(normalize_distance)
    df["distance_norm"] = df["distance"]
    df["class_name"] = df["raceClass"].map(canonical_class_name)
    df["condition"] = df["trackCondition"].map(canonical_condition)
    df["finish_pos"] = df["finishPosition"].map(normalize_finish)
    df["finish_pos_num"] = df["finish_pos"].map(numeric_finish)
    df["horse"] = df["horseName"].map(safe_text)
    df["horse_key"] = df.apply(lambda row: safe_text(row.get("horseKey")) or normalize_horse(row.get("horseName")), axis=1)
    df["horse_name_norm"] = df["horse"].map(normalize_horse)
    df["barrier"] = df["barrier"].map(safe_text)
    df["jockey"] = df["jockey"].map(safe_text)
    df["trainer"] = df["trainer"].map(safe_text)
    df["weight"] = df["weight"].map(safe_text)
    df["margin_num"] = df["margin"].map(parse_float)
    df["sp_num"] = df.apply(lambda row: parse_float(row.get("sp")) or parse_float(row.get("stab")), axis=1)
    df["source_file"] = df["source_batch_file_v1"].map(safe_text).replace("", WAREHOUSE_PATH.name)

    inrun_parts = df["inRun"].map(parse_inrun_positions)
    df["pos_800"] = inrun_parts.map(lambda item: item[0])
    df["pos_400"] = inrun_parts.map(lambda item: item[1])
    df["pos_800_num"] = inrun_parts.map(lambda item: item[2])
    df["pos_400_num"] = inrun_parts.map(lambda item: item[3])

    df = df[df["race_date"].astype(str).str.strip().ne("")].copy()
    df = df[df["track_norm"].astype(str).str.strip().ne("")].copy()
    df = df[df["race_no"].astype(str).str.strip().ne("")].copy()
    df = df[df["distance_norm"].astype(str).str.strip().ne("")].copy()
    df = df[df["horse_name_norm"].astype(str).str.strip().ne("")].copy()
    df = df[df["finish_pos_num"].notna()].copy()

    df["race_key"] = df.apply(
        lambda row: "|".join(
            [
                safe_text(row["race_date"]),
                safe_text(row["track_norm"]),
                safe_text(row["race_no"]),
            ]
        ),
        axis=1,
    )
    df["field_size"] = df.groupby("race_key")["horse"].transform("count").astype(int)
    df["sp_rank"] = (
        df.groupby("race_key")["sp_num"]
        .rank(method="dense", ascending=True, na_option="keep")
    )
    df["sp_count"] = df.groupby("race_key")["sp_num"].transform(lambda series: series.notna().sum())
    return df


def main() -> None:
    if not WAREHOUSE_PATH.exists():
        raise FileNotFoundError(f"Missing input: {WAREHOUSE_PATH}")

    built_at = now_iso()
    alias_map = load_track_alias_map()
    warehouse = load_warehouse(alias_map)

    exact_sources = [
        (
            "EXACT_V6_1",
            build_unique_exact_maps(
                pd.read_csv(PERF_V61_PATH, dtype=str, keep_default_na=False, low_memory=False).fillna("") if PERF_V61_PATH.exists() else pd.DataFrame(),
                "edgeiq_historical_performance_rating_v6_1_research.csv",
                "performance_rating_v6_1_research",
                "race_date",
                "track",
                "distance",
                "horse",
                "finish_position",
                alias_map,
            ),
        ),
        (
            "EXACT_HISTORICAL_V3",
            build_unique_exact_maps(
                pd.read_csv(RUN_V3_PATH, dtype=str, keep_default_na=False, low_memory=False).fillna("") if RUN_V3_PATH.exists() else pd.DataFrame(),
                "edgeiq_historical_run_rating_v3.csv",
                "historical_run_rating_v3",
                "race_date",
                "track",
                "distance",
                "horse",
                "finish_pos",
                alias_map,
                race_no_col="race_no",
            ),
        ),
        (
            "EXACT_RUN_RATINGS_V1",
            build_unique_exact_maps(
                pd.read_csv(RUN_RATINGS_V1_PATH, dtype=str, keep_default_na=False, low_memory=False).fillna("") if RUN_RATINGS_V1_PATH.exists() else pd.DataFrame(),
                "run_ratings_v1.csv",
                "run_rating",
                "run_date",
                "track",
                "distance",
                "horse",
                "finish_pos",
                alias_map,
            ),
        ),
        (
            "EXACT_ALL_RUNS_RATED",
            build_unique_exact_maps(
                pd.read_csv(ALL_RUNS_RATED_PATH, dtype=str, keep_default_na=False, low_memory=False).fillna("") if ALL_RUNS_RATED_PATH.exists() else pd.DataFrame(),
                "all_horse_runs_rated.csv",
                "run_rating",
                "run_date",
                "track",
                "distance",
                "horse_name",
                "finish_pos",
                alias_map,
            ),
        ),
    ]
    race_strength_maps = load_race_strength_maps(alias_map)

    race_metric_rows = []
    for race_key, group in warehouse.groupby("race_key", sort=False):
        metrics = compute_race_metrics(group, race_strength_maps)
        metrics["race_key"] = race_key
        race_metric_rows.append(metrics)
    race_metrics_df = pd.DataFrame(race_metric_rows)
    enriched = warehouse.merge(race_metrics_df, on="race_key", how="left")

    output_rows = []
    for row in enriched.to_dict("records"):
        series = pd.Series(row)
        exact_rating, method = choose_exact_rating(series, exact_sources)
        if exact_rating is None:
            final_rating, result_score, margin_penalty, market_adj, inrun_adj = formula_rating(series)
            method = "FORMULA_WAREHOUSE"
        else:
            final_rating = round(exact_rating, 2)
            result_score = ""
            margin_penalty = ""
            market_adj = ""
            inrun_adj = ""

        output_rows.append(
            {
                "horse": safe_text(row.get("horse")),
                "horse_key": safe_text(row.get("horse_key")),
                "race_date": safe_text(row.get("race_date")),
                "track": safe_text(row.get("track")),
                "race_no": safe_text(row.get("race_no")),
                "distance": safe_text(row.get("distance")),
                "class_name": safe_text(row.get("class_name")),
                "condition": safe_text(row.get("condition")),
                "finish_pos": safe_text(row.get("finish_pos")),
                "field_size": safe_text(row.get("field_size")),
                "barrier": safe_text(row.get("barrier")),
                "jockey": safe_text(row.get("jockey")),
                "trainer": safe_text(row.get("trainer")),
                "weight": safe_text(row.get("weight")),
                "margin": safe_text(row.get("margin")),
                "sp": safe_text(row.get("sp")) or safe_text(row.get("stab")),
                "pos_800": safe_text(row.get("pos_800")),
                "pos_400": safe_text(row.get("pos_400")),
                "performance_rating": f"{final_rating:.2f}",
                "rating_band": rating_band(final_rating),
                "rating_rank_in_race": "",
                "rating_confidence": rating_confidence(method, series),
                "race_strength": safe_text(row.get("race_strength")),
                "field_strength": safe_text(row.get("field_strength")),
                "source_file": safe_text(row.get("source_file")),
                "rating_method": method,
                "race_strength_source": safe_text(row.get("race_strength_source")),
                "class_strength_base": safe_text(row.get("class_strength_base")),
                "result_score": safe_text(result_score),
                "margin_penalty": safe_text(margin_penalty),
                "market_adj": safe_text(market_adj),
                "inrun_adj": safe_text(inrun_adj),
                "built_at": built_at,
            }
        )

    output_df = pd.DataFrame(output_rows)
    output_df["race_key"] = (
        output_df["race_date"].astype(str)
        + "|"
        + output_df["track"].map(compact)
        + "|"
        + output_df["race_no"].astype(str)
    )
    output_df["performance_rating_num"] = output_df["performance_rating"].map(parse_float)
    output_df["rating_rank_in_race"] = (
        output_df.groupby("race_key")["performance_rating_num"]
        .rank(method="dense", ascending=False)
        .astype(int)
        .astype(str)
    )
    output_df.sort_values(
        by=["race_date", "track", "race_no", "finish_pos"],
        ascending=[True, True, True, True],
        inplace=True,
    )
    output_df.drop(columns=["race_key", "performance_rating_num"], inplace=True)
    output_df.to_csv(OUT_PATH, index=False)

    method_counts = output_df["rating_method"].value_counts(dropna=False).to_dict()
    confidence_counts = output_df["rating_confidence"].value_counts(dropna=False).to_dict()
    band_counts = output_df["rating_band"].value_counts(dropna=False).to_dict()
    summary = pd.DataFrame(
        [
            {
                "status": "PASS" if len(output_df) > 0 else "FAIL",
                "warehouse_finished_rows": int(len(warehouse)),
                "output_rows": int(len(output_df)),
                "unique_horses": int(output_df["horse_key"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()),
                "unique_races": int(
                    (
                        output_df["race_date"].astype(str)
                        + "|"
                        + output_df["track"].astype(str)
                        + "|"
                        + output_df["race_no"].astype(str)
                    ).nunique()
                ),
                "rating_coverage_pct": round(
                    float((output_df["performance_rating"].astype(str).str.strip() != "").mean() * 100.0),
                    2,
                ),
                "race_strength_coverage_pct": round(
                    float((output_df["race_strength"].astype(str).str.strip() != "").mean() * 100.0),
                    2,
                ),
                "field_strength_coverage_pct": round(
                    float((output_df["field_strength"].astype(str).str.strip() != "").mean() * 100.0),
                    2,
                ),
                "rating_method_counts": "; ".join(f"{key}:{value}" for key, value in method_counts.items()),
                "rating_confidence_counts": "; ".join(f"{key}:{value}" for key, value in confidence_counts.items()),
                "rating_band_counts": "; ".join(f"{key}:{value}" for key, value in band_counts.items()),
                "built_at": built_at,
            }
        ]
    )
    summary.to_csv(SUMMARY_PATH, index=False)

    print("[EDGEIQ_HISTORICAL_RUN_RATINGS_MASTER_V1] COMPLETE")
    print(summary.to_string(index=False))
    print(f"out={OUT_PATH}")
    print(f"summary={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
