from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_market_source_coverage_discovery_v1.csv"
SUMMARY = DATA / "edgeiq_market_source_coverage_discovery_v1_summary.csv"
CANDIDATES = DATA / "edgeiq_market_source_coverage_discovery_v1_candidate_files.csv"
INVENTORY = DATA / "edgeiq_market_source_coverage_discovery_v1_column_inventory.csv"

INCLUDE_TERMS = [
    "price",
    "odds",
    "fixed",
    "market",
    "win",
    "sp",
    "tab",
    "sportsbet",
    "live_price",
]

EXCLUDE_TERMS = [
    "won",
    "winner",
    "win_pct",
    "wins",
    "profit",
    "roi",
    "ae",
    "expected",
    "result",
    "finish",
    "placed",
]

AUDIT_NAME_TERMS = ["audit", "replay", "diagnosis", "summary", "verdict"]
LIVE_HINT_TERMS = ["sportsbet", "live_market", "market_snapshot", "market_history", "bookmaker", "official_prices"]
RACECARD_HINT_TERMS = ["tab", "racecard", "racecards", "field", "fields", "upcoming", "pre_race"]
RESULTS_HINT_TERMS = ["results", "warehouse"]
MODEL_HINT_TERMS = ["projection", "rating", "fair", "runner_board", "board", "probability", "model", "execution"]
VICTORIA_HINT_TERMS = ["vic", "victoria"]
TRANSFORM_HINT_TERMS = [
    "velocity",
    "tape",
    "rank",
    "intelligence",
    "vulnerability",
    "hidden",
    "master_runner",
    "core_market",
    "stewards",
    "pace_advantage",
    "speed_map",
    "watchlist",
    "betting",
    "paper_bets",
    "report",
    "comments",
    "snapshot",
]
RAW_SOURCE_SELECT_TERMS = [
    "sportsbet_live_market",
    "tab_vic_racecards",
    "tab_market",
    "tab_racecards",
    "tab_single_race",
    "live_terminal_feed",
    "official_prices",
]
MODEL_COLUMN_TERMS = [
    "rated_price",
    "fair_price",
    "market_signal",
    "price_confidence_band",
    "probability",
    "overlay",
    "edge_pct",
    "calibrated_price",
    "dynamic_fair_price",
]


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm_col(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", clean_text(value).lower()).strip("_")


def parse_numeric(value: object) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    text = text.replace("$", "").replace(",", "").replace("%", "")
    text = text.replace("â€“", "").replace("–", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def discover_csv_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    paths.extend(sorted(root.glob("*.csv")))
    for child in sorted(root.iterdir()):
        if child.is_dir():
            paths.extend(sorted(child.glob("*.csv")))
    return paths


def is_price_keyword(column_name: str) -> bool:
    lowered = column_name.lower()
    return any(term in lowered for term in INCLUDE_TERMS)


def exclusion_reason(column_name: str) -> str:
    lowered = column_name.lower()
    matched = [term for term in EXCLUDE_TERMS if term in lowered]
    return ",".join(matched)


def kept_price_column(column_name: str) -> bool:
    if not is_price_keyword(column_name):
        return False
    return exclusion_reason(column_name) == ""


def bool_from_columns(columns: list[str], patterns: list[str]) -> bool:
    lowered = [norm_col(col) for col in columns]
    return any(any(pattern in col for pattern in patterns) for col in lowered)


def classify_source_type(file_name: str, kept_columns: list[str], all_columns: list[str]) -> str:
    name = file_name.lower()
    kept_lower = [col.lower() for col in kept_columns]
    all_lower = [col.lower() for col in all_columns]
    has_model_columns = any(any(term in col for term in MODEL_COLUMN_TERMS) for col in kept_lower + all_lower)
    has_explicit_bookmaker_cols = any(
        token in col
        for col in kept_lower + all_lower
        for token in ["sportsbet_price", "tab_fixed_win", "tab_tote_win", "fixed_odds", "win_odds", "market_price", "live_price", "price_win"]
    )

    if any(term in name for term in RESULTS_HINT_TERMS) and any("sp" in col for col in kept_lower):
        return "RESULTS_WITH_SP"

    if any(term in name for term in AUDIT_NAME_TERMS):
        return "AUDIT_OUTPUT"

    if any(term in name for term in MODEL_HINT_TERMS + TRANSFORM_HINT_TERMS) or ("snapshot" in name and not any(term in name for term in ["sportsbet", "tab"])) or (has_model_columns and not any(term in name for term in ["sportsbet", "tab", "racecard", "racecards", "official_prices"])):
        return "MODEL_OUTPUT"

    if any(term in name for term in LIVE_HINT_TERMS) and kept_columns:
        return "LIVE_MARKET_SOURCE"

    if any(term in name for term in RACECARD_HINT_TERMS) and kept_columns:
        if any(term in name for term in ["live", "sportsbet"]):
            return "LIVE_MARKET_SOURCE"
        return "RACECARD_WITH_MARKET"

    if kept_columns and any("tab_fixed" in col or "sportsbet" in col or "fixed_odds" in col or "market_price" in col for col in kept_lower):
        return "RACECARD_WITH_MARKET"

    if kept_columns and any("live_price" in col or "price_win" in col for col in kept_lower):
        return "LIVE_MARKET_SOURCE"

    if has_model_columns and not has_explicit_bookmaker_cols:
        return "MODEL_OUTPUT"

    if any(term in name for term in RESULTS_HINT_TERMS) or any("sp" == norm_col(col) for col in all_lower):
        return "RESULTS_WITH_SP" if kept_columns else "UNKNOWN"

    return "UNKNOWN"


def candidate_rank(file_name: str, source_type: str, rows: int, has_meeting_date: bool, has_track: bool, has_race_no: bool, has_horse: bool, has_horse_key: bool, kept_columns: list[str]) -> tuple[int, str]:
    name = file_name.lower()
    score = 0
    reasons: list[str] = []

    if has_meeting_date:
        score += 15
        reasons.append("HAS_DATE")
    if has_track:
        score += 15
        reasons.append("HAS_TRACK")
    if has_race_no:
        score += 15
        reasons.append("HAS_RACE")
    if has_horse:
        score += 15
        reasons.append("HAS_HORSE")
    if has_horse_key:
        score += 10
        reasons.append("HAS_HORSE_KEY")
    if kept_columns:
        score += 20
        reasons.append("HAS_PRICE_COLUMNS")
    if len(kept_columns) >= 2:
        score += 5
        reasons.append("MULTI_PRICE_COLUMNS")

    if any(term in name for term in VICTORIA_HINT_TERMS):
        score += 10
        reasons.append("VIC_HINT")
    if "tab" in name or "sportsbet" in name:
        score += 10
        reasons.append("BOOKMAKER_HINT")
    if any(token in name for token in ["sportsbet_live_market", "tab_vic_racecards", "tab_market", "official_prices", "live_terminal_feed"]):
        score += 15
        reasons.append("RAW_SOURCE_NAME_HINT")
    if any(term in name for term in ["live", "racecard", "racecards", "market", "current_field"]):
        score += 10
        reasons.append("PRE_RESULT_NAME_HINT")

    if source_type == "LIVE_MARKET_SOURCE":
        score += 15
        reasons.append("LIVE_SOURCE_TYPE")
    elif source_type == "RACECARD_WITH_MARKET":
        score += 12
        reasons.append("RACECARD_SOURCE_TYPE")
    elif source_type == "RESULTS_WITH_SP":
        score -= 18
        reasons.append("POST_RESULT_SP_SOURCE")
    elif source_type == "AUDIT_OUTPUT":
        score -= 30
        reasons.append("AUDIT_OUTPUT")
    elif source_type == "MODEL_OUTPUT":
        score -= 35
        reasons.append("MODEL_OUTPUT")

    if any(term in name for term in TRANSFORM_HINT_TERMS):
        score -= 20
        reasons.append("TRANSFORM_LAYER")

    if rows == 0:
        score -= 20
        reasons.append("EMPTY_FILE")

    if kept_columns and all("sp" in col.lower() and "sportsbet" not in col.lower() and "tab_fixed" not in col.lower() and "price" not in col.lower() and "odds" not in col.lower() for col in kept_columns):
        score -= 15
        reasons.append("SP_ONLY_COLUMNS")

    if any(term in name for term in AUDIT_NAME_TERMS):
        score -= 10
    if any(term in name for term in ["replay", "settled", "history"]) and source_type != "LIVE_MARKET_SOURCE":
        score -= 10

    score = max(0, min(100, score))
    return score, "; ".join(reasons)


def analyse_file(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    columns: list[str] = []
    row_count = 0
    inventory_rows: list[dict[str, object]] = []

    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = list(reader.fieldnames or [])
            matched_cols = [col for col in columns if is_price_keyword(col)]
            matched_meta = {
                col: {
                    "excluded_reason": exclusion_reason(col),
                    "non_null_rows": 0,
                    "numeric_parse_rows": 0,
                    "sum_value": 0.0,
                    "min_value": math.inf,
                    "max_value": -math.inf,
                    "sample_values": [],
                }
                for col in matched_cols
            }

            for row in reader:
                row_count += 1
                for col in matched_cols:
                    raw = clean_text(row.get(col))
                    if raw == "":
                        continue
                    meta = matched_meta[col]
                    meta["non_null_rows"] += 1
                    if raw not in meta["sample_values"] and len(meta["sample_values"]) < 5:
                        meta["sample_values"].append(raw)
                    num = parse_numeric(raw)
                    if num is None:
                        continue
                    meta["numeric_parse_rows"] += 1
                    meta["sum_value"] += num
                    meta["min_value"] = min(meta["min_value"], num)
                    meta["max_value"] = max(meta["max_value"], num)

    except Exception as exc:
        file_row = {
            "file_path": str(path.relative_to(DATA)),
            "file_name": path.name,
            "rows": 0,
            "columns_count": 0,
            "has_meeting_date": False,
            "has_track": False,
            "has_race_no": False,
            "has_horse": False,
            "has_horse_key": False,
            "has_price_like_column": False,
            "price_like_columns": "",
            "likely_source_type": "UNKNOWN",
            "candidate_rank": 0,
            "reason_v1": f"READ_ERROR:{exc}",
        }
        return file_row, inventory_rows

    kept_columns = [col for col in columns if kept_price_column(col)]
    has_meeting_date = bool_from_columns(columns, ["meeting_date", "race_date", "date"])
    has_track = bool_from_columns(columns, ["track", "meeting_name", "location", "venue"])
    has_race_no = bool_from_columns(columns, ["race_no", "race_number"])
    has_horse = bool_from_columns(columns, ["horse", "runner"])
    has_horse_key = bool_from_columns(columns, ["horse_key", "horse_canon", "runner_key"])

    source_type = classify_source_type(path.name, kept_columns, columns)
    rank, reason = candidate_rank(path.name, source_type, row_count, has_meeting_date, has_track, has_race_no, has_horse, has_horse_key, kept_columns)

    for col in [col for col in columns if is_price_keyword(col)]:
        meta = matched_meta[col]
        numeric_parse_pct = (meta["numeric_parse_rows"] / meta["non_null_rows"] * 100) if meta["non_null_rows"] else 0.0
        mean_value = (meta["sum_value"] / meta["numeric_parse_rows"]) if meta["numeric_parse_rows"] else None
        inventory_rows.append(
            {
                "file_name": path.name,
                "file_path": str(path.relative_to(DATA)),
                "column_name": col,
                "non_null_rows": int(meta["non_null_rows"]),
                "numeric_parse_rows": int(meta["numeric_parse_rows"]),
                "numeric_parse_pct": round(numeric_parse_pct, 2),
                "min_value": round(meta["min_value"], 4) if meta["numeric_parse_rows"] else "",
                "max_value": round(meta["max_value"], 4) if meta["numeric_parse_rows"] else "",
                "mean_value": round(mean_value, 4) if mean_value is not None else "",
                "sample_values": " | ".join(meta["sample_values"]),
                "excluded_reason": meta["excluded_reason"],
            }
        )

    file_row = {
        "file_path": str(path.relative_to(DATA)),
        "file_name": path.name,
        "rows": int(row_count),
        "columns_count": int(len(columns)),
        "has_meeting_date": bool(has_meeting_date),
        "has_track": bool(has_track),
        "has_race_no": bool(has_race_no),
        "has_horse": bool(has_horse),
        "has_horse_key": bool(has_horse_key),
        "has_price_like_column": bool(len(kept_columns) > 0),
        "price_like_columns": ", ".join(kept_columns),
        "likely_source_type": source_type,
        "candidate_rank": int(rank),
        "reason_v1": reason,
    }
    return file_row, inventory_rows


def main() -> None:
    csv_files = discover_csv_files(DATA)

    discovery_rows: list[dict[str, object]] = []
    inventory_rows: list[dict[str, object]] = []

    for path in csv_files:
        row, inv = analyse_file(path)
        discovery_rows.append(row)
        inventory_rows.extend(inv)

    discovery_df = pd.DataFrame(discovery_rows)
    inventory_df = pd.DataFrame(inventory_rows)

    if discovery_df.empty:
        discovery_df = pd.DataFrame(
            columns=[
                "file_path",
                "file_name",
                "rows",
                "columns_count",
                "has_meeting_date",
                "has_track",
                "has_race_no",
                "has_horse",
                "has_horse_key",
                "has_price_like_column",
                "price_like_columns",
                "likely_source_type",
                "candidate_rank",
                "reason_v1",
            ]
        )

    discovery_df = discovery_df.sort_values(["candidate_rank", "has_price_like_column", "file_name"], ascending=[False, False, True]).reset_index(drop=True)
    discovery_df.to_csv(OUT, index=False)

    candidate_df = discovery_df[
        (discovery_df["has_price_like_column"] == True)
        & (discovery_df["likely_source_type"].isin(["LIVE_MARKET_SOURCE", "RACECARD_WITH_MARKET", "RESULTS_WITH_SP"]))
    ].copy()
    candidate_df = candidate_df.sort_values(["candidate_rank", "rows", "file_name"], ascending=[False, False, True]).reset_index(drop=True)
    candidate_df.to_csv(CANDIDATES, index=False)

    inventory_df = inventory_df.sort_values(["file_name", "column_name"]).reset_index(drop=True)
    inventory_df.to_csv(INVENTORY, index=False)

    total_csv = int(len(discovery_df))
    files_with_price = int(discovery_df["has_price_like_column"].sum()) if not discovery_df.empty else 0
    live_candidates = int((discovery_df["likely_source_type"] == "LIVE_MARKET_SOURCE").sum()) if not discovery_df.empty else 0
    racecard_candidates = int((discovery_df["likely_source_type"] == "RACECARD_WITH_MARKET").sum()) if not discovery_df.empty else 0
    results_candidates = int((discovery_df["likely_source_type"] == "RESULTS_WITH_SP").sum()) if not discovery_df.empty else 0

    preferred = candidate_df[
        candidate_df["likely_source_type"].isin(["LIVE_MARKET_SOURCE", "RACECARD_WITH_MARKET"])
    ].copy()
    if not preferred.empty:
        raw_preferred = preferred[
            preferred["file_name"].str.lower().apply(lambda x: any(term in x for term in RAW_SOURCE_SELECT_TERMS))
        ].copy()
        raw_preferred = raw_preferred[raw_preferred["rows"] > 0]
        if not raw_preferred.empty:
            preferred = raw_preferred
    if preferred.empty:
        best_row = candidate_df.iloc[0] if not candidate_df.empty else None
    else:
        best_row = preferred.iloc[0]

    if best_row is None:
        best_candidate_file = ""
        best_candidate_rank = 0
        best_candidate_price_columns = ""
    else:
        best_candidate_file = str(best_row["file_path"])
        best_candidate_rank = int(best_row["candidate_rank"])
        best_candidate_price_columns = str(best_row["price_like_columns"])

    if best_candidate_rank >= 80 and best_row is not None and best_row["likely_source_type"] in {"LIVE_MARKET_SOURCE", "RACECARD_WITH_MARKET"}:
        verdict = "MARKET_SOURCE_CANDIDATE_FOUND"
    elif not candidate_df.empty:
        verdict = "MARKET_SOURCE_CANDIDATES_WEAK"
    else:
        verdict = "NO_CLEAN_MARKET_SOURCE_FOUND"

    summary_df = pd.DataFrame(
        [
            {"metric": "total_csv_files_scanned", "value": total_csv},
            {"metric": "files_with_price_like_columns", "value": files_with_price},
            {"metric": "candidate_live_market_files", "value": live_candidates},
            {"metric": "candidate_racecard_market_files", "value": racecard_candidates},
            {"metric": "candidate_results_sp_files", "value": results_candidates},
            {"metric": "best_candidate_file", "value": best_candidate_file},
            {"metric": "best_candidate_rank", "value": best_candidate_rank},
            {"metric": "best_candidate_price_columns", "value": best_candidate_price_columns},
            {"metric": "verdict", "value": verdict},
        ]
    )
    summary_df.to_csv(SUMMARY, index=False)

    print("[MARKET_SOURCE_COVERAGE_DISCOVERY_V1] COMPLETE")
    print(f"csv_files_scanned={total_csv}")
    print(f"files_with_price_like_columns={files_with_price}")
    print(f"candidate_files={len(candidate_df)}")
    print(f"best_candidate_file={best_candidate_file}")
    print(f"best_candidate_rank={best_candidate_rank}")
    print(f"best_candidate_price_columns={best_candidate_price_columns}")
    print(f"verdict={verdict}")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={CANDIDATES}")
    print(f"wrote={INVENTORY}")


if __name__ == "__main__":
    main()
