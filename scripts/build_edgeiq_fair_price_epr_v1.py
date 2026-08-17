from pathlib import Path
from datetime import datetime, timezone
import os

import numpy as np
import pandas as pd

from edgeiq_current_feed_authority_v1 import choose_current_feed_authority


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJECTION = DATA / "edgeiq_current_field_projection_v5_2.csv"
CURRENT_EPR = DATA / "edgeiq_epi_current_rating_v1.csv"
CURRENT_EPR_JSON = DATA / "edgeiq_epi_current_rating_v1.json"

OUT = DATA / "edgeiq_fair_price_epr_v1.csv"
AUDIT = DATA / "edgeiq_fair_price_epr_v1_audit.csv"

MODEL_POWER = 1.35
NO_HISTORY_GAP_PENALTY = 2.0
CURRENT_EPR_STATUS_VALUES = {"CURRENT", "EPI_AVAILABLE"}


def clean_race_no(v):
    return str(v).replace(".0", "").strip()


def first_existing_column(frame: pd.DataFrame, names: list[str]) -> str:
    for name in names:
        if name in frame.columns:
            return name
    raise KeyError(names[0])


def load_current_epr_frame() -> tuple[pd.DataFrame, str]:
    selected_path, inspection, _inspections, reason = choose_current_feed_authority(
        [CURRENT_EPR, CURRENT_EPR_JSON],
        "edgeiq_epi_current_rating_v1",
        critical=True,
    )
    if selected_path.suffix.lower() == ".json":
        frame = pd.DataFrame(list(inspection.records))
    else:
        frame = pd.read_csv(
            selected_path,
            dtype=str,
            keep_default_na=False,
            low_memory=False,
        )
    if frame.empty:
        raise FileNotFoundError(f"Current EPR authority is empty: {selected_path}")
    frame = frame.fillna("")
    frame.attrs["edgeiq_authority_reason"] = reason
    return frame, selected_path.name




def build_from_current_epr_feed(pipeline_date: str = "") -> None:
    df, epr_source_name = load_current_epr_frame()
    epr_source_reason = str(df.attrs.get("edgeiq_authority_reason", ""))

    df["raceDate"] = df["raceDate"].astype(str).str.strip()
    if pipeline_date:
        df = df[df["raceDate"].eq(pipeline_date)].copy()

    if df.empty:
        raise ValueError(f"EPR_FAIR_PRICE_CURRENT_EPR_EMPTY: {pipeline_date or 'FULL_LIVE_WINDOW'}")

    df["race_date"] = df["raceDate"].astype(str).str.strip()
    df["track"] = df["meeting"].astype(str).str.strip()
    df["race_no"] = df["raceNumber"].map(clean_race_no)
    df["horse"] = df["runnerName"].astype(str).str.strip()
    runner_key_col = first_existing_column(
        df,
        ["normalizedRunnerName", "normalisedRunnerName"],
    )
    df["horse_key"] = df[runner_key_col].astype(str).str.strip()
    df["saddlecloth"] = df["runnerNumber"].astype(str).str.strip()
    df["horse_no"] = df["runnerNumber"].astype(str).str.strip()
    df["race_key_epr_market"] = (
        df["race_date"] + "|" + df["track"].str.upper().str.strip() + "|R" + df["race_no"]
    )
    df["epr_value"] = pd.to_numeric(df["value"], errors="coerce")
    df["epr_status"] = df["status"].astype(str).str.upper().str.strip()
    df = df[~df["epr_status"].eq("SCRATCHED")].copy()

    if df.empty:
        raise ValueError(f"EPR_FAIR_PRICE_ACTIVE_CURRENT_EPR_EMPTY: {pipeline_date}")

    df["is_no_history_epr_market"] = ~(
        df["epr_status"].isin(CURRENT_EPR_STATUS_VALUES)
        & df["epr_value"].notna()
    )

    frames = []
    for race_key, race in df.groupby("race_key_epr_market", dropna=False):
        race = race.copy()
        known = ~race["is_no_history_epr_market"]
        known_count = int(known.sum())
        no_history_count = int((~known).sum())
        race["epr_market_gap_used"] = np.nan
        race["epr_market_no_history_policy"] = ""
        race["epr_market_score"] = np.nan
        race["edgeiq_probability_epr_v1"] = np.nan
        race["edgeiq_price_epr_v1"] = np.nan
        race["edgeiq_rank_epr_v1"] = np.nan
        if known_count == 0:
            race["epr_market_no_history_policy"] = "NO_CURRENT_EPR_NO_PRICE"
            race["race_probability_sum_epr_v1"] = 0.0
        else:
            race.loc[known, "epr_market_gap_used"] = race.loc[known, "epr_value"]
            race.loc[known, "epr_market_no_history_policy"] = "REAL_GOVERNED_EPR"
            race.loc[~known, "epr_market_no_history_policy"] = "NO_CURRENT_EPR_NO_PRICE"
            race_min = race.loc[known, "epr_market_gap_used"].min()
            race.loc[known, "epr_market_score"] = (race.loc[known, "epr_market_gap_used"] - race_min + 1.0).clip(lower=0.000001).pow(MODEL_POWER)
            score_sum = race.loc[known, "epr_market_score"].sum()
            if not np.isfinite(score_sum) or score_sum <= 0:
                raise ValueError(f"INVALID_EPR_MARKET_SCORE_SUM: {race_key}")
            race.loc[known, "edgeiq_probability_epr_v1"] = (race.loc[known, "epr_market_score"] / score_sum).round(8)
            race.loc[known, "edgeiq_price_epr_v1"] = (1.0 / race.loc[known, "edgeiq_probability_epr_v1"]).round(2)
            race.loc[known, "edgeiq_rank_epr_v1"] = race.loc[known, "edgeiq_probability_epr_v1"].rank(ascending=False, method="first").astype(int)
            race["race_probability_sum_epr_v1"] = race.loc[known, "edgeiq_probability_epr_v1"].sum()
        race["known_epr_runner_count"] = known_count
        race["no_history_runner_count"] = no_history_count
        frames.append(race)

    out = pd.concat(frames, ignore_index=True)
    priced = out[out["edgeiq_probability_epr_v1"].notna()].copy()
    race_sums = priced.groupby("race_key_epr_market")["edgeiq_probability_epr_v1"].sum()
    probability_failures = int(((race_sums - 1.0).abs() > 0.00001).sum())
    if probability_failures:
        raise ValueError(f"EPR_MARKET_PROBABILITY_SUM_FAILURES={probability_failures}")

    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    out["edgeiq_price_engine"] = "EPR_MARKET_V1"
    out["edgeiq_price_engine_method"] = "EPR_FIELD_RELATIVE_POWER_NORMALIZATION"
    out["edgeiq_price_engine_parameters"] = f"power={MODEL_POWER};source=edgeiq_epi_current_rating_v1"
    out["built_at_epr_market_v1"] = built_at
    out.to_csv(OUT, index=False)

    audit = pd.DataFrame([
        {"metric": "pipeline_date", "value": pipeline_date or "FULL_LIVE_WINDOW"},
        {"metric": "source", "value": epr_source_name},
        {"metric": "source_authority_reason", "value": epr_source_reason},
        {"metric": "rows", "value": len(out)},
        {"metric": "races", "value": out["race_key_epr_market"].nunique()},
        {"metric": "epr_current", "value": int((~out["is_no_history_epr_market"]).sum())},
        {"metric": "no_history_policy_rows", "value": int(out["is_no_history_epr_market"].sum())},
        {"metric": "priced_without_current_epr", "value": int(((~out["epr_status"].isin(CURRENT_EPR_STATUS_VALUES)) & out["edgeiq_price_epr_v1"].notna()).sum())},
        {"metric": "public_market_inputs", "value": 0},
        {"metric": "eri_weight", "value": 0},
    ])
    audit.to_csv(AUDIT, index=False)
    print(f"EDGEIQ_FAIR_PRICE_EPR_V1 rows={len(out)} races={out['race_key_epr_market'].nunique()} source={epr_source_name}")

def main():
    pipeline_date = os.environ.get("EDGEIQ_EPR_PRICE_DATE", "").strip()

    # Fair price authority is the governed current EPR publication. The
    # projection feed may be used upstream to publish EPR, but prices must not
    # depend on legacy projection-gap target fields that are unavailable for
    # some current-window race classes. By default this publishes the full
    # current three-day window; EDGEIQ_EPR_PRICE_DATE is reserved for a scoped
    # operator replay.
    build_from_current_epr_feed(pipeline_date)
    return

    if not PROJECTION.exists():
        raise FileNotFoundError(PROJECTION)

    df = pd.read_csv(
        PROJECTION,
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )

    required = {
        "race_date",
        "track",
        "race_no",
        "horse",
        "history_match_status_v5_2",
        "starts_found_v5_2",
        "projected_rating_v5_2",
        "race_target_rating_v5_2",
        "projection_gap_v5_2",
    }

    missing = sorted(required.difference(df.columns))

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Strict current-window contract. Operators may still set
    # EDGEIQ_PIPELINE_DATE for a deliberately scoped replay.
    df["race_date"] = df["race_date"].astype(str).str.strip()
    if pipeline_date:
        df = df[df["race_date"].eq(pipeline_date)].copy()

    if df.empty:
        build_from_current_epr_feed(pipeline_date)
        return

    # Projection builder already excludes scratches, but remain defensive.
    if "is_scratched_bool_v5_2" in df.columns:
        scratched = (
            df["is_scratched_bool_v5_2"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "yes"])
        )
        df = df[~scratched].copy()

    df["race_no"] = df["race_no"].map(clean_race_no)

    df["race_key_epr_market"] = (
        df["race_date"].astype(str)
        + "|"
        + df["track"].astype(str).str.upper().str.strip()
        + "|R"
        + df["race_no"].astype(str)
    )

    df["starts_found_v5_2"] = pd.to_numeric(
        df["starts_found_v5_2"],
        errors="coerce",
    ).fillna(0).astype(int)

    for col in [
        "projected_rating_v5_2",
        "race_target_rating_v5_2",
        "projection_gap_v5_2",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["epr_value"] = df["projected_rating_v5_2"]

    df["epr_status"] = np.where(
        df["epr_value"].notna(),
        "CURRENT",
        "NO_HISTORY",
    )

    df["is_no_history_epr_market"] = (
        df["history_match_status_v5_2"].astype(str).eq("NO_HISTORY")
        | df["starts_found_v5_2"].eq(0)
        | df["projection_gap_v5_2"].isna()
    )

    frames = []

    for race_key, race in df.groupby(
        "race_key_epr_market",
        dropna=False,
    ):
        race = race.copy()

        known = (
            ~race["is_no_history_epr_market"]
            & race["projection_gap_v5_2"].notna()
        )

        known_count = int(known.sum())
        no_history_count = int(
            race["is_no_history_epr_market"].sum()
        )

        race["epr_market_gap_used"] = np.nan
        race["epr_market_no_history_policy"] = ""
        race["epr_market_score"] = np.nan
        race["edgeiq_probability_epr_v1"] = np.nan
        race["edgeiq_price_epr_v1"] = np.nan
        race["edgeiq_rank_epr_v1"] = np.nan

        if known_count == 0:
            race["epr_market_no_history_policy"] = (
                "NO_CURRENT_EPR_NO_PRICE"
            )
            race["race_probability_sum_epr_v1"] = 0.0
        else:
            race.loc[
                known,
                "epr_market_gap_used"
            ] = race.loc[
                known,
                "projection_gap_v5_2"
            ]

            race.loc[
                known,
                "epr_market_no_history_policy"
            ] = "REAL_EPR_PROJECTION_GAP"

            race.loc[
                ~known,
                "epr_market_no_history_policy"
            ] = (
                "NO_CURRENT_EPR_NO_PRICE"
            )

            race_min = race.loc[known, "epr_market_gap_used"].min()

            race.loc[known, "epr_market_score"] = (
                (
                race.loc[known, "epr_market_gap_used"]
                - race_min
                + 1.0
                )
                .clip(lower=0.000001)
                .pow(MODEL_POWER)
            )

            score_sum = race.loc[known, "epr_market_score"].sum()

            if not np.isfinite(score_sum) or score_sum <= 0:
                raise ValueError(
                    f"INVALID_EPR_MARKET_SCORE_SUM: {race_key}"
                )

            race.loc[known, "edgeiq_probability_epr_v1"] = (
                race.loc[known, "epr_market_score"] / score_sum
            )

            race.loc[known, "edgeiq_price_epr_v1"] = (
                1.0 / race.loc[known, "edgeiq_probability_epr_v1"]
            )

            race.loc[known, "edgeiq_probability_epr_v1"] = (
                race.loc[known, "edgeiq_probability_epr_v1"].round(8)
            )

            race.loc[known, "edgeiq_price_epr_v1"] = (
                race.loc[known, "edgeiq_price_epr_v1"].round(2)
            )

            race.loc[known, "edgeiq_rank_epr_v1"] = (
                race.loc[known, "edgeiq_probability_epr_v1"]
                .rank(
                    ascending=False,
                    method="first",
                )
                .astype(int)
            )

            race["race_probability_sum_epr_v1"] = (
                race.loc[known, "edgeiq_probability_epr_v1"].sum()
            )

        race["known_epr_runner_count"] = known_count
        race["no_history_runner_count"] = no_history_count

        frames.append(race)

    out = pd.concat(frames, ignore_index=True)

    # Hard integrity gates.
    bad_date = int((~out["race_date"].eq(pipeline_date)).sum()) if pipeline_date else 0

    if bad_date:
        raise ValueError(
            f"EPR_MARKET_DATE_CONTAMINATION={bad_date}"
        )

    priced = out[out["edgeiq_probability_epr_v1"].notna()].copy()
    race_sums = (
        priced.groupby("race_key_epr_market")[
            "edgeiq_probability_epr_v1"
        ].sum()
    )

    probability_failures = int(
        ((race_sums - 1.0).abs() > 0.00001).sum()
    )

    if probability_failures:
        raise ValueError(
            "EPR_MARKET_PROBABILITY_SUM_FAILURES="
            f"{probability_failures}"
        )

    out["edgeiq_price_engine"] = "EPR_MARKET_V1"
    out["edgeiq_price_engine_method"] = (
        "EPR_PROJECTION_GAP_POWER_NORMALIZATION"
    )

    out["edgeiq_price_engine_parameters"] = (
        f"power={MODEL_POWER};"
        f"no_history_gap_penalty="
        f"{NO_HISTORY_GAP_PENALTY}"
    )

    out["built_at_epr_market_v1"] = (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
    )

    out.to_csv(OUT, index=False)

    audit = pd.DataFrame([
        {
            "metric": "pipeline_date",
            "value": pipeline_date or "FULL_LIVE_WINDOW",
        },
        {
            "metric": "runners",
            "value": len(out),
        },
        {
            "metric": "races",
            "value": out["race_key_epr_market"].nunique(),
        },
        {
            "metric": "epr_current",
            "value": int(
                (~out["is_no_history_epr_market"]).sum()
            ),
        },
        {
            "metric": "no_history",
            "value": int(
                out["is_no_history_epr_market"].sum()
            ),
        },
        {
            "metric": "probability_rows",
            "value": int(
                out["edgeiq_probability_epr_v1"]
                .notna()
                .sum()
            ),
        },
        {
            "metric": "price_rows",
            "value": int(
                out["edgeiq_price_epr_v1"]
                .notna()
                .sum()
            ),
        },
        {
            "metric": "priced_without_current_epr",
            "value": int(
                (
                    out["epr_status"].ne("CURRENT")
                    & out["edgeiq_price_epr_v1"].notna()
                ).sum()
            ),
        },
        {
            "metric": "probability_sum_failures",
            "value": probability_failures,
        },
        {
            "metric": "model_power",
            "value": MODEL_POWER,
        },
        {
            "metric": "no_history_gap_penalty",
            "value": NO_HISTORY_GAP_PENALTY,
        },
        {
            "metric": "legacy_runner_score_used",
            "value": "NO",
        },
        {
            "metric": "legacy_live_strength_used",
            "value": "NO",
        },
        {
            "metric": "eri_used",
            "value": "NO_CURRENT_ERI_AVAILABLE",
        },
    ])

    audit.to_csv(AUDIT, index=False)

    print("[EPR_FAIR_PRICE_V1] COMPLETE")
    print(f"pipeline_date={pipeline_date}")
    print(f"runners={len(out)}")
    print(f"races={out['race_key_epr_market'].nunique()}")
    print(
        "epr_current="
        f"{int((~out['is_no_history_epr_market']).sum())}"
    )
    print(
        "no_history="
        f"{int(out['is_no_history_epr_market'].sum())}"
    )
    print(
        "probability_sum_failures="
        f"{probability_failures}"
    )
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")


if __name__ == "__main__":
    main()
