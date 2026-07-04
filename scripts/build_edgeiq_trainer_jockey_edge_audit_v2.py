from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_HISTORY = DATA / "edgeiq_trainer_jockey_runner_history_v1.csv"
MODEL_RUNNER = DATA / "edgeiq_race_reliability_replay_v1.csv"
TRAINER_QUALITY = DATA / "edgeiq_trainer_quality_audit_v1.csv"
JOCKEY_QUALITY = DATA / "edgeiq_jockey_quality_audit_v1.csv"
COMBO_QUALITY = DATA / "edgeiq_trainer_jockey_combo_quality_audit_v1.csv"

OUT_RUNNER = DATA / "edgeiq_trainer_jockey_edge_runner_dataset_v2.csv"
OUT_SUMMARY = DATA / "edgeiq_trainer_jockey_edge_audit_summary_v2.csv"
OUT_BY_RANK = DATA / "edgeiq_trainer_jockey_edge_by_rank_bucket_v2.csv"
OUT_BY_TRUST = DATA / "edgeiq_trainer_jockey_edge_by_trust_v2.csv"
OUT_BY_RELIABILITY = DATA / "edgeiq_trainer_jockey_edge_by_reliability_v2.csv"
OUT_BY_DOMINANCE = DATA / "edgeiq_trainer_jockey_edge_by_dominance_v2.csv"
OUT_BY_SCORE_SHARE = DATA / "edgeiq_trainer_jockey_edge_by_score_share_v2.csv"
OUT_AUDIT = DATA / "edgeiq_trainer_jockey_edge_audit_v2.json"


def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()


def key(x):
    return norm(x).replace(" ", "").replace("-", "").replace("_", "").replace("'", "")


def num(s):
    return pd.to_numeric(s, errors="coerce")


def make_join_key(date_s, track_s, race_no_s, horse_s):
    d = pd.to_datetime(date_s, errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    t = track_s.map(key)
    r = race_no_s.astype(str).str.extract(r"(\d+)")[0].fillna("")
    h = horse_s.map(key)
    return d + "|" + t + "|R" + r + "|" + h


def rank_bucket(x):
    if pd.isna(x):
        return "UNKNOWN"
    x = int(x)
    if x == 1:
        return "RANK_1"
    if x == 2:
        return "RANK_2"
    if x == 3:
        return "RANK_3"
    if 4 <= x <= 5:
        return "RANK_4_5"
    if 6 <= x <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def rate_band(rate, starts, kind):
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


def agg(df, group_cols, view):
    out = (
        df.groupby(group_cols, dropna=False)
        .agg(
            runners=("won", "size"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            races=("race_runner_key", "nunique"),
            horses=("horse_key_join", "nunique"),
        )
        .reset_index()
    )
    out["win_pct"] = np.where(out["runners"] > 0, out["wins"] / out["runners"] * 100, 0).round(2)
    out["place_pct"] = np.where(out["runners"] > 0, out["places"] / out["runners"] * 100, 0).round(2)
    out["audit_view"] = view
    return out


def lift_summary(df, entity_band, context_col=None, context_val=None):
    sub = df.copy()
    if context_col is not None:
        sub = sub[sub[context_col].astype(str) == str(context_val)].copy()

    valid = sub[sub[entity_band].isin(["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"])].copy()
    low = valid[valid[entity_band].isin(["POOR", "NEGATIVE"])]
    high = valid[valid[entity_band].isin(["POSITIVE", "ELITE"])]

    low_wp = low["won"].mean() * 100 if len(low) else np.nan
    high_wp = high["won"].mean() * 100 if len(high) else np.nan
    lift = high_wp - low_wp if not pd.isna(low_wp) and not pd.isna(high_wp) else np.nan

    return {
        "entity_band": entity_band,
        "context": context_col or "OVERALL",
        "context_value": context_val or "ALL",
        "valid_runners": int(len(valid)),
        "poor_negative_runners": int(len(low)),
        "poor_negative_win_pct": round(low_wp, 2) if not pd.isna(low_wp) else "",
        "positive_elite_runners": int(len(high)),
        "positive_elite_win_pct": round(high_wp, 2) if not pd.isna(high_wp) else "",
        "lift_pts": round(lift, 2) if not pd.isna(lift) else "",
    }


def verdict(row):
    try:
        n = int(row["valid_runners"])
        lift = float(row["lift_pts"])
    except Exception:
        return "INSUFFICIENT_DATA"

    if n < 1000:
        return "INSUFFICIENT_DATA"
    if lift >= 5:
        return "STRONG_DIRECTIONAL_SIGNAL"
    if lift >= 3:
        return "DIRECTIONAL_SIGNAL"
    if lift >= 1:
        return "WEAK_SIGNAL"
    return "NO_CLEAR_SIGNAL"


def main():
    for f in [RUNNER_HISTORY, MODEL_RUNNER, TRAINER_QUALITY, JOCKEY_QUALITY, COMBO_QUALITY]:
        if not f.exists():
            raise FileNotFoundError(f"Missing required input: {f}")

    hist = pd.read_csv(RUNNER_HISTORY, low_memory=False)
    model = pd.read_csv(MODEL_RUNNER, low_memory=False)

    hist["finish_position_num"] = num(hist["finish_position_v1"])
    hist = hist[hist["finish_position_num"].notna()].copy()

    hist["hist_join_key"] = make_join_key(
        hist["meeting_date"],
        hist["track"],
        hist["race_no"],
        hist["horse"],
    )

    model["model_join_key"] = make_join_key(
        model["meeting_date"],
        model["track"],
        model["race_no"],
        model["horse"],
    )

    model_keep = model[
        [
            "model_join_key",
            "runner_rank",
            "runner_score",
            "score_share_of_race",
            "score_share_band_v1",
            "dominance_score_v1",
            "dominance_band_v1",
            "trust_profile_v1",
            "trust_band_v1",
            "field_size",
            "field_size_bucket_v1",
            "race_reliability_score_v1",
            "race_reliability_band_v1",
            "won",
            "placed",
            "finish_position",
        ]
    ].drop_duplicates("model_join_key")

    df = hist.merge(model_keep, left_on="hist_join_key", right_on="model_join_key", how="inner")

    trainer = pd.read_csv(TRAINER_QUALITY, low_memory=False)
    jockey = pd.read_csv(JOCKEY_QUALITY, low_memory=False)
    combo = pd.read_csv(COMBO_QUALITY, low_memory=False)

    for c in ["trainer_key_norm"]:
        trainer[c] = trainer[c].map(norm)
    for c in ["jockey_key_norm"]:
        jockey[c] = jockey[c].map(norm)
    for c in ["trainer_key_norm", "jockey_key_norm"]:
        combo[c] = combo[c].map(norm)

    df["trainer_key_norm"] = df["trainer_key"].map(norm)
    df["jockey_key_norm"] = df["jockey_key"].map(norm)
    df["horse_key_join"] = df["horse_key"].map(key)
    df["race_runner_key"] = df["meeting_date"].astype(str) + "|" + df["track"].astype(str) + "|R" + df["race_no"].astype(str)

    trainer_small = trainer[["trainer_key_norm", "starts", "wins", "win_pct"]].rename(
        columns={"starts": "trainer_total_starts", "wins": "trainer_total_wins", "win_pct": "trainer_raw_win_pct"}
    )

    jockey_small = jockey[["jockey_key_norm", "starts", "wins", "win_pct"]].rename(
        columns={"starts": "jockey_total_starts", "wins": "jockey_total_wins", "win_pct": "jockey_raw_win_pct"}
    )

    combo_small = combo[["trainer_key_norm", "jockey_key_norm", "starts", "wins", "win_pct"]].rename(
        columns={"starts": "combo_total_starts", "wins": "combo_total_wins", "win_pct": "combo_raw_win_pct"}
    )

    df = df.merge(trainer_small, on="trainer_key_norm", how="left")
    df = df.merge(jockey_small, on="jockey_key_norm", how="left")
    df = df.merge(combo_small, on=["trainer_key_norm", "jockey_key_norm"], how="left")

    df["won"] = num(df["won"]).fillna(0).astype(int)
    df["placed"] = num(df["placed"]).fillna(0).astype(int)

    df["trainer_loo_starts"] = num(df["trainer_total_starts"]).fillna(0) - 1
    df["trainer_loo_wins"] = num(df["trainer_total_wins"]).fillna(0) - df["won"]
    df["trainer_loo_win_pct"] = np.where(df["trainer_loo_starts"] > 0, df["trainer_loo_wins"] / df["trainer_loo_starts"] * 100, np.nan)

    df["jockey_loo_starts"] = num(df["jockey_total_starts"]).fillna(0) - 1
    df["jockey_loo_wins"] = num(df["jockey_total_wins"]).fillna(0) - df["won"]
    df["jockey_loo_win_pct"] = np.where(df["jockey_loo_starts"] > 0, df["jockey_loo_wins"] / df["jockey_loo_starts"] * 100, np.nan)

    df["combo_loo_starts"] = num(df["combo_total_starts"]).fillna(0) - 1
    df["combo_loo_wins"] = num(df["combo_total_wins"]).fillna(0) - df["won"]
    df["combo_loo_win_pct"] = np.where(df["combo_loo_starts"] > 0, df["combo_loo_wins"] / df["combo_loo_starts"] * 100, np.nan)

    df["trainer_edge_band_v2"] = [rate_band(r, s, "TRAINER") for r, s in zip(df["trainer_loo_win_pct"], df["trainer_loo_starts"])]
    df["jockey_edge_band_v2"] = [rate_band(r, s, "JOCKEY") for r, s in zip(df["jockey_loo_win_pct"], df["jockey_loo_starts"])]
    df["combo_edge_band_v2"] = [rate_band(r, s, "COMBO") for r, s in zip(df["combo_loo_win_pct"], df["combo_loo_starts"])]

    df["rank_bucket_v2"] = num(df["runner_rank"]).map(rank_bucket)
    df["trust_profile_v1"] = df["trust_profile_v1"].map(norm)
    df["race_reliability_band_v1"] = df["race_reliability_band_v1"].map(norm)
    df["dominance_band_v1"] = df["dominance_band_v1"].map(norm)
    df["score_share_band_v1"] = df["score_share_band_v1"].map(norm)

    entity_cols = ["trainer_edge_band_v2", "jockey_edge_band_v2", "combo_edge_band_v2"]

    summaries = []
    for e in entity_cols:
        summaries.append(lift_summary(df, e))

    for e in entity_cols:
        for rv in ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS"]:
            summaries.append(lift_summary(df, e, "rank_bucket_v2", rv))

    for e in entity_cols:
        for rv in ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]:
            summaries.append(lift_summary(df, e, "race_reliability_band_v1", rv))

    summary = pd.DataFrame(summaries)
    summary["verdict"] = summary.apply(verdict, axis=1)

    by_rank = pd.concat([agg(df, ["rank_bucket_v2", e], e) for e in entity_cols], ignore_index=True)
    by_trust = pd.concat([agg(df, ["trust_profile_v1", e], e) for e in entity_cols], ignore_index=True)
    by_reliability = pd.concat([agg(df, ["race_reliability_band_v1", e], e) for e in entity_cols], ignore_index=True)
    by_dominance = pd.concat([agg(df, ["dominance_band_v1", e], e) for e in entity_cols], ignore_index=True)
    by_score_share = pd.concat([agg(df, ["score_share_band_v1", e], e) for e in entity_cols], ignore_index=True)

    runner_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "trainer",
        "jockey",
        "runner_rank",
        "rank_bucket_v2",
        "runner_score",
        "score_share_of_race",
        "score_share_band_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "field_size",
        "field_size_bucket_v1",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "won",
        "placed",
        "finish_position",
        "trainer_loo_starts",
        "trainer_loo_win_pct",
        "trainer_edge_band_v2",
        "jockey_loo_starts",
        "jockey_loo_win_pct",
        "jockey_edge_band_v2",
        "combo_loo_starts",
        "combo_loo_win_pct",
        "combo_edge_band_v2",
    ]

    df[runner_cols].to_csv(OUT_RUNNER, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    by_rank.to_csv(OUT_BY_RANK, index=False)
    by_trust.to_csv(OUT_BY_TRUST, index=False)
    by_reliability.to_csv(OUT_BY_RELIABILITY, index=False)
    by_dominance.to_csv(OUT_BY_DOMINANCE, index=False)
    by_score_share.to_csv(OUT_BY_SCORE_SHARE, index=False)

    audit = {
        "status": "COMPLETE",
        "raw_history_rows": int(len(hist)),
        "model_runner_rows": int(len(model)),
        "matched_runner_rows": int(len(df)),
        "match_rate_vs_history_pct": round(len(df) / len(hist) * 100, 2) if len(hist) else 0,
        "model_file_used": str(MODEL_RUNNER),
        "important_note": "V2 uses horse-level runner rank, score share, dominance, trust and Race Reliability. No SP, no A/E, no ROI, no execution change.",
        "outputs": {
            "runner_dataset": str(OUT_RUNNER),
            "summary": str(OUT_SUMMARY),
            "by_rank": str(OUT_BY_RANK),
            "by_trust": str(OUT_BY_TRUST),
            "by_reliability": str(OUT_BY_RELIABILITY),
            "by_dominance": str(OUT_BY_DOMINANCE),
            "by_score_share": str(OUT_BY_SCORE_SHARE),
        },
    }

    OUT_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print("[TRAINER_JOCKEY_EDGE_AUDIT_V2] COMPLETE")
    print(f"history_runner_rows={len(hist)}")
    print(f"model_runner_rows={len(model)}")
    print(f"matched_runner_rows={len(df)}")
    print(f"match_rate_vs_history_pct={round(len(df) / len(hist) * 100, 2) if len(hist) else 0}")
    print("")
    print(summary[summary["context"].eq("OVERALL")].to_string(index=False))


if __name__ == "__main__":
    main()
