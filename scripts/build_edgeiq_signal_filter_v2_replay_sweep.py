from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_historical_signal_filter_replay_v1.csv"
SWEEP_OUT = DATA / "edgeiq_signal_filter_v2_replay_sweep.csv"
SUMMARY_OUT = DATA / "edgeiq_signal_filter_v2_replay_sweep_summary.csv"
RECOMMENDED_OUT = DATA / "edgeiq_signal_filter_v2_recommended_rules.csv"

ACTION_SOURCE = "EXECUTE"
RANK_MAX_VALUES = [1, 2, 3]
SCORE_MIN_VALUES = [55, 60, 65, 70]
EXCLUDE_PACE_IGNORE_VALUES = [False, True]
EXCLUDE_GOV_UNKNOWN_VALUES = [False, True]
MIN_SAMPLE = 500
TARGET_WIN_RATE = 0.24
RECOMMENDED_MIN_SIGNALS = 1000
RECOMMENDED_MIN_WIN_RATE = 0.23
RECOMMENDED_MIN_PLACE_RATE = 0.50


def to_float(value: object) -> float:
    try:
        number = float(value)
    except Exception:
        return math.nan
    return number if math.isfinite(number) else math.nan


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator in {0, 0.0} or pd.isna(denominator):
        return math.nan
    return float(numerator) / float(denominator)


def bool_label(value: bool) -> str:
    return "YES" if bool(value) else "NO"


def build_rule_id(rank_max: int, score_min: int, exclude_pace_ignore: bool, exclude_gov_unknown: bool) -> str:
    return (
        f"EXECUTE_ONLY|RANK_LE_{rank_max}|SCORE_GE_{score_min}"
        f"|EX_PACE_IGNORE_{bool_label(exclude_pace_ignore)}"
        f"|EX_GOV_FSU_{bool_label(exclude_gov_unknown)}"
        "|EX_RANK_4_5_YES"
    )


def build_rule_reason(rank_max: int, score_min: int, exclude_pace_ignore: bool, exclude_gov_unknown: bool) -> str:
    parts = [
        f"keep EXECUTE source rows with rank <= {rank_max}",
        f"score >= {score_min}",
        "rank bucket 4_5 excluded via rank cap",
    ]
    if exclude_pace_ignore:
        parts.append("exclude pace_trust IGNORE")
    if exclude_gov_unknown:
        parts.append("exclude FIRST_STARTER_OR_UNKNOWN governance")
    return " | ".join(parts)


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT}")

    df = pd.read_csv(INPUT, low_memory=False)
    df["runner_rank_signal_v1"] = pd.to_numeric(df["runner_rank_signal_v1"], errors="coerce")
    df["runner_score_signal_v1"] = pd.to_numeric(df["runner_score_signal_v1"], errors="coerce")
    df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
    df["won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0).astype(int)
    df["placed"] = pd.to_numeric(df["placed"], errors="coerce").fillna(0).astype(int)
    df["pace_trust_band_v1"] = df["pace_trust_band_v1"].fillna("IGNORE").astype(str).str.upper().str.strip()
    df["governance_band_v1"] = df["governance_band_v1"].fillna("UNKNOWN").astype(str).str.strip()
    df["rank_bucket_v1"] = df["rank_bucket_v1"].fillna("UNKNOWN")
    df["score_band_v1"] = df["score_band_v1"].fillna("UNKNOWN")

    total_rows = int(len(df))
    total_winners = int(df["won"].sum())
    source_df = df[df["action"].astype(str).str.upper() == ACTION_SOURCE].copy()
    source_rows = int(len(source_df))
    source_winners = int(source_df["won"].sum())

    sweep_rows: list[dict[str, object]] = []

    for rank_max in RANK_MAX_VALUES:
        for score_min in SCORE_MIN_VALUES:
            for exclude_pace_ignore in EXCLUDE_PACE_IGNORE_VALUES:
                for exclude_gov_unknown in EXCLUDE_GOV_UNKNOWN_VALUES:
                    subset = source_df.copy()
                    subset = subset[subset["runner_rank_signal_v1"].le(rank_max)]
                    subset = subset[subset["runner_score_signal_v1"].ge(score_min)]

                    if exclude_pace_ignore:
                        subset = subset[subset["pace_trust_band_v1"] != "IGNORE"]
                    if exclude_gov_unknown:
                        subset = subset[subset["governance_band_v1"] != "FIRST_STARTER_OR_UNKNOWN"]

                    signals = int(len(subset))
                    wins = int(subset["won"].sum())
                    places = int(subset["placed"].sum())
                    win_rate = safe_rate(wins, signals)
                    place_rate = safe_rate(places, signals)

                    sweep_rows.append(
                        {
                            "rule_id_v1": build_rule_id(rank_max, score_min, exclude_pace_ignore, exclude_gov_unknown),
                            "action_source_v1": ACTION_SOURCE,
                            "rank_max_v1": rank_max,
                            "score_min_v1": score_min,
                            "exclude_pace_trust_ignore_v1": bool_label(exclude_pace_ignore),
                            "exclude_governance_first_starter_unknown_v1": bool_label(exclude_gov_unknown),
                            "exclude_rank_bucket_4_5_v1": "YES",
                            "signals": signals,
                            "sample_size": signals,
                            "signal_rate": safe_rate(signals, source_rows),
                            "replay_signal_rate": safe_rate(signals, total_rows),
                            "wins": wins,
                            "places": places,
                            "win_rate": win_rate,
                            "place_rate": place_rate,
                            "avg_finish": float(subset["finish_position"].mean()) if signals else math.nan,
                            "avg_rank": float(subset["runner_rank_signal_v1"].mean()) if signals else math.nan,
                            "avg_score": float(subset["runner_score_signal_v1"].mean()) if signals else math.nan,
                            "winner_capture": safe_rate(wins, total_winners),
                            "source_winner_capture": safe_rate(wins, source_winners),
                            "meets_min_sample_v1": int(signals >= MIN_SAMPLE),
                            "meets_target_v1": int(signals >= MIN_SAMPLE and not pd.isna(win_rate) and win_rate >= TARGET_WIN_RATE),
                            "recommended_eligible_v1": int(
                                signals >= RECOMMENDED_MIN_SIGNALS
                                and not pd.isna(win_rate)
                                and win_rate >= RECOMMENDED_MIN_WIN_RATE
                                and not pd.isna(place_rate)
                                and place_rate >= RECOMMENDED_MIN_PLACE_RATE
                            ),
                            "complexity_points_v1": int(exclude_pace_ignore) + int(exclude_gov_unknown),
                            "rule_reason_v1": build_rule_reason(rank_max, score_min, exclude_pace_ignore, exclude_gov_unknown),
                        }
                    )

    sweep_df = pd.DataFrame(sweep_rows)
    sweep_df = sweep_df.sort_values(
        ["win_rate", "signals", "place_rate", "complexity_points_v1", "rank_max_v1", "score_min_v1"],
        ascending=[False, False, False, True, True, True],
    ).reset_index(drop=True)
    sweep_df.to_csv(SWEEP_OUT, index=False)

    qualifying_df = sweep_df[(sweep_df["signals"] >= MIN_SAMPLE) & (sweep_df["win_rate"] >= TARGET_WIN_RATE)].copy()
    recommended_pool_df = sweep_df[
        (sweep_df["signals"] >= RECOMMENDED_MIN_SIGNALS)
        & (sweep_df["win_rate"] >= RECOMMENDED_MIN_WIN_RATE)
        & (sweep_df["place_rate"] >= RECOMMENDED_MIN_PLACE_RATE)
    ].copy()

    recommended_df = recommended_pool_df.sort_values(
        ["win_rate", "signals", "place_rate", "complexity_points_v1", "rank_max_v1", "score_min_v1"],
        ascending=[False, False, False, True, True, True],
    ).head(5).copy()
    if not recommended_df.empty:
        recommended_df.insert(0, "recommendation_rank_v1", range(1, len(recommended_df) + 1))
    else:
        recommended_df.insert(0, "recommendation_rank_v1", pd.Series(dtype="int64"))
    recommended_df.to_csv(RECOMMENDED_OUT, index=False)

    best_rule = sweep_df.iloc[0] if not sweep_df.empty else None
    best_qualifier = qualifying_df.iloc[0] if not qualifying_df.empty else None
    best_recommended = recommended_df.iloc[0] if not recommended_df.empty else None

    summary_rows = [
        {"metric": "input_rows", "value": total_rows},
        {"metric": "input_winners", "value": total_winners},
        {"metric": "source_action", "value": ACTION_SOURCE},
        {"metric": "source_rows", "value": source_rows},
        {"metric": "source_wins", "value": source_winners},
        {"metric": "sweep_combinations", "value": int(len(sweep_df))},
        {"metric": "min_sample", "value": MIN_SAMPLE},
        {"metric": "target_win_rate", "value": TARGET_WIN_RATE},
        {"metric": "target_signal_threshold", "value": MIN_SAMPLE},
        {"metric": "qualifying_rule_count", "value": int(len(qualifying_df))},
        {"metric": "recommended_pool_count", "value": int(len(recommended_pool_df))},
        {"metric": "recommended_rule_count", "value": int(len(recommended_df))},
        {"metric": "best_rule_id", "value": best_rule["rule_id_v1"] if best_rule is not None else ""},
        {"metric": "best_rule_win_rate", "value": float(best_rule["win_rate"]) if best_rule is not None else math.nan},
        {"metric": "best_rule_signals", "value": int(best_rule["signals"]) if best_rule is not None else math.nan},
        {"metric": "best_qualifying_rule_id", "value": best_qualifier["rule_id_v1"] if best_qualifier is not None else ""},
        {"metric": "best_qualifying_rule_win_rate", "value": float(best_qualifier["win_rate"]) if best_qualifier is not None else math.nan},
        {"metric": "best_qualifying_rule_signals", "value": int(best_qualifier["signals"]) if best_qualifier is not None else math.nan},
        {"metric": "best_recommended_rule_id", "value": best_recommended["rule_id_v1"] if best_recommended is not None else ""},
        {"metric": "best_recommended_rule_win_rate", "value": float(best_recommended["win_rate"]) if best_recommended is not None else math.nan},
        {"metric": "best_recommended_rule_signals", "value": int(best_recommended["signals"]) if best_recommended is not None else math.nan},
    ]
    pd.DataFrame(summary_rows).to_csv(SUMMARY_OUT, index=False)

    print("[EDGEIQ_SIGNAL_FILTER_V2_REPLAY_SWEEP] COMPLETE")
    print(f"source_rows={source_rows}")
    print(f"source_wins={source_winners}")
    print(f"sweep_combinations={len(sweep_df)}")
    print(f"qualifying_rule_count={len(qualifying_df)}")
    print(f"recommended_pool_count={len(recommended_pool_df)}")
    print(f"recommended_rule_count={len(recommended_df)}")
    if best_rule is not None:
        print(f"best_rule_id={best_rule['rule_id_v1']}")
        print(f"best_rule_win_rate={float(best_rule['win_rate']):.6f}")
        print(f"best_rule_signals={int(best_rule['signals'])}")
    if best_qualifier is not None:
        print(f"best_qualifying_rule_id={best_qualifier['rule_id_v1']}")
        print(f"best_qualifying_rule_win_rate={float(best_qualifier['win_rate']):.6f}")
        print(f"best_qualifying_rule_signals={int(best_qualifier['signals'])}")
    print(f"sweep_out={SWEEP_OUT}")
    print(f"summary_out={SUMMARY_OUT}")
    print(f"recommended_out={RECOMMENDED_OUT}")


if __name__ == "__main__":
    main()
