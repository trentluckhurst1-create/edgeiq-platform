from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_overlay_quality_audit_v5_2.csv"
OUT = DATA / "edgeiq_clean_overlay_review_board_v5_2.csv"
SUMMARY = DATA / "edgeiq_clean_overlay_review_board_v5_2_summary.csv"

CLEAN_CLASS = "CLEAN_RESEARCH_OVERLAY"
MARKET_SHAPE_REVIEW_THRESHOLD = 3


def norm(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def to_number(value: object) -> float:
    return pd.to_numeric(value, errors="coerce")


def fmt(value: object, decimals: int = 6) -> str:
    parsed = to_number(value)
    if pd.isna(parsed):
        return ""
    return f"{float(parsed):.{decimals}f}"


def clean_race_no(value: object) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def race_label(row: pd.Series) -> str:
    race_no = clean_race_no(row.get("race_no", ""))
    track = str(row.get("track", "")).strip()
    race_time = str(row.get("race_time", "")).strip()
    race_class = str(row.get("race_class_corrected", "")).strip()
    return f"R{race_no} {track} {race_time} {race_class}".strip()


def sportsbet_implied_probability(price: object) -> float:
    parsed = to_number(price)
    if pd.isna(parsed) or float(parsed) <= 0:
        return pd.NA
    return 1.0 / float(parsed)


def clean_warning_flags(row: pd.Series, race_review_flags: set[str]) -> str:
    flags = ["REVIEW_ONLY"]
    race_key = str(row.get("race_key_v5_2", ""))
    if race_key in race_review_flags:
        flags.append("MARKET_SHAPE_REVIEW")
    return "|".join(flags)


def review_note(row: pd.Series, race_target_available: bool) -> str:
    notes = [
        "Review only; clean overlay filter passed; not a betting recommendation.",
    ]
    if "MARKET_SHAPE_REVIEW" in str(row.get("warning_flags", "")).split("|"):
        notes.append("Race has 3+ clean overlays, so market shape needs review.")
    if not race_target_available:
        notes.append("Race target unavailable in overlay quality audit input.")
    return " ".join(notes)


def load_input() -> pd.DataFrame:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing overlay quality audit input: {INPUT}")

    df = pd.read_csv(INPUT, dtype=str, keep_default_na=False, low_memory=False)
    required = {
        "race_date",
        "track",
        "race_no",
        "race_time",
        "race_key_v5_2",
        "race_class_corrected",
        "horse",
        "rated_probability_v5_2_review",
        "rated_price_v5_2_review",
        "history_bucket_v5_2",
        "sportsbet_price",
        "sportsbet_price_band_v5_2",
        "price_role_v5_2",
        "overlay_percentage_v5_2",
        "overlay_percentage_band_v5_2",
        "overlay_quality_class_v5_2",
        "projection_gap_v5_2",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required columns from overlay quality audit: {missing}")
    return df


def target_column(df: pd.DataFrame) -> str | None:
    candidates = [
        "race_target",
        "race_target_rating_v5_2",
        "race_target_rating_v5_1",
        "target_rating_v5_2",
        "target_rating_v5_1",
    ]
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def build_board(df: pd.DataFrame) -> pd.DataFrame:
    clean = df[df["overlay_quality_class_v5_2"].map(norm).eq(CLEAN_CLASS)].copy()
    clean["race_no"] = clean["race_no"].map(clean_race_no)
    clean["sportsbet_price"] = pd.to_numeric(clean["sportsbet_price"], errors="coerce")
    clean["rated_price_v5_2_review"] = pd.to_numeric(
        clean["rated_price_v5_2_review"], errors="coerce"
    )
    clean["rated_probability_v5_2_review"] = pd.to_numeric(
        clean["rated_probability_v5_2_review"], errors="coerce"
    )
    clean["overlay_percentage_v5_2"] = pd.to_numeric(
        clean["overlay_percentage_v5_2"], errors="coerce"
    )
    clean["projection_gap_v5_2"] = pd.to_numeric(clean["projection_gap_v5_2"], errors="coerce")

    race_counts = clean.groupby("race_key_v5_2", dropna=False).size()
    market_shape_races = set(
        race_counts[race_counts >= MARKET_SHAPE_REVIEW_THRESHOLD].index.astype(str)
    )

    race_target_col = target_column(clean)
    race_target_available = race_target_col is not None

    board = pd.DataFrame()
    board["race"] = clean.apply(race_label, axis=1)
    board["horse"] = clean["horse"]
    board["sportsbet_price"] = clean["sportsbet_price"].map(lambda value: fmt(value, decimals=2))
    board["rated_price"] = clean["rated_price_v5_2_review"].map(
        lambda value: fmt(value, decimals=2)
    )
    board["overlay_pct"] = clean["overlay_percentage_v5_2"].map(
        lambda value: fmt(value, decimals=2)
    )
    board["rated_probability"] = clean["rated_probability_v5_2_review"].map(
        lambda value: fmt(value, decimals=6)
    )
    board["sportsbet_implied_probability"] = clean["sportsbet_price"].apply(
        lambda value: fmt(sportsbet_implied_probability(value), decimals=6)
    )
    board["projection_score"] = clean["projection_gap_v5_2"].map(
        lambda value: fmt(value, decimals=2)
    )
    if race_target_available:
        board["race_target"] = clean[race_target_col].map(lambda value: fmt(value, decimals=2))
    else:
        board["race_target"] = ""
    board["history_bucket"] = clean["history_bucket_v5_2"]
    board["price_role"] = clean["price_role_v5_2"]
    board["overlay_band"] = clean["overlay_percentage_band_v5_2"]
    board["warning_flags"] = clean.apply(
        lambda row: clean_warning_flags(row, market_shape_races), axis=1
    )
    board["review_note"] = board.join(clean[["race_key_v5_2"]]).apply(
        lambda row: review_note(row, race_target_available), axis=1
    )

    sort_frame = board.copy()
    sort_frame["_overlay_sort"] = pd.to_numeric(sort_frame["overlay_pct"], errors="coerce")
    sort_frame["_race_sort"] = clean["race_no"].astype(int).to_numpy()
    sort_frame = sort_frame.sort_values(["_race_sort", "_overlay_sort"], ascending=[True, False])
    return sort_frame.drop(columns=["_overlay_sort", "_race_sort"]).reset_index(drop=True)


def summary_record(
    section: str,
    group: str,
    clean_overlay_count: int,
    avg_overlay_pct: object = "",
    max_overlay_pct: object = "",
    min_overlay_pct: object = "",
    market_shape_review: str = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "group": group,
        "clean_overlay_count": clean_overlay_count,
        "avg_overlay_pct": fmt(avg_overlay_pct, decimals=2),
        "max_overlay_pct": fmt(max_overlay_pct, decimals=2),
        "min_overlay_pct": fmt(min_overlay_pct, decimals=2),
        "market_shape_review": market_shape_review,
        "notes": notes,
    }


def aggregate(board: pd.DataFrame, section: str, column: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for group, frame in board.groupby(column, dropna=False):
        overlays = pd.to_numeric(frame["overlay_pct"], errors="coerce")
        market_shape = "MARKET_SHAPE_REVIEW" if len(frame) >= MARKET_SHAPE_REVIEW_THRESHOLD else ""
        rows.append(
            summary_record(
                section=section,
                group=str(group),
                clean_overlay_count=len(frame),
                avg_overlay_pct=overlays.mean(),
                max_overlay_pct=overlays.max(),
                min_overlay_pct=overlays.min(),
                market_shape_review=market_shape,
            )
        )
    return rows


def build_summary(board: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    overlays = pd.to_numeric(board["overlay_pct"], errors="coerce")

    rows.append(
        summary_record(
            section="overall",
            group="ALL",
            clean_overlay_count=len(board),
            avg_overlay_pct=overlays.mean(),
            max_overlay_pct=overlays.max(),
            min_overlay_pct=overlays.min(),
            notes="Review board only. No execution, no production prices, no bet recommendations.",
        )
    )

    rows.extend(aggregate(board, "overlays_by_race", "race"))
    rows.extend(aggregate(board, "price_band_distribution", "overlay_band"))
    rows.extend(aggregate(board, "favourite_mid_longshot_distribution", "price_role"))
    rows.extend(aggregate(board, "warning_flags", "warning_flags"))

    summary = pd.DataFrame(rows)
    summary["built_at_clean_overlay_review_board_v5_2"] = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")
    return summary


def main() -> None:
    print("=" * 90)
    print("EDGEIQ CLEAN OVERLAY REVIEW BOARD V5.2 - REVIEW ONLY")
    print("=" * 90)

    source = load_input()
    board = build_board(source)
    summary = build_summary(board)

    board.to_csv(OUT, index=False)
    summary.to_csv(SUMMARY, index=False)

    print(f"input: {INPUT}")
    print(f"wrote: {OUT}")
    print(f"wrote: {SUMMARY}")
    print()
    print(summary[summary["section"].eq("overall")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("overlays_by_race")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("price_band_distribution")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("favourite_mid_longshot_distribution")].to_string(index=False))
    print()
    print(board.to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
