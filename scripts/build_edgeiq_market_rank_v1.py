from pathlib import Path
import pandas as pd
import re
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SHAPE_FIT = DATA / "edgeiq_race_shape_fit_v1.csv"

MARKET_CANDIDATES = [
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_terminal_feed_v1.csv",
    DATA / "sportsbet_live_market_v1.csv",
    DATA / "edgeiq_tab_vic_racecards_v1.csv",
]

OUTPUT = DATA / "edgeiq_market_rank_v1.csv"
AUDIT = DATA / "edgeiq_market_rank_v1_audit.csv"

def clean_key(v):
    if pd.isna(v):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(v).upper().strip())

def num(v):
    try:
        if pd.isna(v):
            return np.nan
        x = float(str(v).replace("$", "").replace(",", "").strip())
        if x <= 0:
            return np.nan
        return x
    except Exception:
        return np.nan

def first_col(df, names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n in df.columns:
            return n
        if n.lower() in lower:
            return lower[n.lower()]
    return None

def normalize_race_no(v):
    s = str(v).upper().strip()
    s = s.replace("RACE", "").replace("R", "").strip()
    s = s.replace(".0", "")
    if not s:
        return ""
    return "R" + s

def build_race_key(df):
    if "race_key" in df.columns:
        return df["race_key"].astype(str).str.upper().str.strip().str.replace(r"\|([0-9]+)$", r"|R\1", regex=True)

    date_col = first_col(df, ["meeting_date", "race_date", "date"])
    track_col = first_col(df, ["track", "meeting_name", "venue", "location"])
    race_col = first_col(df, ["race_no", "race_number", "raceNo", "race"])

    if not all([date_col, track_col, race_col]):
        return pd.Series([""] * len(df))

    return (
        df[date_col].astype(str).str.strip()
        + "|"
        + df[track_col].astype(str).str.upper().str.strip()
        + "|"
        + df[race_col].apply(normalize_race_no)
    )

def pick_market_file():
    existing = [p for p in MARKET_CANDIDATES if p.exists()]
    if not existing:
        return None
    existing.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return existing[0]

def main():
    if not SHAPE_FIT.exists():
        raise FileNotFoundError(f"Missing input: {SHAPE_FIT}")

    market_file = pick_market_file()
    if market_file is None:
        raise FileNotFoundError("No market file found from candidate list")

    sf = pd.read_csv(SHAPE_FIT)
    mk = pd.read_csv(market_file)

    print("[MARKET_RANK_V1] market_file=" + str(market_file))
    print("[MARKET_RANK_V1] market columns:")
    print(", ".join(mk.columns))

    sf_horse_key = first_col(sf, ["horse_key", "horse_key_join", "horseKey"])
    sf_horse = first_col(sf, ["horse", "horse_name", "horseName"])

    mk_horse_key = first_col(mk, ["horse_key", "horse_key_join", "horseKey"])
    mk_horse = first_col(mk, ["horse", "horse_name", "horseName", "runner", "runner_name"])

    if sf_horse_key is None:
        sf["horse_key_join"] = sf[sf_horse].apply(clean_key)
    else:
        sf["horse_key_join"] = sf[sf_horse_key].apply(clean_key)

    if mk_horse_key is None:
        if mk_horse is None:
            raise ValueError("Market file has no horse column")
        mk["horse_key_join"] = mk[mk_horse].apply(clean_key)
    else:
        mk["horse_key_join"] = mk[mk_horse_key].apply(clean_key)

    sf["race_key_join"] = build_race_key(sf)
    mk["race_key_join"] = build_race_key(mk)

    price_col = first_col(mk, [
        "live_price",
        "ui_price",
        "sportsbet_price",
        "market_price",
        "fixed_win",
        "tab_fixed_win",
        "tab_price",
        "win_price",
        "price",
        "odds",
    ])

    if price_col is None:
        raise ValueError("Could not find market price column")

    mk["market_price_v1"] = mk[price_col].apply(num)

    mk_small = (
        mk[["race_key_join", "horse_key_join", "market_price_v1"]]
        .dropna(subset=["market_price_v1"])
        .drop_duplicates(["race_key_join", "horse_key_join"], keep="first")
    )

    mk_small["market_rank_v1"] = (
        mk_small.groupby("race_key_join")["market_price_v1"]
        .rank(method="min", ascending=True)
        .astype(int)
    )

    mk_small["market_field_size_v1"] = (
        mk_small.groupby("race_key_join")["horse_key_join"]
        .transform("count")
        .astype(int)
    )

    out = sf.merge(
        mk_small,
        on=["race_key_join", "horse_key_join"],
        how="left"
    )

    out["shape_fit_rank_in_race_num"] = pd.to_numeric(
        out["shape_fit_rank_in_race"],
        errors="coerce"
    )

    out["shape_edge_v1"] = (
        pd.to_numeric(out["market_rank_v1"], errors="coerce")
        - out["shape_fit_rank_in_race_num"]
    )

    out["shape_edge_band_v1"] = np.where(
        out["shape_edge_v1"] >= 8,
        "MASSIVE_SHAPE_EDGE",
        np.where(
            out["shape_edge_v1"] >= 5,
            "STRONG_SHAPE_EDGE",
            np.where(
                out["shape_edge_v1"] >= 3,
                "POSITIVE_SHAPE_EDGE",
                np.where(
                    out["shape_edge_v1"] <= -5,
                    "MARKET_OVERVALUES",
                    np.where(
                        out["shape_edge_v1"] <= -3,
                        "NEGATIVE_SHAPE_EDGE",
                        "NEUTRAL"
                    )
                )
            )
        )
    )

    out["market_rank_engine"] = "MARKET_RANK_V1"
    out["market_rank_input_shape_fit"] = SHAPE_FIT.name
    out["market_rank_input_market"] = market_file.name
    out["market_price_column_used"] = price_col

    preferred = [
        "race_key",
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "horse_key_join",
        "race_shape_v1",
        "ability_dna_v3",
        "race_shape_fit_score_v1",
        "race_shape_fit_band_v1",
        "shape_fit_rank_in_race",
        "shape_fit_percentile_in_race",
        "market_price_v1",
        "market_rank_v1",
        "market_field_size_v1",
        "shape_edge_v1",
        "shape_edge_band_v1",
        "hidden_runner_score_v1",
        "hidden_runner_band_v1",
    ]

    preferred = [c for c in preferred if c in out.columns]
    remaining = [c for c in out.columns if c not in preferred]
    out = out[preferred + remaining]

    out.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "shape_fit_rows": len(sf),
        "market_rows": len(mk),
        "output_rows": len(out),
        "matched_market_prices": int(out["market_price_v1"].notna().sum()),
        "unmatched_market_prices": int(out["market_price_v1"].isna().sum()),
        "unique_races_with_market": int(mk_small["race_key_join"].nunique()),
        "price_column_used": price_col,
        "market_file_used": str(market_file),
        "massive_shape_edge": int((out["shape_edge_band_v1"] == "MASSIVE_SHAPE_EDGE").sum()),
        "strong_shape_edge": int((out["shape_edge_band_v1"] == "STRONG_SHAPE_EDGE").sum()),
        "positive_shape_edge": int((out["shape_edge_band_v1"] == "POSITIVE_SHAPE_EDGE").sum()),
        "market_overvalues": int((out["shape_edge_band_v1"] == "MARKET_OVERVALUES").sum()),
        "negative_shape_edge": int((out["shape_edge_band_v1"] == "NEGATIVE_SHAPE_EDGE").sum()),
        "neutral": int((out["shape_edge_band_v1"] == "NEUTRAL").sum()),
        "output": str(OUTPUT),
    }])

    audit.to_csv(AUDIT, index=False)

    print("[MARKET_RANK_V1] COMPLETE")
    print(f"market_file={market_file}")
    print(f"price_column_used={price_col}")
    print(f"output_rows={len(out)}")
    print(f"matched_market_prices={int(out['market_price_v1'].notna().sum())}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")
    print(out["shape_edge_band_v1"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()

