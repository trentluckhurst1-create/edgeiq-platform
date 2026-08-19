from __future__ import annotations

from datetime import datetime
from pathlib import Path
import math
import shutil
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"
INPUT_PATH = DATA_DIR / "edgeiq_live_runner_board_v1.csv"
BACKUP_PATH = DATA_DIR / "edgeiq_live_runner_board_v1_BEFORE_PROB_NORMALISE_V1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_live_runner_board_probability_normalisation_v1_summary.csv"
DETAIL_PATH = DATA_DIR / "edgeiq_live_runner_board_probability_normalisation_v1_detail.csv"


def text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def as_float(value: object) -> float | None:
    raw = text(value).replace("$", "").replace("%", "").replace(",", "")
    if not raw:
        return None
    try:
        number = float(raw)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def fmt_probability_pct(value: float | None) -> str:
    if value is None or math.isnan(value) or math.isinf(value):
        return ""
    return f"{value:.2f}"


def fmt_probability_decimal(value: float | None) -> str:
    if value is None or math.isnan(value) or math.isinf(value):
        return ""
    return f"{value:.6f}"


def fmt_price(value: float | None) -> str:
    if value is None or math.isnan(value) or math.isinf(value) or value <= 0:
        return ""
    return f"{value:.2f}"


def fmt_edge(value: float | None) -> str:
    if value is None or math.isnan(value) or math.isinf(value):
        return ""
    return f"{value:.1f}"


def is_scratched(row: pd.Series) -> bool:
    status_text = " ".join(
        [
            text(row.get("runner_status")),
            text(row.get("scratch_status")),
            text(row.get("tab_fixed_betting_status")),
            text(row.get("is_scratched")),
            text(row.get("display_decision")),
            text(row.get("execution_action")),
        ]
    ).upper()
    if "SCRATCH" in status_text:
        return True
    if text(row.get("is_scratched")).upper() in {"1", "TRUE", "YES", "Y"}:
        return True
    return False


def get_live_price(row: pd.Series) -> float | None:
    for column in ["display_live_price", "live_price", "tab_fixed_win"]:
        value = as_float(row.get(column))
        if value is not None and value > 0:
            return value
    return None


def decision_from_values(row: pd.Series) -> str:
    if is_scratched(row):
        return "SCRATCHED"

    live = get_live_price(row)
    fair = as_float(row.get("display_fair_price") or row.get("fair_price"))
    edge = as_float(row.get("display_edge_pct") or row.get("edge_pct"))

    if live is None or live <= 0:
        return "NO MARKET"
    if fair is None or fair <= 0:
        return "NO MODEL"
    if edge is None:
        return "NO EDGE"
    if edge >= 18:
        return "WATCH"
    if edge >= 10:
        return "LEAN"
    if edge > 0:
        return "PASS"
    return "UNDERLAY"


def ensure_column(frame: pd.DataFrame, column: str) -> None:
    if column not in frame.columns:
        frame[column] = ""


def main() -> int:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    board = pd.read_csv(INPUT_PATH, dtype=str, keep_default_na=False)
    if board.empty:
        raise ValueError(f"Input file is empty: {INPUT_PATH}")

    for required in ["race_date", "track", "race_no"]:
        if required not in board.columns:
            raise KeyError(f"Missing required column: {required}")

    shutil.copyfile(INPUT_PATH, BACKUP_PATH)

    for column in [
        "probability_normalised_v1",
        "probability_raw_sum_before_v1",
        "probability_sum_after_v1",
        "probability_normalisation_factor_v1",
        "probability_normalisation_status_v1",
    ]:
        ensure_column(board, column)

    board["__row_order__"] = range(len(board))
    board["__is_scratched__"] = board.apply(is_scratched, axis=1)

    built_at = datetime.now().astimezone().isoformat(timespec="seconds")
    detail_rows: list[dict[str, object]] = []

    races_total = 0
    races_normalised = 0
    races_fail_no_raw_prob = 0
    active_rows_normalised = 0
    scratched_rows_excluded = int(board["__is_scratched__"].sum())
    raw_sums: list[float] = []

    grouped = board.groupby(["race_date", "track", "race_no"], sort=False, dropna=False)
    for (race_date, track, race_no), group in grouped:
        races_total += 1
        race_index = group.index.tolist()

        active_index = [idx for idx in race_index if not bool(board.at[idx, "__is_scratched__"])]
        scratched_index = [idx for idx in race_index if bool(board.at[idx, "__is_scratched__"])]

        raw_probability_map: dict[int, float | None] = {}
        raw_source_map: dict[int, str] = {}
        positive_raw_count = 0
        rows_from_win_pct = 0
        rows_from_fair_price = 0

        for idx in active_index:
            win_pct = as_float(board.at[idx, "win_pct"]) if "win_pct" in board.columns else None
            fair_price = as_float(board.at[idx, "fair_price"]) if "fair_price" in board.columns else None

            raw_probability = None
            raw_source = ""

            if win_pct is not None and win_pct > 0:
                raw_probability = win_pct
                raw_source = "WIN_PCT"
                rows_from_win_pct += 1
            elif fair_price is not None and fair_price > 0:
                raw_probability = 100.0 / fair_price
                raw_source = "FAIR_PRICE"
                rows_from_fair_price += 1

            raw_probability_map[idx] = raw_probability
            raw_source_map[idx] = raw_source
            if raw_probability is not None and raw_probability > 0:
                positive_raw_count += 1

        raw_sum_before = float(
            sum(value for value in raw_probability_map.values() if value is not None and value > 0)
        )
        raw_sums.append(raw_sum_before)

        top_horse_before = ""
        top_raw_before = None
        if positive_raw_count > 0:
            top_idx = max(
                (idx for idx in active_index if raw_probability_map.get(idx) is not None and raw_probability_map[idx] > 0),
                key=lambda idx: raw_probability_map[idx],
            )
            top_horse_before = text(board.at[top_idx, "horse"]) if "horse" in board.columns else ""
            top_raw_before = raw_probability_map[top_idx]

        if raw_sum_before <= 0:
            status = "FAIL_NO_RAW_PROB"
            races_fail_no_raw_prob += 1

            for idx in active_index:
                board.at[idx, "probability_normalised_v1"] = "NO"
                board.at[idx, "probability_raw_sum_before_v1"] = fmt_probability_pct(raw_sum_before)
                board.at[idx, "probability_sum_after_v1"] = ""
                board.at[idx, "probability_normalisation_factor_v1"] = ""
                board.at[idx, "probability_normalisation_status_v1"] = status

            for idx in scratched_index:
                board.at[idx, "probability_normalised_v1"] = "NO"
                board.at[idx, "probability_raw_sum_before_v1"] = fmt_probability_pct(raw_sum_before)
                board.at[idx, "probability_sum_after_v1"] = ""
                board.at[idx, "probability_normalisation_factor_v1"] = ""
                board.at[idx, "probability_normalisation_status_v1"] = "SCRATCHED_EXCLUDED"

            detail_rows.append(
                {
                    "race_date": race_date,
                    "track": track,
                    "race_no": race_no,
                    "rows_total": len(race_index),
                    "active_runner_count": len(active_index),
                    "scratched_rows_excluded": len(scratched_index),
                    "rows_from_win_pct": rows_from_win_pct,
                    "rows_from_fair_price": rows_from_fair_price,
                    "rows_with_positive_raw_probability": positive_raw_count,
                    "probability_raw_sum_before_v1": round(raw_sum_before, 6),
                    "probability_sum_after_v1": "",
                    "probability_normalisation_factor_v1": "",
                    "top_horse_before_v1": top_horse_before,
                    "top_raw_probability_before_v1": round(top_raw_before, 6) if top_raw_before is not None else "",
                    "top_horse_after_v1": "",
                    "top_probability_after_v1": "",
                    "status": status,
                    "built_at": built_at,
                }
            )
            continue

        normalisation_factor = 100.0 / raw_sum_before
        normalised_probabilities: list[tuple[int, float]] = []

        for idx in active_index:
            raw_probability = raw_probability_map.get(idx)
            if raw_probability is None or raw_probability <= 0:
                board.at[idx, "probability_normalised_v1"] = "NO"
                board.at[idx, "probability_raw_sum_before_v1"] = fmt_probability_pct(raw_sum_before)
                board.at[idx, "probability_sum_after_v1"] = ""
                board.at[idx, "probability_normalisation_factor_v1"] = fmt_probability_decimal(normalisation_factor)
                board.at[idx, "probability_normalisation_status_v1"] = "MISSING_RAW_PROBABILITY"
                continue

            normalised_probability = raw_probability * normalisation_factor
            normalised_fair_price = 100.0 / normalised_probability if normalised_probability > 0 else None
            live_price = get_live_price(board.loc[idx])
            edge_pct = None
            if live_price is not None and normalised_fair_price is not None and normalised_fair_price > 0:
                edge_pct = ((live_price / normalised_fair_price) - 1.0) * 100.0

            board.at[idx, "win_pct"] = fmt_probability_pct(normalised_probability)
            board.at[idx, "fair_price"] = fmt_price(normalised_fair_price)
            if "rated_price" in board.columns:
                board.at[idx, "rated_price"] = fmt_price(normalised_fair_price)
            if "ui_fair_price" in board.columns:
                board.at[idx, "ui_fair_price"] = fmt_price(normalised_fair_price)
            if "display_fair_price" in board.columns:
                board.at[idx, "display_fair_price"] = fmt_price(normalised_fair_price)
            if "V6_1_RESEARCH_probability" in board.columns:
                board.at[idx, "V6_1_RESEARCH_probability"] = fmt_probability_decimal(normalised_probability / 100.0)
            if "V6_1_RESEARCH_fair_price" in board.columns:
                board.at[idx, "V6_1_RESEARCH_fair_price"] = fmt_price(normalised_fair_price)
            if "edge_pct" in board.columns:
                board.at[idx, "edge_pct"] = fmt_edge(edge_pct)
            if "ui_edge_pct" in board.columns:
                board.at[idx, "ui_edge_pct"] = fmt_edge(edge_pct)
            if "display_edge_pct" in board.columns:
                board.at[idx, "display_edge_pct"] = fmt_edge(edge_pct)

            board.at[idx, "probability_normalised_v1"] = "YES"
            board.at[idx, "probability_raw_sum_before_v1"] = fmt_probability_pct(raw_sum_before)
            board.at[idx, "probability_sum_after_v1"] = fmt_probability_pct(100.0)
            board.at[idx, "probability_normalisation_factor_v1"] = fmt_probability_decimal(normalisation_factor)
            board.at[idx, "probability_normalisation_status_v1"] = "PASS"

            normalised_probabilities.append((idx, normalised_probability))

        for idx in scratched_index:
            board.at[idx, "probability_normalised_v1"] = "NO"
            board.at[idx, "probability_raw_sum_before_v1"] = fmt_probability_pct(raw_sum_before)
            board.at[idx, "probability_sum_after_v1"] = fmt_probability_pct(100.0)
            board.at[idx, "probability_normalisation_factor_v1"] = fmt_probability_decimal(normalisation_factor)
            board.at[idx, "probability_normalisation_status_v1"] = "SCRATCHED_EXCLUDED"

        if normalised_probabilities:
            ranked = sorted(
                normalised_probabilities,
                key=lambda item: (-item[1], int(item[0])),
            )
            for rank, (idx, _) in enumerate(ranked, start=1):
                if "V6_1_RESEARCH_price_rank" in board.columns:
                    board.at[idx, "V6_1_RESEARCH_price_rank"] = str(rank)

            for idx, _ in normalised_probabilities:
                if "display_decision" in board.columns:
                    board.at[idx, "display_decision"] = decision_from_values(board.loc[idx])
                if "execution_action" in board.columns:
                    board.at[idx, "execution_action"] = decision_from_values(board.loc[idx])
                if "execution_action_final" in board.columns:
                    board.at[idx, "execution_action_final"] = decision_from_values(board.loc[idx])

            top_idx_after = ranked[0][0]
            top_horse_after = text(board.at[top_idx_after, "horse"]) if "horse" in board.columns else ""
            top_probability_after = ranked[0][1]
        else:
            top_horse_after = ""
            top_probability_after = None

        races_normalised += 1
        active_rows_normalised += len(normalised_probabilities)

        detail_rows.append(
            {
                "race_date": race_date,
                "track": track,
                "race_no": race_no,
                "rows_total": len(race_index),
                "active_runner_count": len(active_index),
                "scratched_rows_excluded": len(scratched_index),
                "rows_from_win_pct": rows_from_win_pct,
                "rows_from_fair_price": rows_from_fair_price,
                "rows_with_positive_raw_probability": positive_raw_count,
                "probability_raw_sum_before_v1": round(raw_sum_before, 6),
                "probability_sum_after_v1": round(
                    sum(probability for _, probability in normalised_probabilities), 6
                ),
                "probability_normalisation_factor_v1": round(normalisation_factor, 8),
                "top_horse_before_v1": top_horse_before,
                "top_raw_probability_before_v1": round(top_raw_before, 6) if top_raw_before is not None else "",
                "top_horse_after_v1": top_horse_after,
                "top_probability_after_v1": round(top_probability_after, 6) if top_probability_after is not None else "",
                "status": "PASS",
                "built_at": built_at,
            }
        )

    board = board.sort_values("__row_order__").drop(columns=["__row_order__", "__is_scratched__"], errors="ignore")
    board.to_csv(INPUT_PATH, index=False, encoding="utf-8")

    detail_df = pd.DataFrame(detail_rows)
    detail_df.to_csv(DETAIL_PATH, index=False, encoding="utf-8")

    summary_row = {
        "built_at": built_at,
        "input_file": INPUT_PATH.name,
        "backup_file": BACKUP_PATH.name,
        "output_file": INPUT_PATH.name,
        "races_total": races_total,
        "races_normalised": races_normalised,
        "races_fail_no_raw_prob": races_fail_no_raw_prob,
        "rows_total": int(len(board)),
        "active_rows_normalised": active_rows_normalised,
        "scratched_rows_excluded": scratched_rows_excluded,
        "avg_probability_raw_sum_before_v1": round(sum(raw_sums) / len(raw_sums), 6) if raw_sums else "",
        "min_probability_raw_sum_before_v1": round(min(raw_sums), 6) if raw_sums else "",
        "max_probability_raw_sum_before_v1": round(max(raw_sums), 6) if raw_sums else "",
        "status": "PASS" if races_fail_no_raw_prob == 0 else "PASS_WITH_FAIL_NO_RAW_PROB_RACES",
    }
    pd.DataFrame([summary_row]).to_csv(SUMMARY_PATH, index=False, encoding="utf-8")

    print("[EDGEIQ_LIVE_RUNNER_BOARD_PROBABILITY_NORMALISATION_V1] COMPLETE")
    print(f"races_total={races_total}")
    print(f"races_normalised={races_normalised}")
    print(f"races_fail_no_raw_prob={races_fail_no_raw_prob}")
    print(f"active_rows_normalised={active_rows_normalised}")
    print(f"scratched_rows_excluded={scratched_rows_excluded}")
    print(f"wrote={INPUT_PATH}")
    print(f"backup={BACKUP_PATH}")
    print(f"summary={SUMMARY_PATH}")
    print(f"detail={DETAIL_PATH}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(f"[EDGEIQ_LIVE_RUNNER_BOARD_PROBABILITY_NORMALISATION_V1] FAILED: {exc}", file=sys.stderr)
        raise
