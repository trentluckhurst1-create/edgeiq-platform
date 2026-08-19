from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_results_master.csv"

COLUMNS = [
    "race_id",
    "race_date",
    "track",
    "race_no",
    "horse",
    "market_type",
    "bookmaker",
    "rated_price",
    "market_price",
    "closing_price",
    "overlay_pct",
    "confidence",
    "regime",
    "volatility",
    "execution_state",
    "final_execution_state",
    "original_execution_state",
    "original_stake",
    "suppression_risk_grade",
    "suppression_recommendation",
    "suppression_intelligence_reason",
    "suppression_matched_segments",
    "learned_suppression_applied",
    "suppression_reason",
    "stake",
    "result",
    "profit_loss",
    "clv_pct",
    "execution_timestamp",
    "settlement_timestamp",
    "source_signal_file",
    "source_result_file",
]

SIGNAL_FILES = [
    "paper_bets_settled.csv",
    "paper_bets.csv",
    "edgeiq_live_bets.csv",
    "edgeiq_execution_feed_v1_clv.csv",
    "edgeiq_execution_feed_v1.csv",
    "edgeiq_execution_board_live.csv",
    "edgeiq_execution_board_terminal.csv",
    "edgeiq_calibrated_execution_board.csv",
]

RESULT_FILES = [
    "edgeiq_result_reconciliation.csv",
    "race_results.csv",
    "official_prices.csv",
    "results_history_clean.csv",
    "master_result_events.csv",
]

CLOSING_PRICE_FILES = [
    "official_prices.csv",
    "edgeiq_execution_feed_v1_clv.csv",
    "edgeiq_market_orchestrator_runner_prices_v1.csv",
    "edgeiq_market_memory_v1.csv",
    "market_regime_board.csv",
    "market_movement_board.csv",
    "edgeiq_market_tape.csv",
    "sportsbet_live_market_v1.csv",
    "race_results.csv",
    "results_history_clean.csv",
    "master_result_events.csv",
]

BOOKMAKER_PREFIXES = [
    "SPORTSBET ",
    "SPORTSBET-",
    "BET365 ",
    "BET365-",
    "LADBROKES ",
    "LADBROKES-",
    "TAB ",
    "TAB-",
]


def log(message: str) -> None:
    print(f"[edgeiq_results_master] {message}")


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        log(f"missing: {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
        log(f"read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        log(f"warning: failed to read {path.name}: {exc}")
        return pd.DataFrame()


def first(row: pd.Series, names: list[str], default: str = "") -> str:
    for name in names:
        if name in row.index:
            value = str(row.get(name, "")).strip()
            if value and value.lower() not in {"nan", "none", "null"}:
                return value
    return default


def num(value: object) -> float | None:
    text = str(value or "").replace("$", "").replace("%", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def norm_text(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def norm_track(value: object) -> str:
    text = " ".join(str(value or "").upper().replace("-", " ").split())
    for prefix in BOOKMAKER_PREFIXES:
        clean_prefix = prefix.replace("-", " ")
        if text.startswith(clean_prefix):
            text = text[len(clean_prefix) :]
            break
    return " ".join(text.split())


def race_no_text(value: object) -> str:
    raw = str(value or "").strip()
    if raw.endswith(".0"):
        raw = raw[:-2]
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits or raw


def race_id(race_date: str, track: str, race_no: str) -> str:
    return f"{race_date}|{norm_track(track)}|{race_no_text(race_no)}"


def key(race_date: str, track: str, race_no: str, horse: str) -> str:
    return f"{race_id(race_date, track, race_no)}|{norm_text(horse)}"


def result_from_finish(value: object, status: str = "") -> str:
    status_u = str(status or "").upper()
    if any(token in status_u for token in ["VOID", "SCR", "ABANDON"]):
        return "VOID"
    if "PENDING" in status_u:
        return "PENDING"
    finish = num(value)
    if finish is None:
        return "PENDING"
    if finish == 1:
        return "WON"
    if finish > 1:
        return "LOST"
    return "PENDING"


def canonical_result(value: object, finish: object = "", status: object = "") -> str:
    raw = str(value or "").upper()
    if "WON" in raw or raw == "WIN":
        return "WON"
    if "LOST" in raw or raw == "LOSS":
        return "LOST"
    if "VOID" in raw or "SCR" in raw or "ABANDON" in raw:
        return "VOID"
    if "PENDING" in raw or raw == "OPEN":
        return "PENDING"
    return result_from_finish(finish, str(status or ""))


def profit_loss(result: str, stake: float | None, market_price: float | None, existing: object = "") -> str:
    existing_num = num(existing)
    if existing_num is not None:
        return f"{existing_num:.4f}"
    if stake is None:
        return ""
    if result == "WON" and market_price is not None:
        return f"{stake * (market_price - 1):.4f}"
    if result == "LOST":
        return f"{-stake:.4f}"
    if result == "VOID":
        return "0.0000"
    return ""


def clv_pct(entry_price: float | None, closing_price: float | None, existing: object = "") -> str:
    existing_num = num(existing)
    if existing_num is not None:
        return f"{existing_num:.4f}"
    if entry_price is None or closing_price is None or closing_price <= 0:
        return ""
    return f"{((entry_price - closing_price) / closing_price) * 100:.4f}"


def price_from_row(row: pd.Series, names: list[str]) -> float | None:
    for name in names:
        value = num(first(row, [name]))
        if value is not None and value > 0:
            return value
    return None


def source_name(filename: str, label: str) -> str:
    return f"{filename}:{label}"


def add_closing_candidate(
    lookup: dict[str, tuple[float, str]],
    k: str,
    price: float | None,
    source: str,
) -> None:
    if not k or price is None or price <= 0:
        return
    if k not in lookup:
        lookup[k] = (price, source)


def build_closing_lookup() -> tuple[dict[str, tuple[float, str]], dict[str, tuple[float, str]]]:
    lookup: dict[str, tuple[float, str]] = {}
    horse_only_sources: dict[str, list[tuple[float, str]]] = {}

    for filename in CLOSING_PRICE_FILES:
        df = read_csv(DATA / filename)
        if df.empty:
            continue

        for _, row in df.iterrows():
            race_date = first(row, ["race_date", "date", "run_date"])
            track = first(row, ["track", "meeting"])
            race_no = first(row, ["race_no", "race", "race_number"])
            horse = first(row, ["horse", "runner", "selection", "horse_name"])
            price = price_from_row(
                row,
                [
                    "official_price",
                    "closing_price",
                    "close_price",
                    "result_sp",
                    "sp_clean",
                    "sp",
                    "latest_market_price",
                    "latest_price",
                    "consensus_price",
                    "current_price",
                    "best_price",
                    "avg_price",
                    "sportsbet_price",
                ],
            )

            if not horse or price is None:
                continue

            if race_date and track and race_no:
                add_closing_candidate(
                    lookup,
                    key(race_date, track, race_no, horse),
                    price,
                    source_name(filename, "exact"),
                )
            elif track and race_no:
                add_closing_candidate(
                    lookup,
                    f"{norm_track(track)}|{race_no_text(race_no)}|{norm_text(horse)}",
                    price,
                    source_name(filename, "track_race_horse"),
                )
            else:
                horse_key = norm_text(horse)
                if horse_key:
                    horse_only_sources.setdefault(horse_key, []).append(
                        (price, source_name(filename, "unique_horse"))
                    )

    unique_horse_lookup = {
        horse: values[-1]
        for horse, values in horse_only_sources.items()
        if len({source for _, source in values}) == 1 or len(values) == 1
    }

    log(f"closing lookup exact/track keys: {len(lookup)}")
    log(f"closing lookup unique-horse fallback keys: {len(unique_horse_lookup)}")
    return lookup, unique_horse_lookup


def find_closing_price(
    row: pd.Series,
    result_row: pd.Series,
    closing_lookup: dict[str, tuple[float, str]],
    horse_lookup: dict[str, tuple[float, str]],
    race_date: str,
    track: str,
    race_no: str,
    horse: str,
) -> tuple[float | None, str]:
    row_price = price_from_row(row, ["closing_price", "result_sp"])
    if row_price is not None:
        return row_price, "source_signal_file:closing_price"

    exact_key = key(race_date, track, race_no, horse)
    if exact_key in closing_lookup:
        return closing_lookup[exact_key]

    loose_key = f"{norm_track(track)}|{race_no_text(race_no)}|{norm_text(horse)}"
    if loose_key in closing_lookup:
        return closing_lookup[loose_key]

    result_price = price_from_row(result_row, ["official_price", "closing_price", "result_sp", "sp_clean", "sp"])
    if result_price is not None:
        return result_price, "source_result_file:sp"

    horse_key = norm_text(horse)
    if horse_key in horse_lookup:
        return horse_lookup[horse_key]

    return None, ""


def execution_allows_default_stake(state: str) -> bool:
    state_u = state.upper()
    return "PRIORITY_EXECUTE" in state_u or state_u == "EXECUTE"


def build_result_lookup() -> tuple[dict[str, pd.Series], dict[str, str]]:
    lookup: dict[str, pd.Series] = {}
    source_lookup: dict[str, str] = {}
    for filename in RESULT_FILES:
        df = read_csv(DATA / filename)
        if df.empty:
            continue
        for _, row in df.iterrows():
            race_date = first(row, ["race_date", "date", "run_date"])
            track = first(row, ["track", "meeting"])
            race_no = first(row, ["race_no", "race", "race_number"])
            horse = first(row, ["horse", "runner", "selection", "horse_name"])
            if not race_date or not track or not race_no or not horse:
                continue
            k = key(race_date, track, race_no, horse)
            if k not in lookup:
                lookup[k] = row
                source_lookup[k] = filename
    return lookup, source_lookup


def signal_rows() -> list[dict[str, str]]:
    result_lookup, result_sources = build_result_lookup()
    closing_lookup, horse_closing_lookup = build_closing_lookup()
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    default_stake_count = 0

    for filename in SIGNAL_FILES:
        df = read_csv(DATA / filename)
        if df.empty:
            continue
        for _, row in df.iterrows():
            race_date = first(row, ["race_date", "date"])
            track = first(row, ["track", "meeting"])
            race_no = first(row, ["race_no", "race", "race_number"])
            horse = first(row, ["horse", "runner", "selection"])
            if not race_date or not track or not race_no or not horse:
                continue

            k = key(race_date, track, race_no, horse)
            if k in seen:
                continue
            seen.add(k)

            result_row = result_lookup.get(k, pd.Series(dtype=str))
            result_file = result_sources.get(k, "")

            rated = num(first(row, ["rated_price", "elite_rated_price", "model_price"]))
            market = num(first(row, ["market_price", "market_price_clean", "entry_price", "sportsbet_price", "current_price"]))
            execution_state = first(row, ["execution_state", "execution_action", "action_grade", "execution_instruction", "final_execution_decision"])
            final_execution_state = first(row, ["final_execution_state", "execution_action", "execution_state", "action_grade", "execution_instruction", "final_execution_decision"])
            original_execution_state = first(row, ["original_execution_state"])
            original_stake = first(row, ["original_stake"])
            suppression_risk_grade = first(row, ["suppression_risk_grade"])
            suppression_recommendation = first(row, ["suppression_recommendation"])
            suppression_intelligence_reason = first(row, ["suppression_intelligence_reason"])
            suppression_matched_segments = first(row, ["suppression_matched_segments"])
            learned_suppression_applied = first(row, ["learned_suppression_applied"])
            close, close_source = find_closing_price(
                row,
                result_row,
                closing_lookup,
                horse_closing_lookup,
                race_date,
                track,
                race_no,
                horse,
            )
            stake = num(
                first(
                    row,
                    [
                        "stake",
                        "unit",
                        "units",
                        "stake_units",
                        "kelly_stake",
                        "recommended_stake",
                        "adaptive_stake_units",
                    ],
                )
            )
            if stake is None and execution_allows_default_stake(execution_state):
                stake = 1.0
                default_stake_count += 1
            finish = first(row, ["finish_pos", "finish_position"]) or first(result_row, ["finish_pos", "finish_position", "position"])
            status = first(row, ["status", "result_status", "settlement_status"]) or first(result_row, ["status", "result_status", "settlement_status"])
            signal_result = canonical_result(first(row, ["result", "settled_result_state", "status"]), finish, status)
            matched_result = canonical_result(
                first(result_row, ["result", "settled_result_state", "status", "settlement_status"]),
                finish,
                status,
            )
            result = matched_result if signal_result == "PENDING" and matched_result != "PENDING" else signal_result
            existing_profit = first(row, ["profit_loss", "profit_units", "settled_profit_units"]) or first(result_row, ["profit_loss", "profit_units", "settled_profit_units"])
            existing_clv = first(row, ["clv_pct", "settled_clv_pct", "clv_proxy"]) or first(result_row, ["clv_pct", "settled_clv_pct", "clv_proxy"])

            records.append(
                {
                    "race_id": race_id(race_date, track, race_no),
                    "race_date": race_date,
                    "track": norm_track(track),
                    "race_no": race_no_text(race_no),
                    "horse": horse,
                    "market_type": first(row, ["market_type", "market_name"], "WIN"),
                    "bookmaker": first(row, ["bookmaker", "book"], "Sportsbet"),
                    "rated_price": "" if rated is None else f"{rated:.4f}",
                    "market_price": "" if market is None else f"{market:.4f}",
                    "closing_price": "" if close is None else f"{close:.4f}",
                    "overlay_pct": first(row, ["overlay_pct", "edge_pct", "calibrated_edge_pct"]),
                    "confidence": first(row, ["confidence", "confidence_band", "confidence_tier", "confidence_band_v1"]),
                    "regime": first(row, ["regime", "market_regime", "market_signal", "movement_signal"]),
                    "volatility": first(row, ["volatility", "volatility_score", "move_pct", "price_delta_pct"]),
                    "execution_state": execution_state,
                    "final_execution_state": final_execution_state or execution_state,
                    "original_execution_state": original_execution_state,
                    "original_stake": original_stake,
                    "suppression_risk_grade": suppression_risk_grade,
                    "suppression_recommendation": suppression_recommendation,
                    "suppression_intelligence_reason": suppression_intelligence_reason,
                    "suppression_matched_segments": suppression_matched_segments,
                    "learned_suppression_applied": learned_suppression_applied,
                    "suppression_reason": first(row, ["suppression_reason", "risk_flags", "fake_overlay_risk"]),
                    "stake": "" if stake is None else f"{stake:.4f}",
                    "result": result,
                    "profit_loss": profit_loss(result, stake, market, existing_profit),
                    "clv_pct": clv_pct(market, close, existing_clv),
                    "execution_timestamp": first(row, ["execution_timestamp", "created_at", "timestamp"]),
                    "settlement_timestamp": first(row, ["settlement_timestamp", "settled_at"]) or first(result_row, ["settlement_timestamp", "reconciliation_timestamp", "scraped_at"]),
                    "source_signal_file": filename,
                    "source_result_file": ";".join(part for part in [result_file, close_source] if part),
                }
            )

    log(f"default paper stakes assigned: {default_stake_count}")
    return records


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    records = signal_rows()
    output = pd.DataFrame(records, columns=COLUMNS)
    if output.empty:
        log("no usable signal rows found; writing structured empty CSV")
        output = pd.DataFrame(columns=COLUMNS)
    else:
        output = output.drop_duplicates(subset=["race_id", "horse", "market_type", "bookmaker"], keep="first")
    output.to_csv(OUT, index=False, encoding="utf-8")
    log(f"wrote {OUT.relative_to(ROOT)}: {len(output)} rows")
    log(f"results: {output['result'].value_counts(dropna=False).to_dict() if not output.empty else {}}")
    if not output.empty:
        log(f"stake coverage: {int(output['stake'].astype(str).str.strip().ne('').sum())}/{len(output)}")
        log(f"closing price coverage: {int(output['closing_price'].astype(str).str.strip().ne('').sum())}/{len(output)}")
        log(f"CLV coverage: {int(output['clv_pct'].astype(str).str.strip().ne('').sum())}/{len(output)}")
        log(f"profit/loss coverage: {int(output['profit_loss'].astype(str).str.strip().ne('').sum())}/{len(output)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
