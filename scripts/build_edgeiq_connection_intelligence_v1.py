from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"
RESULTS_PATH = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"
PERF_PATH = DATA / "edgeiq_historical_performance_rating_v6_research.csv"
DNA_PATH = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
SCORECARD_PATH = DATA / "edgeiq_live_runner_factor_scorecard_v2.csv"

OUT_PATH = DATA / "edgeiq_connection_intelligence_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_connection_intelligence_v1_summary.csv"


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


def parse_float(value: object) -> float | None:
    text = safe_text(value)
    if not text:
        return None
    text = text.replace("$", "").replace("%", "").replace(",", "").strip()
    if text in {"-", "—", "N/A"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number):
        return None
    return number


def parse_int(value: object) -> int | None:
    number = parse_float(value)
    if number is None:
        return None
    return int(round(number))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_track(value: object) -> str:
    text = upper_text(value)
    if not text:
        return ""
    replacements = {
        "SPORTSBET-": "",
        "SPORTSBET ": "",
        "BET365 ": "",
        "TAB ": "",
        "MVRC ": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("SYNTHETIC", "SYNTH")
    text = text.replace("SYN ", "SYNTH ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return normalize_spaces(text)


def normalize_horse(value: object) -> str:
    text = upper_text(value)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


PERSON_SPLIT_RE = re.compile(r"[^A-Z0-9]+")
PERSON_SUFFIXES = {"JNR", "JR", "SNR", "SR"}


def person_tokens(value: object) -> list[str]:
    text = upper_text(value)
    if not text:
        return []
    tokens = [token for token in PERSON_SPLIT_RE.split(text) if token]
    while tokens and tokens[-1] in PERSON_SUFFIXES:
        tokens.pop()
    return tokens


def person_compact(value: object) -> str:
    return "".join(person_tokens(value))


def person_first_initial_surname_key(value: object) -> str:
    tokens = person_tokens(value)
    if not tokens:
        return ""
    surname = tokens[-1]
    first_initial = tokens[0][0]
    return f"{first_initial}{surname}"


def distance_bucket(value: object) -> str:
    distance = parse_int(value)
    if distance is None:
        return "UNKNOWN"
    if 800 <= distance <= 999:
        return "800_999"
    if 1000 <= distance <= 1199:
        return "1000_1199"
    if 1200 <= distance <= 1399:
        return "1200_1399"
    if 1400 <= distance <= 1599:
        return "1400_1599"
    if 1600 <= distance <= 1999:
        return "1600_1999"
    if distance >= 2000:
        return "2000_PLUS"
    return "UNKNOWN"


def condition_group(value: object, track_value: object = "") -> str:
    text = upper_text(value)
    track_text = upper_text(track_value)
    if "SYNTH" in text or "SYNTH" in track_text:
        return "SYNTH"
    if text.startswith("HVY") or text.startswith("HEAVY") or text.startswith("H "):
        return "HEAVY"
    if text.startswith("SOFT") or text.startswith("SFT") or text.startswith("S "):
        return "SOFT"
    if text.startswith("GOOD") or text.startswith("GD") or text.startswith("G "):
        return "GOOD"
    if "HEAVY" in text:
        return "HEAVY"
    if "SOFT" in text:
        return "SOFT"
    if "GOOD" in text:
        return "GOOD"
    return "UNKNOWN"


def is_scratched_row(row: pd.Series) -> bool:
    values = [
        upper_text(row.get("is_scratched")),
        upper_text(row.get("scratch_status")),
        upper_text(row.get("runner_status")),
    ]
    return any(value in {"TRUE", "YES", "Y", "1", "SCRATCHED", "LATE_SCRATCHED", "LATESCRATCHED"} for value in values)


def choose_first_existing(columns: Iterable[str], available: set[str]) -> str | None:
    for column in columns:
        if column in available:
            return column
    return None


def pct(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value * 100.0, 4)


def pct_from_counts(wins: int, starts: int) -> float | None:
    if starts <= 0:
        return None
    return round((wins / starts) * 100.0, 4)


def fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}%"


def fmt_pts(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.{digits}f} pts"


def fmt_count(value: int | None) -> str:
    if value is None:
        return "0"
    return str(int(value))


def fmt_sp(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"${value:.2f}"


def read_csv(path: Path, preferred_columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    if preferred_columns is None:
        return pd.read_csv(path, dtype=str).fillna("")
    header = pd.read_csv(path, nrows=0)
    usecols = [column for column in preferred_columns if column in header.columns]
    return pd.read_csv(path, dtype=str, usecols=usecols).fillna("")


def build_perf_condition_map(perf_df: pd.DataFrame) -> dict[tuple[str, str, str, int | None], str]:
    result: dict[tuple[str, str, str, int | None], str] = {}
    if perf_df.empty:
        return result
    for row in perf_df.to_dict("records"):
        key = (
            safe_text(row.get("race_date")),
            normalize_track(row.get("track")),
            normalize_horse(row.get("horse")),
            parse_int(row.get("finish_position")),
        )
        condition_value = safe_text(row.get("condition_recovered"))
        if key not in result and condition_value:
            result[key] = condition_value
    return result


def build_runner_key(row: pd.Series | dict[str, object]) -> str:
    race_date = safe_text(row.get("race_date") or row.get("meeting_date"))
    track = upper_text(row.get("track"))
    race_no = safe_text(row.get("race_no"))
    horse_key = upper_text(row.get("horse_key")) or normalize_horse(row.get("horse"))
    return "|".join([race_date, track, race_no, horse_key])


def add_score_adjustment(
    positives: list[dict[str, object]],
    risks: list[dict[str, object]],
    label: str,
    value_text: str,
    delta: int,
) -> int:
    if delta > 0:
        positives.append({"priority": delta, "label": label, "value": value_text})
    elif delta < 0:
        risks.append({"priority": abs(delta), "label": label, "value": value_text})
    return delta


def score_sr(
    positives: list[dict[str, object]],
    risks: list[dict[str, object]],
    label: str,
    starts: int,
    sr_pct: float | None,
    high_bonus: int,
    medium_bonus: int,
    low_penalty: int,
) -> int:
    if sr_pct is None or starts < 10:
        return 0
    evidence = f"{fmt_pct(sr_pct)} from {starts}"
    if sr_pct >= 18.0:
        return add_score_adjustment(positives, risks, label, evidence, high_bonus)
    if sr_pct >= 12.0:
        return add_score_adjustment(positives, risks, label, evidence, medium_bonus)
    if sr_pct <= 6.0:
        return add_score_adjustment(positives, risks, label, evidence, low_penalty)
    return 0


def score_combo(
    positives: list[dict[str, object]],
    risks: list[dict[str, object]],
    label: str,
    starts: int,
    sr_pct: float | None,
) -> int:
    if sr_pct is None or starts < 8:
        return 0
    evidence = f"{fmt_pct(sr_pct)} from {starts}"
    if sr_pct >= 20.0:
        return add_score_adjustment(positives, risks, label, evidence, 10)
    if sr_pct >= 14.0:
        return add_score_adjustment(positives, risks, label, evidence, 5)
    if sr_pct <= 5.0:
        return add_score_adjustment(positives, risks, label, evidence, -6)
    return 0


def score_combo_track(
    positives: list[dict[str, object]],
    risks: list[dict[str, object]],
    label: str,
    starts: int,
    sr_pct: float | None,
) -> int:
    if sr_pct is None or starts < 5:
        return 0
    evidence = f"{fmt_pct(sr_pct)} from {starts}"
    if sr_pct >= 20.0:
        return add_score_adjustment(positives, risks, label, evidence, 8)
    if sr_pct <= 5.0:
        return add_score_adjustment(positives, risks, label, evidence, -5)
    return 0


def build_market_label(delta_prop: float | None, sample: int) -> str:
    if delta_prop is None or sample < 10:
        return "INSUFFICIENT_SP_SAMPLE"
    if delta_prop >= 0.05:
        return "OUTPERFORMS_MARKET"
    if delta_prop <= -0.05:
        return "UNDERPERFORMS_MARKET"
    return "MARKET_NEUTRAL"


def band_from_score(score: float) -> str:
    if score >= 80:
        return "ELITE"
    if score >= 68:
        return "STRONG"
    if score >= 56:
        return "POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 32:
        return "NEGATIVE"
    return "POOR"


def narrative_for_row(
    trainer_track_starts: int,
    jockey_track_starts: int,
    combo_starts: int,
    positives: list[dict[str, object]],
    risks: list[dict[str, object]],
    market_label: str,
) -> str:
    if combo_starts < 5 and trainer_track_starts < 10 and jockey_track_starts < 10:
        return "Connection evidence is limited: trainer/jockey combination has insufficient track/combo sample."
    if positives:
        lead = positives[0]
        second = positives[1] if len(positives) > 1 else None
        extra = f" and {second['label'].lower()} {second['value']}" if second else ""
        market = " and outperform market expectation." if market_label == "OUTPERFORMS_MARKET" else "."
        return f"Connection profile is strong: {lead['label']} {lead['value']}{extra}{market}"
    if market_label == "UNDERPERFORMS_MARKET":
        return "Market expectation risk: this connection has underperformed starting-price expectation from available history."
    if risks:
        lead = risks[0]
        return f"Connection profile is under pressure: {lead['label']} {lead['value']}."
    return "Connection evidence is neutral: enough trainer/jockey data but no standout positive or negative edge."


def build_stat_lookup(df: pd.DataFrame, group_cols: list[str]) -> dict[tuple[object, ...], dict[str, float | int]]:
    if df.empty:
        return {}
    grouped = (
        df.groupby(group_cols, dropna=False)
        .agg(starts=("win_flag", "size"), wins=("win_flag", "sum"))
        .reset_index()
    )
    result: dict[tuple[object, ...], dict[str, float | int]] = {}
    for row in grouped.to_dict("records"):
        key = tuple(row[column] for column in group_cols)
        starts = int(row["starts"])
        wins = int(row["wins"])
        result[key] = {
            "starts": starts,
            "wins": wins,
            "sr_pct": pct_from_counts(wins, starts),
        }
    return result


def build_sp_lookup(df: pd.DataFrame) -> dict[str, dict[str, float | int]]:
    if df.empty:
        return {}
    sp_df = df[df["combo_key"] != ""].copy()
    sp_df = sp_df[sp_df["sp_num"].notna()].copy()
    if sp_df.empty:
        return {}
    sp_df["implied_prob"] = 1.0 / sp_df["sp_num"]
    grouped = (
        sp_df.groupby("combo_key", dropna=False)
        .agg(
            sp_sample_starts=("win_flag", "size"),
            wins=("win_flag", "sum"),
            avg_sp=("sp_num", "mean"),
            sp_expectation_win_rate=("implied_prob", "mean"),
        )
        .reset_index()
    )
    result: dict[str, dict[str, float | int]] = {}
    for row in grouped.to_dict("records"):
        sample = int(row["sp_sample_starts"])
        wins = int(row["wins"])
        actual_rate = wins / sample if sample else None
        implied_rate = float(row["sp_expectation_win_rate"]) if sample else None
        delta_prop = (actual_rate - implied_rate) if actual_rate is not None and implied_rate is not None else None
        result[str(row["combo_key"])] = {
            "sp_sample_starts": sample,
            "avg_sp": round(float(row["avg_sp"]), 4) if sample else None,
            "actual_win_rate_pct": pct(actual_rate),
            "sp_expectation_win_rate_pct": pct(implied_rate),
            "sp_expectation_delta_pct": pct(delta_prop),
            "market_expectation_label": build_market_label(delta_prop, sample),
            "delta_prop": delta_prop,
        }
    return result


def main() -> None:
    built_at = now_iso()

    live_columns = [
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "trainer",
        "jockey",
        "distance",
        "race_class",
        "track_condition",
        "is_scratched",
        "scratch_status",
        "runner_status",
        "runner_key",
    ]
    results_columns = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horseName",
        "horseKey",
        "trainer",
        "jockey",
        "distance",
        "trackCondition",
        "finishPosition",
        "sp",
        "stab",
    ]
    perf_columns = [
        "horse",
        "race_date",
        "track",
        "distance",
        "condition_recovered",
        "finish_position",
    ]
    context_columns = ["race_date", "track", "race_no", "horse", "horse_key", "runner_key"]

    live_df = read_csv(LIVE_PATH, live_columns)
    results_df = read_csv(RESULTS_PATH, results_columns)
    perf_df = read_csv(PERF_PATH, perf_columns)
    dna_df = read_csv(DNA_PATH, context_columns)
    scorecard_df = read_csv(SCORECARD_PATH, context_columns)

    if live_df.empty:
        raise FileNotFoundError(f"Live runner board is missing or empty: {LIVE_PATH}")
    if results_df.empty:
        raise FileNotFoundError(f"Historical results warehouse is missing or empty: {RESULTS_PATH}")

    input_live_rows = len(live_df)
    live_df = live_df[~live_df.apply(is_scratched_row, axis=1)].copy()
    live_df = live_df.fillna("")
    live_df["runner_join_key"] = live_df.apply(build_runner_key, axis=1)
    live_df["norm_track"] = live_df["track"].apply(normalize_track)
    live_df["distance_bucket"] = live_df["distance"].apply(distance_bucket)
    live_df["condition_group"] = live_df.apply(lambda row: condition_group(row.get("track_condition"), row.get("track")), axis=1)
    live_df["trainer_key_simple"] = live_df["trainer"].apply(person_first_initial_surname_key)
    live_df["jockey_key_simple"] = live_df["jockey"].apply(person_first_initial_surname_key)
    live_df["combo_key"] = live_df.apply(
        lambda row: f"{row['trainer_key_simple']}|{row['jockey_key_simple']}" if row["trainer_key_simple"] and row["jockey_key_simple"] else "",
        axis=1,
    )

    perf_condition_map = build_perf_condition_map(perf_df)

    results_df = results_df.fillna("")
    results_df["race_date"] = results_df["meeting_date"].apply(safe_text)
    results_df["norm_track"] = results_df["track"].apply(normalize_track)
    results_df["horse_norm"] = results_df.apply(
        lambda row: normalize_horse(row.get("horseKey")) or normalize_horse(row.get("horseName")),
        axis=1,
    )
    results_df["distance_bucket"] = results_df["distance"].apply(distance_bucket)
    results_df["finish_position_num"] = results_df["finishPosition"].apply(parse_int)
    results_df["win_flag"] = results_df["finish_position_num"].apply(lambda value: 1 if value == 1 else 0)
    results_df["sp_num"] = results_df.apply(
        lambda row: next(
            (
                price for price in (
                    parse_float(row.get("sp")),
                    parse_float(row.get("stab")),
                )
                if price is not None and price > 1.0
            ),
            None,
        ),
        axis=1,
    )
    results_df["trainer_key_simple"] = results_df["trainer"].apply(person_first_initial_surname_key)
    results_df["jockey_key_simple"] = results_df["jockey"].apply(person_first_initial_surname_key)
    results_df["combo_key"] = results_df.apply(
        lambda row: f"{row['trainer_key_simple']}|{row['jockey_key_simple']}" if row["trainer_key_simple"] and row["jockey_key_simple"] else "",
        axis=1,
    )
    results_df["condition_fallback"] = results_df.apply(
        lambda row: perf_condition_map.get(
            (
                safe_text(row.get("race_date")),
                normalize_track(row.get("track")),
                normalize_horse(row.get("horseKey")) or normalize_horse(row.get("horseName")),
                parse_int(row.get("finishPosition")),
            ),
            "",
        ),
        axis=1,
    )
    results_df["condition_group"] = results_df.apply(
        lambda row: condition_group(row.get("trackCondition") or row.get("condition_fallback"), row.get("track")),
        axis=1,
    )

    trainer_track_lookup = build_stat_lookup(results_df[results_df["trainer_key_simple"] != ""], ["trainer_key_simple", "norm_track"])
    trainer_distance_lookup = build_stat_lookup(results_df[results_df["trainer_key_simple"] != ""], ["trainer_key_simple", "distance_bucket"])
    trainer_condition_lookup = build_stat_lookup(results_df[results_df["trainer_key_simple"] != ""], ["trainer_key_simple", "condition_group"])

    jockey_track_lookup = build_stat_lookup(results_df[results_df["jockey_key_simple"] != ""], ["jockey_key_simple", "norm_track"])
    jockey_distance_lookup = build_stat_lookup(results_df[results_df["jockey_key_simple"] != ""], ["jockey_key_simple", "distance_bucket"])
    jockey_condition_lookup = build_stat_lookup(results_df[results_df["jockey_key_simple"] != ""], ["jockey_key_simple", "condition_group"])

    combo_lookup = build_stat_lookup(results_df[results_df["combo_key"] != ""], ["combo_key"])
    combo_track_lookup = build_stat_lookup(results_df[results_df["combo_key"] != ""], ["combo_key", "norm_track"])
    sp_lookup = build_sp_lookup(results_df)

    dna_keys = set()
    if not dna_df.empty:
        dna_df["runner_join_key"] = dna_df.apply(build_runner_key, axis=1)
        dna_keys = set(dna_df["runner_join_key"].tolist())
    scorecard_keys = set()
    if not scorecard_df.empty:
        scorecard_df["runner_join_key"] = scorecard_df.apply(build_runner_key, axis=1)
        scorecard_keys = set(scorecard_df["runner_join_key"].tolist())

    out_rows: list[dict[str, object]] = []
    for row in live_df.to_dict("records"):
        trainer_key = safe_text(row.get("trainer_key_simple"))
        jockey_key = safe_text(row.get("jockey_key_simple"))
        combo_key = safe_text(row.get("combo_key"))
        norm_track = safe_text(row.get("norm_track"))
        live_distance_bucket = safe_text(row.get("distance_bucket"))
        live_condition_group = safe_text(row.get("condition_group"))

        trainer_track = trainer_track_lookup.get((trainer_key, norm_track), {})
        trainer_distance = trainer_distance_lookup.get((trainer_key, live_distance_bucket), {})
        trainer_condition = trainer_condition_lookup.get((trainer_key, live_condition_group), {})

        jockey_track = jockey_track_lookup.get((jockey_key, norm_track), {})
        jockey_distance = jockey_distance_lookup.get((jockey_key, live_distance_bucket), {})
        jockey_condition = jockey_condition_lookup.get((jockey_key, live_condition_group), {})

        combo_stats = combo_lookup.get((combo_key,), {})
        combo_track_stats = combo_track_lookup.get((combo_key, norm_track), {})
        sp_stats = sp_lookup.get(combo_key, {})

        positives: list[dict[str, object]] = []
        risks: list[dict[str, object]] = []
        score = 50

        score += score_sr(positives, risks, "Trainer track", int(trainer_track.get("starts", 0)), trainer_track.get("sr_pct"), 8, 4, -5)
        score += score_sr(positives, risks, "Jockey track", int(jockey_track.get("starts", 0)), jockey_track.get("sr_pct"), 8, 4, -5)
        score += score_sr(positives, risks, "Trainer distance", int(trainer_distance.get("starts", 0)), trainer_distance.get("sr_pct"), 5, 0, -4)
        score += score_sr(positives, risks, "Jockey distance", int(jockey_distance.get("starts", 0)), jockey_distance.get("sr_pct"), 5, 0, -4)
        score += score_sr(positives, risks, "Trainer condition", int(trainer_condition.get("starts", 0)), trainer_condition.get("sr_pct"), 4, 0, -3)
        score += score_sr(positives, risks, "Jockey condition", int(jockey_condition.get("starts", 0)), jockey_condition.get("sr_pct"), 4, 0, -3)
        score += score_combo(positives, risks, "Trainer/Jockey combo", int(combo_stats.get("starts", 0)), combo_stats.get("sr_pct"))
        score += score_combo_track(positives, risks, "Combo at track", int(combo_track_stats.get("starts", 0)), combo_track_stats.get("sr_pct"))

        market_label = safe_text(sp_stats.get("market_expectation_label")) or "INSUFFICIENT_SP_SAMPLE"
        delta_prop = sp_stats.get("delta_prop")
        if market_label == "OUTPERFORMS_MARKET":
            score += add_score_adjustment(
                positives,
                risks,
                "Outperforms SP",
                f"{fmt_pts(sp_stats.get('sp_expectation_delta_pct'))} from {fmt_count(sp_stats.get('sp_sample_starts'))}",
                8,
            )
        elif market_label == "UNDERPERFORMS_MARKET":
            score += add_score_adjustment(
                positives,
                risks,
                "Underperforms SP",
                f"{fmt_pts(sp_stats.get('sp_expectation_delta_pct'))} from {fmt_count(sp_stats.get('sp_sample_starts'))}",
                -8,
            )

        score = round(clamp(score, 0, 100), 2)
        band = band_from_score(score)

        positives = sorted(positives, key=lambda item: (-int(item["priority"]), str(item["label"])))
        risks = sorted(risks, key=lambda item: (-int(item["priority"]), str(item["label"])))
        positive_1 = positives[0] if positives else None
        positive_2 = positives[1] if len(positives) > 1 else None
        risk_1 = risks[0] if risks else None

        narrative = narrative_for_row(
            trainer_track_starts=int(trainer_track.get("starts", 0)),
            jockey_track_starts=int(jockey_track.get("starts", 0)),
            combo_starts=int(combo_stats.get("starts", 0)),
            positives=positives,
            risks=risks,
            market_label=market_label,
        )

        runner_join_key = safe_text(row.get("runner_join_key"))
        source_parts = [
            "WAREHOUSE_RESULTS_FULL",
            "TRAINER_KEY=FIRST_INITIAL_SURNAME",
            "JOCKEY_KEY=FIRST_INITIAL_SURNAME",
            "TRACK=NORMALIZED",
            "DNA_CONTEXT=Y" if runner_join_key in dna_keys else "DNA_CONTEXT=N",
            "SCORECARD_CONTEXT=Y" if runner_join_key in scorecard_keys else "SCORECARD_CONTEXT=N",
        ]

        out_rows.append(
            {
                "race_date": safe_text(row.get("race_date")),
                "track": safe_text(row.get("track")),
                "race_no": safe_text(row.get("race_no")),
                "horse": safe_text(row.get("horse")),
                "horse_key": safe_text(row.get("horse_key")),
                "trainer": safe_text(row.get("trainer")),
                "jockey": safe_text(row.get("jockey")),
                "distance": safe_text(row.get("distance")),
                "track_condition": safe_text(row.get("track_condition")),
                "trainer_track_starts": int(trainer_track.get("starts", 0)),
                "trainer_track_wins": int(trainer_track.get("wins", 0)),
                "trainer_track_sr": trainer_track.get("sr_pct"),
                "trainer_distance_starts": int(trainer_distance.get("starts", 0)),
                "trainer_distance_wins": int(trainer_distance.get("wins", 0)),
                "trainer_distance_sr": trainer_distance.get("sr_pct"),
                "trainer_condition_starts": int(trainer_condition.get("starts", 0)),
                "trainer_condition_wins": int(trainer_condition.get("wins", 0)),
                "trainer_condition_sr": trainer_condition.get("sr_pct"),
                "jockey_track_starts": int(jockey_track.get("starts", 0)),
                "jockey_track_wins": int(jockey_track.get("wins", 0)),
                "jockey_track_sr": jockey_track.get("sr_pct"),
                "jockey_distance_starts": int(jockey_distance.get("starts", 0)),
                "jockey_distance_wins": int(jockey_distance.get("wins", 0)),
                "jockey_distance_sr": jockey_distance.get("sr_pct"),
                "jockey_condition_starts": int(jockey_condition.get("starts", 0)),
                "jockey_condition_wins": int(jockey_condition.get("wins", 0)),
                "jockey_condition_sr": jockey_condition.get("sr_pct"),
                "combo_starts": int(combo_stats.get("starts", 0)),
                "combo_wins": int(combo_stats.get("wins", 0)),
                "combo_sr": combo_stats.get("sr_pct"),
                "combo_track_starts": int(combo_track_stats.get("starts", 0)),
                "combo_track_wins": int(combo_track_stats.get("wins", 0)),
                "combo_track_sr": combo_track_stats.get("sr_pct"),
                "sp_sample_starts": int(sp_stats.get("sp_sample_starts", 0) or 0),
                "avg_sp": sp_stats.get("avg_sp"),
                "actual_win_rate": sp_stats.get("actual_win_rate_pct"),
                "sp_expectation_win_rate": sp_stats.get("sp_expectation_win_rate_pct"),
                "sp_expectation_delta": sp_stats.get("sp_expectation_delta_pct"),
                "market_expectation_label": market_label,
                "connection_score": score,
                "connection_band": band,
                "connection_positive_1": positive_1["label"] if positive_1 else "",
                "connection_positive_1_value": positive_1["value"] if positive_1 else "",
                "connection_positive_2": positive_2["label"] if positive_2 else "",
                "connection_positive_2_value": positive_2["value"] if positive_2 else "",
                "connection_risk_1": risk_1["label"] if risk_1 else "",
                "connection_risk_1_value": risk_1["value"] if risk_1 else "",
                "connection_narrative": narrative,
                "source_method": "|".join(source_parts),
                "built_at": built_at,
            }
        )

    out_df = pd.DataFrame(out_rows)
    band_counts = {band: int((out_df["connection_band"] == band).sum()) for band in ["ELITE", "STRONG", "POSITIVE", "NEUTRAL", "NEGATIVE", "POOR"]}
    market_counts = {
        label: int((out_df["market_expectation_label"] == label).sum())
        for label in ["OUTPERFORMS_MARKET", "UNDERPERFORMS_MARKET", "MARKET_NEUTRAL", "INSUFFICIENT_SP_SAMPLE"]
    }

    summary_row = {
        "status": "EDGEIQ_CONNECTION_INTELLIGENCE_V1_BUILT",
        "input_live_rows": input_live_rows,
        "active_runner_rows": len(live_df),
        "historical_result_rows": len(results_df),
        "output_rows": len(out_df),
        "rows_with_trainer": int((out_df["trainer"].astype(str).str.strip() != "").sum()) if not out_df.empty else 0,
        "rows_with_jockey": int((out_df["jockey"].astype(str).str.strip() != "").sum()) if not out_df.empty else 0,
        "rows_with_combo_sample": int((out_df["combo_starts"].fillna(0).astype(float) > 0).sum()) if not out_df.empty else 0,
        "rows_with_sp_sample": int((out_df["sp_sample_starts"].fillna(0).astype(float) > 0).sum()) if not out_df.empty else 0,
        "avg_connection_score": round(float(out_df["connection_score"].astype(float).mean()), 4) if not out_df.empty else 0.0,
        "built_at": built_at,
    }
    for key, value in band_counts.items():
        summary_row[f"band_{key.lower()}_rows"] = value
    for key, value in market_counts.items():
        summary_row[f"market_{key.lower()}_rows"] = value

    out_df.to_csv(OUT_PATH, index=False)
    pd.DataFrame([summary_row]).to_csv(SUMMARY_PATH, index=False)

    print("[EDGEIQ_CONNECTION_INTELLIGENCE_V1] COMPLETE")
    print(f"status={summary_row['status']}")
    print(f"input_live_rows={summary_row['input_live_rows']}")
    print(f"active_runner_rows={summary_row['active_runner_rows']}")
    print(f"historical_result_rows={summary_row['historical_result_rows']}")
    print(f"output_rows={summary_row['output_rows']}")
    print(f"rows_with_combo_sample={summary_row['rows_with_combo_sample']}")
    print(f"rows_with_sp_sample={summary_row['rows_with_sp_sample']}")
    print(f"avg_connection_score={summary_row['avg_connection_score']}")
    print(f"wrote={OUT_PATH}")
    print(f"summary={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
