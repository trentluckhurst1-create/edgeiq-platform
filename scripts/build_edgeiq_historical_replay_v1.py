from __future__ import annotations

import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

OUT = DATA / "edgeiq_historical_replay_v1.csv"
SUMMARY = DATA / "edgeiq_historical_replay_v1_validation_summary.csv"
ROI_BY_RANK = DATA / "edgeiq_historical_replay_v1_roi_by_rank.csv"
ROI_BY_SCORE_BAND = DATA / "edgeiq_historical_replay_v1_roi_by_score_band.csv"


TARGET_FORMULA = "class_par + 0.15*distance_adjustment + 0.15*condition_adjustment"
DEFAULT_GLOBAL_TARGET = 58.0
DEFAULT_GLOBAL_RACE_STRENGTH = 50.0


@dataclass
class HorseHistory:
    starts: int = 0
    wins: int = 0
    places: int = 0
    top4s: int = 0
    sum_finish_pct: float = 0.0
    best_finish_pct: float = 0.0
    recent_finish_pcts: deque[float] = field(default_factory=lambda: deque(maxlen=5))
    recent_run_ratings: deque[float] = field(default_factory=lambda: deque(maxlen=6))
    recent_sectional_scores: deque[float] = field(default_factory=lambda: deque(maxlen=10))
    recent_sectional_race_strengths: deque[float] = field(default_factory=lambda: deque(maxlen=10))

    def update(
        self,
        finish_pct: float,
        run_rating: float,
        sectional_score: float,
        race_strength_score: float,
        won: bool,
        placed: bool,
        top4: bool,
    ) -> None:
        self.starts += 1
        self.wins += int(won)
        self.places += int(placed)
        self.top4s += int(top4)
        self.sum_finish_pct += finish_pct
        self.best_finish_pct = max(self.best_finish_pct, finish_pct)
        self.recent_finish_pcts.append(finish_pct)
        self.recent_run_ratings.append(run_rating)
        self.recent_sectional_scores.append(sectional_score)
        self.recent_sectional_race_strengths.append(race_strength_score)


@dataclass
class EntityHistory:
    starts: int = 0
    wins: int = 0
    places: int = 0
    sum_finish_pct: float = 0.0
    recent_finish_pcts: deque[float] = field(default_factory=lambda: deque(maxlen=25))

    def update(self, finish_pct: float, won: bool, placed: bool) -> None:
        self.starts += 1
        self.wins += int(won)
        self.places += int(placed)
        self.sum_finish_pct += finish_pct
        self.recent_finish_pcts.append(finish_pct)


@dataclass
class ParSamples:
    winner: list[float] = field(default_factory=list)
    top3: list[float] = field(default_factory=list)
    all_runs: list[float] = field(default_factory=list)

    def update(self, run_rating: float, finish_position: float) -> None:
        self.all_runs.append(run_rating)
        if finish_position <= 3:
            self.top3.append(run_rating)
        if finish_position == 1:
            self.winner.append(run_rating)


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def upper_text(value: object) -> str:
    return clean_text(value).upper()


def canon_horse(value: object) -> str:
    text = upper_text(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def norm_track(value: object) -> str:
    text = upper_text(value)
    for prefix in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM "]:
        text = text.replace(prefix, "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def person_key(value: object) -> str:
    return canon_horse(value)


def parse_float(value: object) -> float:
    if pd.isna(value):
        return math.nan
    text = str(value).replace("$", "").replace(",", "").replace("kg", "").strip()
    text = text.replace("â€“", "").replace("—", "")
    if text == "":
        return math.nan
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return math.nan
    try:
        return float(match.group(0))
    except ValueError:
        return math.nan


def parse_pos(value: object) -> float:
    if pd.isna(value):
        return math.nan
    text = upper_text(value)
    if text in {"", "SCR", "SCRATCHED", "NAN", "NONE"}:
        return math.nan
    match = re.search(r"\d+", text)
    if not match:
        return math.nan
    return float(match.group(0))


def parse_distance(value: object) -> float:
    if pd.isna(value):
        return math.nan
    text = upper_text(value).replace("M", "")
    return parse_float(text)


def parse_time_seconds(value: object) -> float:
    text = clean_text(value)
    if not text:
        return math.nan
    text = text.replace(" ", "")
    if ":" in text:
        parts = text.split(":")
        try:
            if len(parts) == 2:
                minutes = float(parts[0])
                seconds = float(parts[1])
                return (minutes * 60.0) + seconds
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return (hours * 3600.0) + (minutes * 60.0) + seconds
        except ValueError:
            return math.nan
    return parse_float(text)


def clean_class(value: object) -> str:
    text = upper_text(value).replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "HANDICAP"

    bm = re.search(r"\bBM\s*(\d{2,3})\b", text)
    if bm:
        return f"BM{bm.group(1)}"

    rating_band = re.search(r"\b0\s*(?:TO|/|-)\s*(\d{2,3})\b", text)
    if rating_band:
        return f"BM{rating_band.group(1)}"

    if "MAIDEN" in text or text in {"MDN", "2YO MDN", "3YO MDN", "2YO MAIDEN", "3YO MAIDEN"}:
        return "MAIDEN"

    class_match = re.search(r"\b(?:CLASS|CL|C)\s*([1-6])\b", text)
    if class_match:
        return f"CLASS {class_match.group(1)}"

    group_match = re.search(r"\bGROUP\s*([123])\b|\bG([123])\b", text)
    if group_match:
        group_no = group_match.group(1) or group_match.group(2)
        return f"GROUP {group_no}"

    if "LISTED" in text:
        return "LISTED"
    if "HANDICAP" in text:
        return "HANDICAP"
    return text


def class_family(class_clean: str) -> str:
    if class_clean in {"GROUP 1", "GROUP 2", "GROUP 3", "LISTED"}:
        return "BLACKTYPE"
    if class_clean.startswith("BM"):
        return "BENCHMARK"
    if class_clean.startswith("CLASS "):
        return "CLASS"
    if class_clean == "MAIDEN":
        return "MAIDEN"
    if class_clean in {"HANDICAP", "UNKNOWN"}:
        return "HANDICAP"
    return "OTHER"


def distance_band(distance: float) -> str:
    if pd.isna(distance):
        return "UNKNOWN"
    if distance < 800:
        return "UNDER_800"
    if distance <= 999:
        return "800-999"
    if distance <= 1199:
        return "1000-1199"
    if distance <= 1399:
        return "1200-1399"
    if distance <= 1599:
        return "1400-1599"
    if distance <= 1799:
        return "1600-1799"
    if distance <= 1999:
        return "1800-1999"
    if distance <= 2199:
        return "2000-2199"
    if distance <= 2399:
        return "2200-2399"
    if distance <= 2799:
        return "2400-2799"
    return "2800+"


def condition_group(value: object) -> str:
    text = upper_text(value)
    if "FIRM" in text:
        return "FIRM"
    if "GOOD" in text:
        return "GOOD"
    if "SOFT" in text:
        return "SOFT"
    if "HEAVY" in text:
        return "HEAVY"
    if "SYNTH" in text or "POLY" in text or "ALL WEATHER" in text:
        return "SYNTHETIC"
    return "UNKNOWN"


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def safe_mean(values: list[float]) -> float:
    cleaned = [float(v) for v in values if not pd.isna(v)]
    if not cleaned:
        return math.nan
    return float(np.mean(cleaned))


def safe_std(values: list[float]) -> float:
    cleaned = [float(v) for v in values if not pd.isna(v)]
    if len(cleaned) < 2:
        return 0.0
    return float(np.std(cleaned, ddof=0))


def safe_median(values: list[float], default: float) -> float:
    cleaned = [float(v) for v in values if not pd.isna(v)]
    if not cleaned:
        return default
    return float(np.median(cleaned))


def evidence_score(runs: int) -> float:
    if runs <= 0:
        return 0.0
    if runs == 1:
        return 18.0
    if runs == 2:
        return 32.0
    if runs == 3:
        return 48.0
    if runs == 4:
        return 58.0
    if runs == 5:
        return 68.0
    if runs == 6:
        return 76.0
    if runs == 7:
        return 83.0
    if runs == 8:
        return 88.0
    if runs == 9:
        return 92.0
    return 100.0


def score_band(score: float) -> str:
    if pd.isna(score):
        return "UNKNOWN"
    if score >= 75:
        return "ELITE"
    if score >= 65:
        return "STRONG"
    if score >= 55:
        return "POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 35:
        return "WEAK"
    return "POOR"


def projection_confidence_label(starts: int, target_confidence: str) -> str:
    if starts <= 2:
        return "LOW"
    if starts <= 4:
        return "MEDIUM" if target_confidence in {"HIGH", "MEDIUM"} else "LOW"
    return "HIGH" if target_confidence == "HIGH" else "MEDIUM"


def confidence_label_from_score(value: float) -> str:
    if value >= 85:
        return "HIGH"
    if value >= 70:
        return "MEDIUM"
    if value >= 50:
        return "LOW"
    return "VERY_LOW"


def governance_status(starts: int, horse_name: str) -> str:
    horse = upper_text(horse_name)
    if starts <= 0:
        if any(tag in horse for tag in ["(GB)", "(IRE)", "(FR)", "(USA)", "(JPN)", "(NZ)"]):
            return "IMPORT_UNKNOWN"
        return "FIRST_STARTER_OR_UNKNOWN"
    if starts == 1:
        return "LIMITED_DATA_1_START"
    if starts == 2:
        return "LIMITED_DATA_2_STARTS"
    if starts < 5:
        return "LIMITED_DATA_3_4_STARTS"
    return "PROVEN"


def governance_score(status: str) -> float:
    mapping = {
        "PROVEN": 100.0,
        "PROVEN_UNCLEAR_HISTORY": 90.0,
        "LIMITED_DATA_3_4_STARTS": 72.0,
        "LIMITED_DATA_2_STARTS": 58.0,
        "LIMITED_DATA_1_START": 45.0,
        "IMPORT_UNKNOWN": 38.0,
        "FIRST_STARTER_OR_UNKNOWN": 25.0,
    }
    return mapping.get(status, 40.0)


def projection_floor(status: str) -> float:
    mapping = {
        "PROVEN": 50.0,
        "PROVEN_UNCLEAR_HISTORY": 45.0,
        "LIMITED_DATA_3_4_STARTS": 38.0,
        "LIMITED_DATA_2_STARTS": 32.0,
        "LIMITED_DATA_1_START": 28.0,
        "IMPORT_UNKNOWN": 26.0,
        "FIRST_STARTER_OR_UNKNOWN": 22.0,
    }
    return mapping.get(status, 30.0)


def governance_multiplier(status: str) -> float:
    mapping = {
        "PROVEN": 1.00,
        "PROVEN_UNCLEAR_HISTORY": 0.95,
        "LIMITED_DATA_3_4_STARTS": 0.92,
        "LIMITED_DATA_2_STARTS": 0.82,
        "LIMITED_DATA_1_START": 0.72,
        "IMPORT_UNKNOWN": 0.60,
        "FIRST_STARTER_OR_UNKNOWN": 0.45,
    }
    return mapping.get(status, 0.70)


def ability_multiplier(status: str) -> float:
    mapping = {
        "PROVEN": 1.00,
        "PROVEN_UNCLEAR_HISTORY": 0.99,
        "LIMITED_DATA_3_4_STARTS": 0.98,
        "LIMITED_DATA_2_STARTS": 1.01,
        "LIMITED_DATA_1_START": 0.98,
        "IMPORT_UNKNOWN": 1.00,
        "FIRST_STARTER_OR_UNKNOWN": 1.02,
    }
    return mapping.get(status, 0.98)


def confidence_multiplier(status: str, confidence_score_value: float) -> float:
    base = {
        "PROVEN": 1.00,
        "PROVEN_UNCLEAR_HISTORY": 0.96,
        "LIMITED_DATA_3_4_STARTS": 0.94,
        "LIMITED_DATA_2_STARTS": 0.90,
        "LIMITED_DATA_1_START": 0.86,
        "IMPORT_UNKNOWN": 0.82,
        "FIRST_STARTER_OR_UNKNOWN": 0.80,
    }.get(status, 0.80)
    adjustment = clip((confidence_score_value - 60.0) * 0.0015, -0.05, 0.03)
    return clip(base + adjustment, 0.75, 1.02)


def race_strength_adjustment(score: float) -> float:
    if score >= 70:
        return 1.06
    if score >= 62:
        return 1.03
    if score >= 52:
        return 1.00
    if score >= 42:
        return 0.97
    return 0.93


def market_score(sp: float) -> float:
    if pd.isna(sp) or sp <= 1.0:
        return 50.0
    implied = 1.0 / sp
    return clip((implied / 0.22) * 100.0, 15.0, 95.0)


def barrier_score(barrier: float, field_size: int, distance: float) -> float:
    if pd.isna(barrier) or field_size <= 1:
        return 50.0
    draw = clip((barrier - 1.0) / max(field_size - 1.0, 1.0), 0.0, 1.0)
    if pd.isna(distance):
        base = 58.0
        penalty = 16.0
    elif distance <= 1200:
        base = 64.0
        penalty = 28.0
    elif distance <= 1600:
        base = 60.0
        penalty = 18.0
    else:
        base = 56.0
        penalty = 10.0
    return clip(base - (penalty * draw), 30.0, 70.0)


def weight_score(weight: float) -> float:
    if pd.isna(weight):
        return 50.0
    score = 58.0 - max(weight - 56.0, 0.0) * 2.0 + max(54.0 - weight, 0.0) * 1.2
    return clip(score, 35.0, 70.0)


def parse_in_run_positions(value: object) -> tuple[float, float]:
    text = upper_text(value)
    if not text:
        return math.nan, math.nan
    nums = [float(match) for match in re.findall(r"(\d+)", text)]
    if not nums:
        return math.nan, math.nan
    if len(nums) == 1:
        return nums[0], nums[0]
    return nums[0], nums[-1]


def finish_pct(finish_position: float, field_size: int) -> float:
    if pd.isna(finish_position) or field_size <= 1:
        return 0.5
    return clip(1.0 - ((finish_position - 1.0) / (field_size - 1.0)), 0.0, 1.0)


def run_sectional_proxy(early_pos: float, late_pos: float, finish_pct_value: float, field_size: int, margin: float) -> float:
    if field_size <= 1:
        return 50.0
    early_pct = finish_pct(early_pos, field_size) if not pd.isna(early_pos) else 0.5
    late_pct = finish_pct(late_pos, field_size) if not pd.isna(late_pos) else early_pct
    margin_quality = 1.0 if pd.isna(margin) else clip(1.0 - (margin / 15.0), 0.0, 1.0)
    late_gain = clip(finish_pct_value - late_pct, -1.0, 1.0)
    mid_gain = clip(late_pct - early_pct, -1.0, 1.0)
    score = (
        20.0 * late_pct
        + 30.0 * finish_pct_value
        + 25.0 * max(late_gain, 0.0)
        + 15.0 * max(mid_gain, 0.0)
        + 10.0 * margin_quality
    )
    return clip(score, 0.0, 100.0)


def speed_score(distance: float, race_time_seconds: float) -> float:
    if pd.isna(distance) or pd.isna(race_time_seconds) or race_time_seconds <= 0:
        return 50.0
    metres_per_second = distance / race_time_seconds
    scaled = ((metres_per_second - 13.5) / 5.5) * 100.0
    return clip(scaled, 0.0, 100.0)


def entity_strength(history: EntityHistory | None) -> float:
    if history is None or history.starts == 0:
        return 50.0
    avg_finish = history.sum_finish_pct / history.starts
    recent_avg = safe_mean(list(history.recent_finish_pcts))
    if pd.isna(recent_avg):
        recent_avg = avg_finish
    win_rate = history.wins / history.starts
    place_rate = history.places / history.starts
    raw = 100.0 * (
        0.45 * avg_finish
        + 0.25 * recent_avg
        + 0.20 * place_rate
        + 0.10 * win_rate
    )
    if history.starts >= 50:
        reliability = 1.00
    elif history.starts >= 20:
        reliability = 0.97
    elif history.starts >= 10:
        reliability = 0.94
    elif history.starts >= 5:
        reliability = 0.90
    else:
        reliability = 0.86
    return clip(raw * reliability, 20.0, 90.0)


def horse_results_strength(history: HorseHistory | None) -> tuple[float, str]:
    if history is None or history.starts == 0:
        return math.nan, "UNKNOWN"

    avg_finish = history.sum_finish_pct / history.starts
    recent_avg = safe_mean(list(history.recent_finish_pcts))
    if pd.isna(recent_avg):
        recent_avg = avg_finish
    win_rate = history.wins / history.starts
    place_rate = history.places / history.starts
    top4_rate = history.top4s / history.starts
    raw = 100.0 * (
        0.34 * avg_finish
        + 0.26 * recent_avg
        + 0.16 * place_rate
        + 0.12 * win_rate
        + 0.08 * top4_rate
        + 0.04 * history.best_finish_pct
    )

    if history.starts >= 10:
        label = "PROVEN_10_PLUS"
        multiplier = 1.00
    elif history.starts >= 5:
        label = "PROVEN_5_9"
        multiplier = 0.96
    elif history.starts >= 3:
        label = "LIMITED_3_4"
        multiplier = 0.90
    else:
        label = "LIMITED_1_2"
        multiplier = 0.82

    return clip(raw * multiplier, 0.0, 100.0), label


def projected_rating(history: HorseHistory | None) -> tuple[float, str]:
    if history is None or history.starts == 0:
        return math.nan, "NO_HISTORY"
    ratings = list(history.recent_run_ratings)
    if not ratings:
        return math.nan, "NO_HISTORY"
    last_rating = ratings[-1]
    avg3 = safe_mean(ratings[-3:])
    avg5 = safe_mean(ratings[-5:])
    peak6 = max(ratings[-6:])
    starts = history.starts

    if starts >= 5:
        rating = (0.35 * last_rating) + (0.35 * avg3) + (0.20 * peak6) + (0.10 * avg5)
        return clip(rating, 0.0, 100.0), "0.35 last + 0.35 avg3 + 0.20 peak6 + 0.10 avg5"
    if starts >= 3:
        rating = (0.45 * last_rating) + (0.40 * avg3) + (0.15 * peak6)
        return clip(rating, 0.0, 100.0), "0.45 last + 0.40 avg3 + 0.15 peak"
    return clip(safe_mean(ratings), 0.0, 100.0), "average available ratings"


def sectional_profile(
    history: HorseHistory | None,
    connection_score_value: float,
    global_race_strength_avg: float,
) -> tuple[float, float, str]:
    if history is None or history.starts == 0 or not history.recent_sectional_scores:
        base = clip(45.0 + ((connection_score_value - 50.0) * 0.15), 25.0, 65.0)
        return base, 30.0, "NO_HISTORY_FALLBACK"

    values = list(history.recent_sectional_scores)
    recent3 = values[-3:]
    recent5 = values[-5:]
    peak = max(values)
    closing = safe_mean(recent3)
    sustained = safe_mean(recent5)
    raw = clip((0.40 * peak) + (0.35 * closing) + (0.25 * sustained), 0.0, 100.0)

    spread = max(peak, closing, sustained) - min(peak, closing, sustained)
    balance = clip(100.0 - spread, 0.0, 100.0)
    evidence = evidence_score(len(values))
    confidence = clip((evidence * 0.80) + (balance * 0.20), 0.0, 100.0)

    strength_runs = list(history.recent_sectional_race_strengths)
    avg_strength = safe_mean(strength_runs)
    if pd.isna(avg_strength) or global_race_strength_avg <= 0:
        strength_factor = 1.0
    else:
        strength_factor = clip(avg_strength / global_race_strength_avg, 0.85, 1.15)
    strength = clip(raw * strength_factor, 0.0, 100.0)
    return strength, confidence, "SECTIONAL_HISTORY"


def predictability_score(history: HorseHistory | None, connection_score_value: float) -> float:
    if history is None or history.starts == 0:
        return clip(38.0 + ((connection_score_value - 50.0) * 0.18), 25.0, 60.0)
    ratings = list(history.recent_run_ratings)
    recent_finish = list(history.recent_finish_pcts)
    rating_std = safe_std(ratings[-5:])
    finish_std = safe_std(recent_finish[-5:]) * 100.0
    consistency = clip(100.0 - (rating_std * 3.5) - (finish_std * 0.6), 20.0, 95.0)
    place_rate = history.places / history.starts
    score = (0.72 * consistency) + (0.28 * (place_rate * 100.0))
    if history.starts <= 2:
        score *= 0.92
    return clip(score, 20.0, 95.0)


def class_par(
    class_name: str,
    family_name: str,
    class_stats: dict[str, ParSamples],
    family_stats: dict[str, ParSamples],
    global_base: float,
    cache: dict[tuple[str, str], tuple[float, str, str]],
) -> tuple[float, str, str]:
    key = (class_name, family_name)
    if key in cache:
        return cache[key]

    samples = class_stats.get(class_name)
    family_samples = family_stats.get(family_name)

    if samples and len(samples.winner) >= 12:
        value = safe_median(samples.winner, global_base)
        confidence = "HIGH" if len(samples.winner) >= 30 else "MEDIUM"
        source = "CLASS_WINNER_MEDIAN"
    elif samples and len(samples.top3) >= 24:
        value = safe_median(samples.top3, global_base)
        confidence = "MEDIUM"
        source = "CLASS_TOP3_MEDIAN"
    elif family_samples and len(family_samples.winner) >= 12:
        value = safe_median(family_samples.winner, global_base)
        confidence = "LOW"
        source = "FAMILY_WINNER_MEDIAN"
    elif family_samples and len(family_samples.top3) >= 24:
        value = safe_median(family_samples.top3, global_base)
        confidence = "LOW"
        source = "FAMILY_TOP3_MEDIAN"
    else:
        value = global_base
        confidence = "LOW"
        source = "GLOBAL_WINNER_MEDIAN"

    cache[key] = (value, confidence, source)
    return cache[key]


def band_adjustment(
    band_name: str,
    band_samples: dict[str, list[float]],
    global_base: float,
    minimum_samples: int,
    cache: dict[str, tuple[float, str]],
) -> tuple[float, str]:
    if band_name in cache:
        return cache[band_name]
    values = band_samples.get(band_name, [])
    if len(values) >= minimum_samples:
        delta = safe_median(values, global_base) - global_base
        confidence = "HIGH" if len(values) >= (minimum_samples * 2) else "MEDIUM"
    else:
        delta = 0.0
        confidence = "LOW"
    cache[band_name] = (delta, confidence)
    return cache[band_name]


def connection_score_value(
    trainer_score_value: float,
    jockey_score_value: float,
    barrier_score_value: float,
    weight_score_value: float,
    market_score_value: float,
) -> float:
    return clip(
        (0.38 * trainer_score_value)
        + (0.24 * jockey_score_value)
        + (0.12 * barrier_score_value)
        + (0.08 * weight_score_value)
        + (0.18 * market_score_value),
        20.0,
        90.0,
    )


def fallback_projection(
    class_target: float,
    connection_score_metric: float,
    market_score_metric: float,
) -> float:
    return clip(
        (0.55 * class_target)
        + (0.30 * connection_score_metric)
        + (0.15 * market_score_metric),
        18.0,
        70.0,
    )


def confidence_score(
    status: str,
    starts: int,
    target_confidence: str,
    projection_confidence: str,
    sectional_confidence: float,
    predictability: float,
    trainer_score_metric: float,
    jockey_score_metric: float,
    has_horse_results: bool,
) -> float:
    score = 25.0

    if status == "PROVEN":
        score += 25.0
    elif status == "LIMITED_DATA_3_4_STARTS":
        score += 15.0
    elif status == "LIMITED_DATA_2_STARTS":
        score += 10.0
    elif status == "LIMITED_DATA_1_START":
        score += 5.0
    else:
        score -= 2.0

    target_points = {"HIGH": 8.0, "MEDIUM": 5.0, "LOW": 2.0}.get(target_confidence, 2.0)
    projection_points = {"HIGH": 12.0, "MEDIUM": 7.0, "LOW": 4.0}.get(projection_confidence, 4.0)
    score += target_points + projection_points

    if sectional_confidence >= 78:
        score += 10.0
    elif sectional_confidence >= 62:
        score += 6.0
    elif sectional_confidence >= 45:
        score += 3.0

    score += (predictability - 50.0) * 0.10
    score += ((trainer_score_metric + jockey_score_metric) / 2.0 - 50.0) * 0.06

    if has_horse_results:
        score += 4.0
    if starts == 0:
        score -= 6.0
    return clip(score, 20.0, 95.0)


def performance_rating(
    finish_pct_value: float,
    margin_value: float,
    speed_score_value: float,
    sectional_proxy_value: float,
    race_strength_score_value: float,
) -> float:
    margin_score = 100.0 if pd.isna(margin_value) else clip(100.0 - (min(margin_value, 15.0) * 6.5), 0.0, 100.0)
    value = (
        0.42 * (finish_pct_value * 100.0)
        + 0.22 * speed_score_value
        + 0.16 * margin_score
        + 0.12 * sectional_proxy_value
        + 0.08 * race_strength_score_value
    )
    return clip(value, 0.0, 100.0)


def race_strength_score(rows: list[dict[str, object]]) -> tuple[float, str, int, float]:
    values = [float(item["horse_results_strength_v3"]) for item in rows if not pd.isna(item["horse_results_strength_v3"])]
    total = len(rows)
    profiled = len(values)
    coverage = (profiled / total) if total else 0.0
    if values:
        ordered = sorted(values, reverse=True)
        top1 = ordered[0]
        top3 = float(np.mean(ordered[:3]))
        top5 = float(np.mean(ordered[:5]))
        avg = float(np.mean(ordered))
        score = (
            0.34 * top3
            + 0.26 * top5
            + 0.20 * avg
            + 0.12 * top1
            + 0.08 * (coverage * 100.0)
        )
    else:
        score = 35.0 + (coverage * 15.0)

    score = clip(score, 0.0, 100.0)
    if score >= 72:
        band = "ELITE"
    elif score >= 64:
        band = "STRONG"
    elif score >= 56:
        band = "SOLID"
    elif score >= 48:
        band = "WEAK"
    else:
        band = "VERY_WEAK"
    return score, band, profiled, coverage


def rank_bucket(rank_value: float) -> str:
    if pd.isna(rank_value):
        return "NO_RANK"
    rank_int = int(rank_value)
    if rank_int <= 10:
        return f"RANK_{rank_int}"
    return "RANK_11_PLUS"


def compute_roi_table(df: pd.DataFrame, group_col: str, output_col: str) -> pd.DataFrame:
    work = df.copy()
    if "sp_num" not in work.columns:
        if "sp" not in work.columns:
            return pd.DataFrame(columns=[output_col, "bets", "winners", "strike_rate", "avg_sp", "total_return", "total_profit", "roi"])
        work["sp_num"] = work["sp"].map(parse_float)
    work = work[work["sp_num"].notna()].copy()
    if work.empty:
        return pd.DataFrame(columns=[output_col, "bets", "winners", "strike_rate", "avg_sp", "total_return", "total_profit", "roi"])

    work["return"] = np.where(work["won"] == 1, work["sp_num"], 0.0)
    work["profit"] = work["return"] - 1.0

    table = (
        work.groupby(group_col, dropna=False)
        .agg(
            bets=("horse", "count"),
            winners=("won", "sum"),
            strike_rate=("won", "mean"),
            avg_sp=("sp_num", "mean"),
            total_return=("return", "sum"),
            total_profit=("profit", "sum"),
        )
        .reset_index()
        .rename(columns={group_col: output_col})
    )
    table["roi"] = np.where(table["bets"] > 0, table["total_profit"] / table["bets"], math.nan)
    for col in ["strike_rate", "avg_sp", "total_return", "total_profit", "roi"]:
        table[col] = pd.to_numeric(table[col], errors="coerce").round(4)
    return table


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input: {INPUT}")

    df = pd.read_csv(INPUT, low_memory=False)

    required = {"meeting_date", "track", "race_no", "horseName", "finishPosition"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work["meeting_date"] = work["meeting_date"].astype(str).str.slice(0, 10)
    work["track_norm"] = work["track"].map(norm_track)
    work["race_no_int"] = pd.to_numeric(work["race_no"], errors="coerce").astype("Int64")
    work["horse"] = work["horseName"].map(clean_text)
    work["horse_key"] = work["horseName"].map(canon_horse)
    work["trainer_key"] = work["trainer"].map(person_key)
    work["jockey_key"] = work["jockey"].map(person_key)
    work["finish_position"] = work["finishPosition"].map(parse_pos)
    work["sp_num"] = work["sp"].map(parse_float) if "sp" in work.columns else math.nan
    work["margin_num"] = work["margin"].map(parse_float) if "margin" in work.columns else math.nan
    work["barrier_num"] = work["barrier"].map(parse_float) if "barrier" in work.columns else math.nan
    work["weight_num"] = work["weight"].map(parse_float) if "weight" in work.columns else math.nan
    work["distance_num"] = work["distance"].map(parse_distance)
    work["race_time_seconds"] = work["raceTime"].map(parse_time_seconds) if "raceTime" in work.columns else math.nan
    work["class_clean"] = work["raceClass"].map(clean_class) if "raceClass" in work.columns else "HANDICAP"
    work["class_family"] = work["class_clean"].map(class_family)
    work["distance_band"] = work["distance_num"].map(distance_band)
    work["condition_group"] = work["trackCondition"].map(condition_group) if "trackCondition" in work.columns else "UNKNOWN"
    work["race_key"] = (
        work["meeting_date"]
        + "|"
        + work["track_norm"]
        + "|R"
        + work["race_no_int"].astype(str)
    )

    in_run = work["inRun"].map(parse_in_run_positions) if "inRun" in work.columns else [(math.nan, math.nan)] * len(work)
    work["early_pos"] = [pair[0] for pair in in_run]
    work["late_pos"] = [pair[1] for pair in in_run]

    work = work[work["horse_key"].ne("") & work["race_no_int"].notna() & work["finish_position"].notna()].copy()

    race_sizes = work.groupby("race_key")["horse_key"].size().rename("field_size").reset_index()
    work = work.merge(race_sizes, on="race_key", how="left")
    work["finish_pct"] = [
        finish_pct(pos, int(size))
        for pos, size in zip(work["finish_position"], work["field_size"])
    ]
    work["won"] = work["finish_position"].eq(1).astype(int)
    work["placed"] = work["finish_position"].le(3).astype(int)
    work["top4"] = work["finish_position"].le(4).astype(int)
    work["speed_score_run"] = [
        speed_score(distance, race_time)
        for distance, race_time in zip(work["distance_num"], work["race_time_seconds"])
    ]
    work["sectional_proxy_run"] = [
        run_sectional_proxy(early, late, finish_pct_value, int(field_size), margin)
        for early, late, finish_pct_value, field_size, margin in zip(
            work["early_pos"],
            work["late_pos"],
            work["finish_pct"],
            work["field_size"],
            work["margin_num"],
        )
    ]

    horse_histories: dict[str, HorseHistory] = {}
    trainer_histories: dict[str, EntityHistory] = {}
    jockey_histories: dict[str, EntityHistory] = {}

    class_stats: dict[str, ParSamples] = defaultdict(ParSamples)
    family_stats: dict[str, ParSamples] = defaultdict(ParSamples)
    distance_stats: dict[str, list[float]] = defaultdict(list)
    condition_stats: dict[str, list[float]] = defaultdict(list)
    global_winner_ratings: list[float] = []
    race_strength_history: list[float] = []

    output_rows: list[dict[str, object]] = []

    grouped_dates = list(work.groupby("meeting_date", sort=True))

    for meeting_date, day_frame in grouped_dates:
        global_base = safe_median(global_winner_ratings, DEFAULT_GLOBAL_TARGET)
        global_race_strength_avg = safe_mean(race_strength_history)
        if pd.isna(global_race_strength_avg):
            global_race_strength_avg = DEFAULT_GLOBAL_RACE_STRENGTH

        class_cache: dict[tuple[str, str], tuple[float, str, str]] = {}
        distance_cache: dict[str, tuple[float, str]] = {}
        condition_cache: dict[str, tuple[float, str]] = {}

        day_scored_rows: list[dict[str, object]] = []

        for _, race_frame in day_frame.sort_values(["track_norm", "race_no_int", "horse"]).groupby("race_key", sort=False):
            prelim_rows: list[dict[str, object]] = []

            for row in race_frame.to_dict("records"):
                horse_history = horse_histories.get(row["horse_key"])
                trainer_history = trainer_histories.get(row["trainer_key"])
                jockey_history = jockey_histories.get(row["jockey_key"])

                trainer_score_metric = entity_strength(trainer_history)
                jockey_score_metric = entity_strength(jockey_history)
                barrier_score_metric = barrier_score(row["barrier_num"], int(row["field_size"]), row["distance_num"])
                weight_score_metric = weight_score(row["weight_num"])
                market_score_metric = market_score(row["sp_num"])
                connection_metric = connection_score_value(
                    trainer_score_metric,
                    jockey_score_metric,
                    barrier_score_metric,
                    weight_score_metric,
                    market_score_metric,
                )

                horse_results_metric, results_reliability = horse_results_strength(horse_history)
                projected_metric, projection_method = projected_rating(horse_history)
                starts_before = 0 if horse_history is None else horse_history.starts
                governance = governance_status(starts_before, row["horse"])
                governance_metric = governance_score(governance)
                projection_floor_metric = projection_floor(governance)

                target_value, target_confidence, target_source = class_par(
                    row["class_clean"],
                    row["class_family"],
                    class_stats,
                    family_stats,
                    global_base,
                    class_cache,
                )
                distance_adjustment, distance_confidence = band_adjustment(
                    row["distance_band"],
                    distance_stats,
                    global_base,
                    18,
                    distance_cache,
                )
                condition_adjustment, condition_confidence = band_adjustment(
                    row["condition_group"],
                    condition_stats,
                    global_base,
                    18,
                    condition_cache,
                )
                race_target_metric = target_value + (0.15 * distance_adjustment) + (0.15 * condition_adjustment)

                if starts_before == 0:
                    projected_metric = fallback_projection(race_target_metric, connection_metric, market_score_metric)
                    governed_projection_metric = min(projected_metric, projection_floor_metric + 6.0)
                elif governance in {"FIRST_STARTER_OR_UNKNOWN", "IMPORT_UNKNOWN"}:
                    governed_projection_metric = min(projected_metric, projection_floor_metric)
                else:
                    governed_projection_metric = clip(
                        max(projected_metric, projection_floor_metric),
                        0.0,
                        100.0,
                    )

                projection_gap_metric = governed_projection_metric - race_target_metric
                projection_confidence_metric = projection_confidence_label(starts_before, target_confidence)

                sectional_strength_metric, sectional_confidence_metric, sectional_source = sectional_profile(
                    horse_history,
                    connection_metric,
                    global_race_strength_avg,
                )
                predictability_metric = predictability_score(horse_history, connection_metric)

                prelim_rows.append(
                    {
                        **row,
                        "starts_before": starts_before,
                        "trainer_score": round(trainer_score_metric, 3),
                        "jockey_score": round(jockey_score_metric, 3),
                        "barrier_score": round(barrier_score_metric, 3),
                        "weight_score": round(weight_score_metric, 3),
                        "market_score": round(market_score_metric, 3),
                        "connection_score": round(connection_metric, 3),
                        "horse_results_strength_v3": round(horse_results_metric, 3) if not pd.isna(horse_results_metric) else math.nan,
                        "results_reliability_v3": results_reliability,
                        "projection_status_v6": governance,
                        "projection_governance_score_v6": round(governance_metric, 3),
                        "projection_floor_v6": round(projection_floor_metric, 3),
                        "projected_rating_v5_2": round(projected_metric, 3),
                        "projection_method_v5_2": projection_method if starts_before > 0 else "connections + class target fallback",
                        "governed_projection_rating_v6": round(governed_projection_metric, 3),
                        "race_target_rating_v5_2": round(race_target_metric, 3),
                        "target_formula_v5_2": TARGET_FORMULA,
                        "target_confidence_v5_2": target_confidence,
                        "target_source_v5_2": target_source,
                        "distance_adjustment_v5_2": round(distance_adjustment, 3),
                        "distance_adjustment_confidence_v5_2": distance_confidence,
                        "condition_adjustment_v5_2": round(condition_adjustment, 3),
                        "condition_adjustment_confidence_v5_2": condition_confidence,
                        "projection_gap_v5_2": round(projection_gap_metric, 3),
                        "projection_confidence_v5_2": projection_confidence_metric,
                        "sectional_strength_rating": round(sectional_strength_metric, 3),
                        "sectional_strength_confidence": round(sectional_confidence_metric, 3),
                        "sectional_strength_source": sectional_source,
                        "predictability_score_v1": round(predictability_metric, 3),
                    }
                )

            race_strength_metric, race_strength_band, profiled_runners, profile_coverage = race_strength_score(prelim_rows)

            scored_rows: list[dict[str, object]] = []
            for item in prelim_rows:
                profile_fill = item["horse_results_strength_v3"]
                if pd.isna(profile_fill):
                    profile_fill = math.nan

                projection_norm = float(item["governed_projection_rating_v6"])
                governance_norm = float(item["projection_governance_score_v6"])
                sectional_norm = float(item["sectional_strength_rating"])
                profile_norm = float(profile_fill) if not pd.isna(profile_fill) else float(item["connection_score"])
                predictability_norm = float(item["predictability_score_v1"])
                race_strength_norm = float(race_strength_metric)

                base_strength_v3 = (
                    (0.28 * projection_norm)
                    + (0.17 * governance_norm)
                    + (0.22 * sectional_norm)
                    + (0.15 * profile_norm)
                    + (0.10 * predictability_norm)
                    + (0.08 * race_strength_norm)
                )

                strength_adjusted_rating_v3 = clip(
                    base_strength_v3 * governance_multiplier(item["projection_status_v6"]),
                    0.0,
                    100.0,
                )
                strength_adjusted_rating_v4 = clip(
                    ((strength_adjusted_rating_v3 * 0.88) + (race_strength_norm * 0.12))
                    * race_strength_adjustment(race_strength_norm),
                    0.0,
                    100.0,
                )
                strength_adjusted_rating_v5 = clip(
                    (0.56 * strength_adjusted_rating_v4)
                    + (0.34 * (float(profile_fill) if not pd.isna(profile_fill) else 28.0))
                    + (0.10 * race_strength_norm),
                    0.0,
                    100.0,
                )
                horse_results_fill_v6 = float(profile_fill) if not pd.isna(profile_fill) else strength_adjusted_rating_v5
                strength_adjusted_rating_v6 = clip(
                    (
                        (0.72 * strength_adjusted_rating_v5)
                        + (0.18 * horse_results_fill_v6)
                        + (0.10 * race_strength_norm)
                    )
                    * ability_multiplier(item["projection_status_v6"]),
                    0.0,
                    100.0,
                )

                confidence_score_metric = confidence_score(
                    item["projection_status_v6"],
                    int(item["starts_before"]),
                    item["target_confidence_v5_2"],
                    item["projection_confidence_v5_2"],
                    float(item["sectional_strength_confidence"]),
                    float(item["predictability_score_v1"]),
                    float(item["trainer_score"]),
                    float(item["jockey_score"]),
                    not pd.isna(item["horse_results_strength_v3"]),
                )
                confidence_adjusted_rating_v6 = clip(
                    strength_adjusted_rating_v6 * confidence_multiplier(item["projection_status_v6"], confidence_score_metric),
                    0.0,
                    100.0,
                )
                horse_results_fill_runner = float(profile_fill) if not pd.isna(profile_fill) else strength_adjusted_rating_v6
                runner_score_metric = clip(
                    (0.72 * strength_adjusted_rating_v6)
                    + (0.18 * horse_results_fill_runner)
                    + (0.10 * race_strength_norm),
                    0.0,
                    100.0,
                )

                scored_rows.append(
                    {
                        **item,
                        "live_race_strength_score_v3": round(race_strength_norm, 3),
                        "live_race_strength_band_v3": race_strength_band,
                        "profiled_runners_v3": int(profiled_runners),
                        "profile_coverage_v3": round(profile_coverage, 4),
                        "strength_adjusted_rating_v3": round(strength_adjusted_rating_v3, 3),
                        "strength_adjusted_rating_v4": round(strength_adjusted_rating_v4, 3),
                        "strength_adjusted_rating_v5": round(strength_adjusted_rating_v5, 3),
                        "strength_adjusted_rating_v6": round(strength_adjusted_rating_v6, 3),
                        "confidence_score_v1": round(confidence_score_metric, 3),
                        "confidence_adjusted_rating_v6": round(confidence_adjusted_rating_v6, 3),
                        "runner_score": round(runner_score_metric, 3),
                        "score_band_v4": score_band(round(runner_score_metric, 3)),
                    }
                )

            race_scores = pd.Series([item["runner_score"] for item in scored_rows], dtype="float64")
            top_score = float(race_scores.max()) if len(race_scores) else math.nan
            tied_top_count = int((race_scores == top_score).sum()) if len(race_scores) else 0
            all_identical = int(race_scores.nunique(dropna=False) <= 1) if len(race_scores) else 0

            rank_frame = pd.DataFrame(scored_rows)
            rank_frame = rank_frame.sort_values(
                ["runner_score", "confidence_adjusted_rating_v6", "connection_score", "horse"],
                ascending=[False, False, False, True],
            ).reset_index(drop=True)
            rank_frame["runner_rank"] = (
                rank_frame["runner_score"]
                .rank(method="min", ascending=False)
                .astype(int)
            )
            rank_frame["rank_bucket"] = rank_frame["runner_rank"].map(rank_bucket)
            rank_frame["top_score_tied_in_race"] = 1 if tied_top_count > 1 else 0
            rank_frame["all_scores_identical_in_race"] = all_identical
            rank_frame["tied_top_score_count"] = tied_top_count

            scored_rows = rank_frame.to_dict("records")
            day_scored_rows.extend(scored_rows)
            output_rows.extend(scored_rows)

        for item in day_scored_rows:
            run_rating_metric = performance_rating(
                float(item["finish_pct"]),
                float(item["margin_num"]) if not pd.isna(item["margin_num"]) else math.nan,
                float(item["speed_score_run"]),
                float(item["sectional_proxy_run"]),
                float(item["live_race_strength_score_v3"]),
            )

            horse_history = horse_histories.setdefault(item["horse_key"], HorseHistory())
            horse_history.update(
                finish_pct=float(item["finish_pct"]),
                run_rating=run_rating_metric,
                sectional_score=float(item["sectional_proxy_run"]),
                race_strength_score=float(item["live_race_strength_score_v3"]),
                won=bool(item["won"]),
                placed=bool(item["placed"]),
                top4=bool(item["top4"]),
            )

            if item["trainer_key"]:
                trainer_history = trainer_histories.setdefault(item["trainer_key"], EntityHistory())
                trainer_history.update(float(item["finish_pct"]), bool(item["won"]), bool(item["placed"]))

            if item["jockey_key"]:
                jockey_history = jockey_histories.setdefault(item["jockey_key"], EntityHistory())
                jockey_history.update(float(item["finish_pct"]), bool(item["won"]), bool(item["placed"]))

            class_stats[item["class_clean"]].update(run_rating_metric, float(item["finish_position"]))
            family_stats[item["class_family"]].update(run_rating_metric, float(item["finish_position"]))
            if float(item["finish_position"]) == 1:
                distance_stats[item["distance_band"]].append(run_rating_metric)
                condition_stats[item["condition_group"]].append(run_rating_metric)
                global_winner_ratings.append(run_rating_metric)

        race_strength_history.extend(
            pd.DataFrame(day_scored_rows)[["race_key", "live_race_strength_score_v3"]]
            .drop_duplicates("race_key")["live_race_strength_score_v3"]
            .astype(float)
            .tolist()
        )

    out = pd.DataFrame(output_rows)
    if out.empty:
        raise RuntimeError("Historical replay produced no rows.")

    if int(out.groupby("race_key")["runner_score"].nunique(dropna=False).le(1).sum()) > 0:
        raise RuntimeError("Replay failed identical-score guard: at least one race still has all runners on the same score.")

    final_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "runner_score",
        "runner_rank",
        "sp",
        "finish_position",
        "won",
        "score_band_v4",
        "projection_status_v6",
        "starts_before",
        "projected_rating_v5_2",
        "governed_projection_rating_v6",
        "race_target_rating_v5_2",
        "projection_gap_v5_2",
        "sectional_strength_rating",
        "horse_results_strength_v3",
        "live_race_strength_score_v3",
        "strength_adjusted_rating_v6",
        "confidence_score_v1",
        "confidence_adjusted_rating_v6",
        "connection_score",
        "trainer_score",
        "jockey_score",
        "market_score",
        "results_reliability_v3",
        "top_score_tied_in_race",
        "tied_top_score_count",
        "all_scores_identical_in_race",
        "race_key",
        "track_norm",
        "horse_key",
    ]
    for col in final_cols:
        if col not in out.columns:
            out[col] = ""

    out = out[final_cols].sort_values(["meeting_date", "track_norm", "race_no", "runner_rank", "horse"])
    out.to_csv(OUT, index=False)

    winners = out[out["won"] == 1].copy()
    tied_top_races = (
        out[["race_key", "tied_top_score_count"]]
        .drop_duplicates("race_key")
        .query("tied_top_score_count > 1")
    )
    identical_score_races = (
        out[["race_key", "all_scores_identical_in_race"]]
        .drop_duplicates("race_key")
        .query("all_scores_identical_in_race == 1")
    )

    summary = pd.DataFrame(
        [
            {"metric": "rows", "value": len(out)},
            {"metric": "races", "value": out["race_key"].nunique()},
            {"metric": "winners", "value": len(winners)},
            {"metric": "winner_top1_rate", "value": round(winners["runner_rank"].le(1).mean(), 4)},
            {"metric": "winner_top3_rate", "value": round(winners["runner_rank"].le(3).mean(), 4)},
            {"metric": "winner_top5_rate", "value": round(winners["runner_rank"].le(5).mean(), 4)},
            {"metric": "winner_top10_rate", "value": round(winners["runner_rank"].le(10).mean(), 4)},
            {"metric": "avg_runner_score", "value": round(out["runner_score"].mean(), 4)},
            {"metric": "avg_winner_score", "value": round(winners["runner_score"].mean(), 4)},
            {"metric": "races_with_tied_top_score", "value": len(tied_top_races)},
            {"metric": "races_with_all_identical_scores", "value": len(identical_score_races)},
            {"metric": "roi_rows_with_sp", "value": int(out["sp"].fillna("").astype(str).str.strip().ne("").sum())},
        ]
    )
    summary.to_csv(SUMMARY, index=False)

    roi_rank = compute_roi_table(out.assign(rank_group=out["runner_rank"].astype(int).where(out["runner_rank"] <= 10, 11)), "rank_group", "rank_group")
    roi_rank["rank_group"] = roi_rank["rank_group"].replace({11: "11_PLUS"}).astype(str)
    roi_rank.to_csv(ROI_BY_RANK, index=False)

    roi_score_band = compute_roi_table(out, "score_band_v4", "score_band_v4")
    roi_score_band.to_csv(ROI_BY_SCORE_BAND, index=False)

    print("[EDGEIQ_HISTORICAL_REPLAY_V1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"races={out['race_key'].nunique()}")
    print(f"winner_top1_rate={round(winners['runner_rank'].le(1).mean(), 4)}")
    print(f"winner_top3_rate={round(winners['runner_rank'].le(3).mean(), 4)}")
    print(f"winner_top5_rate={round(winners['runner_rank'].le(5).mean(), 4)}")
    print(f"winner_top10_rate={round(winners['runner_rank'].le(10).mean(), 4)}")
    print(f"races_with_tied_top_score={len(tied_top_races)}")
    print(f"races_with_all_identical_scores={len(identical_score_races)}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")
    print(f"roi_by_rank={ROI_BY_RANK}")
    print(f"roi_by_score_band={ROI_BY_SCORE_BAND}")


if __name__ == "__main__":
    main()
