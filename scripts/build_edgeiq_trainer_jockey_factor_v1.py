from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER = DATA / "edgeiq_trainer_jockey_edge_runner_dataset_v3.csv"

OUT_TRAINER = DATA / "edgeiq_trainer_factor_v1.csv"
OUT_JOCKEY = DATA / "edgeiq_jockey_factor_v1.csv"
OUT_COMBO = DATA / "edgeiq_trainer_jockey_combo_factor_v1.csv"
OUT_RUNNER = DATA / "edgeiq_trainer_jockey_factor_runner_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_trainer_jockey_factor_v1_summary.csv"
OUT_JSON = DATA / "edgeiq_trainer_jockey_factor_v1.json"


def num(s):
    return pd.to_numeric(s, errors="coerce")


def factor_band(rate, starts, kind):
    if pd.isna(rate) or starts <= 0:
        return "UNKNOWN"

    if kind == "COMBO":
        if starts < 50:
            return "LOW_SAMPLE"
        if rate >= 20:
            return "ELITE"
        if rate >= 15:
            return "POSITIVE"
        if rate >= 10:
            return "NEUTRAL"
        if rate >= 7:
            return "NEGATIVE"
        return "POOR"

    if starts < 100:
        return "LOW_SAMPLE"
    if rate >= 18:
        return "ELITE"
    if rate >= 14:
        return "POSITIVE"
    if rate >= 10:
        return "NEUTRAL"
    if rate >= 7:
        return "NEGATIVE"
    return "POOR"


def factor_score(b):
    return {
        "ELITE": 2.0,
        "POSITIVE": 1.0,
        "NEUTRAL": 0.0,
        "NEGATIVE": -1.0,
        "POOR": -2.0,
        "LOW_SAMPLE": 0.0,
        "UNKNOWN": 0.0,
    }.get(str(b).strip().upper(), 0.0)


def quality(df, key_col, name_col, kind):
    g = (
        df.groupby(key_col, dropna=False)
        .agg(
            name=(name_col, "first"),
            starts=("won", "size"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            races=("race_key_join", "nunique"),
            horses=("horse_key_join", "nunique"),
        )
        .reset_index()
    )
    g["win_pct"] = np.where(g["starts"] > 0, g["wins"] / g["starts"] * 100, 0).round(2)
    g["place_pct"] = np.where(g["starts"] > 0, g["places"] / g["starts"] * 100, 0).round(2)
    g["factor_band"] = [factor_band(r, s, kind) for r, s in zip(g["win_pct"], g["starts"])]
    g["factor_score"] = g["factor_band"].map(factor_score)
    g["entity_type"] = kind
    return g


def main():
    if not RUNNER.exists():
        raise FileNotFoundError(f"Missing V3 runner dataset. Run build_edgeiq_trainer_jockey_edge_audit_v3.py first: {RUNNER}")

    df = pd.read_csv(RUNNER, low_memory=False)
    df["won"] = num(df["won"]).fillna(0).astype(int)
    df["placed"] = num(df["placed"]).fillna(0).astype(int)

    required = [
        "trainer_canonical_key",
        "trainer_canonical",
        "jockey_canonical_key",
        "jockey_canonical",
        "trainer_jockey_canonical_key",
        "trainer_jockey_canonical",
        "race_key_join",
        "horse_key_join",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required V3 columns: {missing}")

    trainer = quality(df, "trainer_canonical_key", "trainer_canonical", "TRAINER")
    jockey = quality(df, "jockey_canonical_key", "jockey_canonical", "JOCKEY")
    combo = quality(df, "trainer_jockey_canonical_key", "trainer_jockey_canonical", "COMBO")

    trainer_out = trainer.rename(columns={
        "trainer_canonical_key": "trainer_key",
        "name": "trainer",
        "starts": "trainer_starts_v1",
        "wins": "trainer_wins_v1",
        "places": "trainer_places_v1",
        "win_pct": "trainer_win_pct_v1",
        "place_pct": "trainer_place_pct_v1",
        "factor_band": "trainer_factor_band_v1",
        "factor_score": "trainer_factor_score_v1",
    })

    jockey_out = jockey.rename(columns={
        "jockey_canonical_key": "jockey_key",
        "name": "jockey",
        "starts": "jockey_starts_v1",
        "wins": "jockey_wins_v1",
        "places": "jockey_places_v1",
        "win_pct": "jockey_win_pct_v1",
        "place_pct": "jockey_place_pct_v1",
        "factor_band": "jockey_factor_band_v1",
        "factor_score": "jockey_factor_score_v1",
    })

    combo_out = combo.rename(columns={
        "trainer_jockey_canonical_key": "trainer_jockey_key",
        "name": "trainer_jockey",
        "starts": "combo_starts_v1",
        "wins": "combo_wins_v1",
        "places": "combo_places_v1",
        "win_pct": "combo_win_pct_v1",
        "place_pct": "combo_place_pct_v1",
        "factor_band": "combo_factor_band_v1",
        "factor_score": "combo_factor_score_v1",
    })

    runner = df.copy()

    runner = runner.merge(
        trainer_out[["trainer_key", "trainer_starts_v1", "trainer_win_pct_v1", "trainer_place_pct_v1", "trainer_factor_band_v1", "trainer_factor_score_v1"]],
        left_on="trainer_canonical_key",
        right_on="trainer_key",
        how="left",
        validate="many_to_one",
    )

    runner = runner.merge(
        jockey_out[["jockey_key", "jockey_starts_v1", "jockey_win_pct_v1", "jockey_place_pct_v1", "jockey_factor_band_v1", "jockey_factor_score_v1"]],
        left_on="jockey_canonical_key",
        right_on="jockey_key",
        how="left",
        validate="many_to_one",
    )

    runner = runner.merge(
        combo_out[["trainer_jockey_key", "combo_starts_v1", "combo_win_pct_v1", "combo_place_pct_v1", "combo_factor_band_v1", "combo_factor_score_v1"]],
        left_on="trainer_jockey_canonical_key",
        right_on="trainer_jockey_key",
        how="left",
        validate="many_to_one",
    )

    runner["trainer_jockey_blend_score_v1"] = (
        runner["trainer_factor_score_v1"].fillna(0) * 0.35
        + runner["jockey_factor_score_v1"].fillna(0) * 0.45
        + runner["combo_factor_score_v1"].fillna(0) * 0.20
    ).round(3)

    runner["trainer_jockey_blend_band_v1"] = np.select(
        [
            runner["trainer_jockey_blend_score_v1"] >= 1.25,
            runner["trainer_jockey_blend_score_v1"] >= 0.50,
            runner["trainer_jockey_blend_score_v1"] <= -1.25,
            runner["trainer_jockey_blend_score_v1"] <= -0.50,
        ],
        ["ELITE", "POSITIVE", "POOR", "NEGATIVE"],
        default="NEUTRAL",
    )

    trainer_out.to_csv(OUT_TRAINER, index=False)
    jockey_out.to_csv(OUT_JOCKEY, index=False)
    combo_out.to_csv(OUT_COMBO, index=False)
    runner.to_csv(OUT_RUNNER, index=False)

    summary = pd.DataFrame([
        ["runner_rows", len(runner)],
        ["trainer_rows", len(trainer_out)],
        ["jockey_rows", len(jockey_out)],
        ["combo_rows", len(combo_out)],
        ["trainer_elite", int((trainer_out["trainer_factor_band_v1"] == "ELITE").sum())],
        ["jockey_elite", int((jockey_out["jockey_factor_band_v1"] == "ELITE").sum())],
        ["combo_elite", int((combo_out["combo_factor_band_v1"] == "ELITE").sum())],
        ["important_note", "Observation only. No fair price, no execution, no SP."],
    ], columns=["metric", "value"])
    summary.to_csv(OUT_SUMMARY, index=False)

    OUT_JSON.write_text(json.dumps({
        "status": "COMPLETE",
        "runner_rows": int(len(runner)),
        "trainer_rows": int(len(trainer_out)),
        "jockey_rows": int(len(jockey_out)),
        "combo_rows": int(len(combo_out)),
        "important_note": "Observation only. No fair price, no execution, no SP.",
    }, indent=2), encoding="utf-8")

    print("[TRAINER_JOCKEY_FACTOR_V1] COMPLETE")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
