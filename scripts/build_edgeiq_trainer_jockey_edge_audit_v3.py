from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST = DATA / "edgeiq_trainer_jockey_runner_history_canonical_v1.csv"
MODEL = DATA / "edgeiq_race_reliability_replay_v1.csv"

OUT_RUNNER = DATA / "edgeiq_trainer_jockey_edge_runner_dataset_v3.csv"
OUT_TRAINER_QUALITY = DATA / "edgeiq_trainer_canonical_quality_v3.csv"
OUT_JOCKEY_QUALITY = DATA / "edgeiq_jockey_canonical_quality_v3.csv"
OUT_COMBO_QUALITY = DATA / "edgeiq_trainer_jockey_combo_canonical_quality_v3.csv"
OUT_SUMMARY = DATA / "edgeiq_trainer_jockey_edge_audit_summary_v3.csv"
OUT_BY_RANK = DATA / "edgeiq_trainer_jockey_edge_by_rank_bucket_v3.csv"
OUT_BY_TRUST = DATA / "edgeiq_trainer_jockey_edge_by_trust_v3.csv"
OUT_BY_RELIABILITY = DATA / "edgeiq_trainer_jockey_edge_by_reliability_v3.csv"
OUT_BY_DOMINANCE = DATA / "edgeiq_trainer_jockey_edge_by_dominance_v3.csv"
OUT_BY_SCORE_SHARE = DATA / "edgeiq_trainer_jockey_edge_by_score_share_v3.csv"
OUT_JSON = DATA / "edgeiq_trainer_jockey_edge_audit_v3.json"


def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()


def key(x):
    return norm(x).replace(" ", "").replace("-", "").replace("_", "").replace("'", "")


def num(s):
    return pd.to_numeric(s, errors="coerce")


def make_join_key(df, date_col, track_col, race_col, horse_col):
    d = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    t = df[track_col].map(key)
    r = df[race_col].astype(str).str.extract(r"(\d+)")[0].fillna("")
    h = df[horse_col].map(key)
    return d + "|" + t + "|R" + r + "|" + h


def rank_bucket(x):
    if pd.isna(x):
        return "UNKNOWN"
    x = int(float(x))
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


def edge_band(rate, starts, kind):
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


def build_quality(df, key_col, name_col, entity_type):
    g = (
        df.groupby(key_col, dropna=False)
        .agg(
            canonical_name=(name_col, "first"),
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
    g["entity_type"] = entity_type
    return g


def agg(df, group_cols, view):
    g = (
        df.groupby(group_cols, dropna=False)
        .agg(
            runners=("won", "size"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            races=("race_key_join", "nunique"),
            horses=("horse_key_join", "nunique"),
        )
        .reset_index()
    )
    g["win_pct"] = np.where(g["runners"] > 0, g["wins"] / g["runners"] * 100, 0).round(2)
    g["place_pct"] = np.where(g["runners"] > 0, g["places"] / g["runners"] * 100, 0).round(2)
    g["audit_view"] = view
    return g


def lift(df, entity_band, context="OVERALL", context_value="ALL"):
    sub = df.copy()
    if context != "OVERALL":
        sub = sub[sub[context].astype(str) == str(context_value)].copy()

    valid = sub[sub[entity_band].isin(["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"])].copy()
    low = valid[valid[entity_band].isin(["POOR", "NEGATIVE"])]
    high = valid[valid[entity_band].isin(["POSITIVE", "ELITE"])]

    low_wp = low["won"].mean() * 100 if len(low) else np.nan
    high_wp = high["won"].mean() * 100 if len(high) else np.nan
    lift_pts = high_wp - low_wp if not pd.isna(low_wp) and not pd.isna(high_wp) else np.nan

    return {
        "entity_band": entity_band,
        "context": context,
        "context_value": context_value,
        "valid_runners": int(len(valid)),
        "poor_negative_runners": int(len(low)),
        "poor_negative_win_pct": round(low_wp, 2) if not pd.isna(low_wp) else "",
        "positive_elite_runners": int(len(high)),
        "positive_elite_win_pct": round(high_wp, 2) if not pd.isna(high_wp) else "",
        "lift_pts": round(lift_pts, 2) if not pd.isna(lift_pts) else "",
    }


def verdict(row):
    try:
        n = int(row["valid_runners"])
        l = float(row["lift_pts"])
    except Exception:
        return "INSUFFICIENT_DATA"

    if n < 1000:
        return "INSUFFICIENT_DATA"
    if l >= 5:
        return "STRONG_INDEPENDENT_DIRECTIONAL_SIGNAL"
    if l >= 3:
        return "DIRECTIONAL_SIGNAL"
    if l >= 1:
        return "WEAK_SIGNAL"
    return "NO_CLEAR_SIGNAL"


def main():
    if not HIST.exists():
        raise FileNotFoundError(f"Missing canonical history. Run build_edgeiq_trainer_jockey_canonicalisation_v1.py first: {HIST}")

    hist = pd.read_csv(HIST, low_memory=False)
    model = pd.read_csv(MODEL, low_memory=False)

    hist["finish_position_num"] = num(hist["finish_position_v1"])
    hist = hist[hist["finish_position_num"].notna()].copy()

    hist["hist_join_key"] = make_join_key(hist, "meeting_date", "track", "race_no", "horse")
    model["model_join_key"] = make_join_key(model, "meeting_date", "track", "race_no", "horse")

    model_keep = model[[
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
    ]].drop_duplicates("model_join_key")

    df = hist.merge(model_keep, left_on="hist_join_key", right_on="model_join_key", how="inner", validate="one_to_one")

    df["won"] = num(df["won"]).fillna(0).astype(int)
    df["placed"] = num(df["placed"]).fillna(0).astype(int)
    df["horse_key_join"] = df["horse_key"].map(key)
    df["race_key_join"] = df["meeting_date"].astype(str) + "|" + df["track"].map(key) + "|R" + df["race_no"].astype(str)

    trainer_q = build_quality(df, "trainer_canonical_key", "trainer_canonical", "TRAINER")
    jockey_q = build_quality(df, "jockey_canonical_key", "jockey_canonical", "JOCKEY")
    combo_q = build_quality(df, "trainer_jockey_canonical_key", "trainer_jockey_canonical", "COMBO")

    trainer_q.to_csv(OUT_TRAINER_QUALITY, index=False)
    jockey_q.to_csv(OUT_JOCKEY_QUALITY, index=False)
    combo_q.to_csv(OUT_COMBO_QUALITY, index=False)

    trainer_map = trainer_q[["trainer_canonical_key", "starts", "wins"]].rename(columns={"starts": "trainer_starts", "wins": "trainer_wins"})
    jockey_map = jockey_q[["jockey_canonical_key", "starts", "wins"]].rename(columns={"starts": "jockey_starts", "wins": "jockey_wins"})
    combo_map = combo_q[["trainer_jockey_canonical_key", "starts", "wins"]].rename(columns={"starts": "combo_starts", "wins": "combo_wins"})

    df = df.merge(trainer_map, on="trainer_canonical_key", how="left", validate="many_to_one")
    df = df.merge(jockey_map, on="jockey_canonical_key", how="left", validate="many_to_one")
    df = df.merge(combo_map, on="trainer_jockey_canonical_key", how="left", validate="many_to_one")

    df["trainer_loo_starts"] = num(df["trainer_starts"]).fillna(0) - 1
    df["trainer_loo_wins"] = num(df["trainer_wins"]).fillna(0) - df["won"]
    df["trainer_loo_win_pct"] = np.where(df["trainer_loo_starts"] > 0, df["trainer_loo_wins"] / df["trainer_loo_starts"] * 100, np.nan)

    df["jockey_loo_starts"] = num(df["jockey_starts"]).fillna(0) - 1
    df["jockey_loo_wins"] = num(df["jockey_wins"]).fillna(0) - df["won"]
    df["jockey_loo_win_pct"] = np.where(df["jockey_loo_starts"] > 0, df["jockey_loo_wins"] / df["jockey_loo_starts"] * 100, np.nan)

    df["combo_loo_starts"] = num(df["combo_starts"]).fillna(0) - 1
    df["combo_loo_wins"] = num(df["combo_wins"]).fillna(0) - df["won"]
    df["combo_loo_win_pct"] = np.where(df["combo_loo_starts"] > 0, df["combo_loo_wins"] / df["combo_loo_starts"] * 100, np.nan)

    df["trainer_edge_band_v3"] = [edge_band(r, s, "TRAINER") for r, s in zip(df["trainer_loo_win_pct"], df["trainer_loo_starts"])]
    df["jockey_edge_band_v3"] = [edge_band(r, s, "JOCKEY") for r, s in zip(df["jockey_loo_win_pct"], df["jockey_loo_starts"])]
    df["combo_edge_band_v3"] = [edge_band(r, s, "COMBO") for r, s in zip(df["combo_loo_win_pct"], df["combo_loo_starts"])]

    df["rank_bucket_v3"] = num(df["runner_rank"]).map(rank_bucket)
    df["trust_profile_v1"] = df["trust_profile_v1"].map(norm)
    df["race_reliability_band_v1"] = df["race_reliability_band_v1"].map(norm)
    df["dominance_band_v1"] = df["dominance_band_v1"].map(norm)
    df["score_share_band_v1"] = df["score_share_band_v1"].map(norm)

    entity_cols = ["trainer_edge_band_v3", "jockey_edge_band_v3", "combo_edge_band_v3"]

    rows = []
    for e in entity_cols:
        rows.append(lift(df, e))
        for rb in ["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS"]:
            rows.append(lift(df, e, "rank_bucket_v3", rb))
        for rr in ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]:
            rows.append(lift(df, e, "race_reliability_band_v1", rr))

    summary = pd.DataFrame(rows)
    summary["verdict"] = summary.apply(verdict, axis=1)

    pd.concat([agg(df, ["rank_bucket_v3", e], e) for e in entity_cols], ignore_index=True).to_csv(OUT_BY_RANK, index=False)
    pd.concat([agg(df, ["trust_profile_v1", e], e) for e in entity_cols], ignore_index=True).to_csv(OUT_BY_TRUST, index=False)
    pd.concat([agg(df, ["race_reliability_band_v1", e], e) for e in entity_cols], ignore_index=True).to_csv(OUT_BY_RELIABILITY, index=False)
    pd.concat([agg(df, ["dominance_band_v1", e], e) for e in entity_cols], ignore_index=True).to_csv(OUT_BY_DOMINANCE, index=False)
    pd.concat([agg(df, ["score_share_band_v1", e], e) for e in entity_cols], ignore_index=True).to_csv(OUT_BY_SCORE_SHARE, index=False)

    df.to_csv(OUT_RUNNER, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    join_integrity = "PASS" if len(hist) == len(model) == len(df) else "FAIL"

    OUT_JSON.write_text(json.dumps({
        "status": "COMPLETE",
        "history_rows": int(len(hist)),
        "model_rows": int(len(model)),
        "matched_rows": int(len(df)),
        "join_integrity": join_integrity,
        "trainer_quality_rows": int(len(trainer_q)),
        "jockey_quality_rows": int(len(jockey_q)),
        "combo_quality_rows": int(len(combo_q)),
        "important_note": "Canonical trainer/jockey V3.1. Validated one-to-one model join and many-to-one entity joins. No SP, no A/E, no ROI, no execution change.",
    }, indent=2), encoding="utf-8")

    print("[TRAINER_JOCKEY_EDGE_AUDIT_V3_1] COMPLETE")
    print(f"history_rows={len(hist)}")
    print(f"model_rows={len(model)}")
    print(f"matched_rows={len(df)}")
    print(f"join_integrity={join_integrity}")
    print("")
    print(summary[summary["context"].eq("OVERALL")].to_string(index=False))


if __name__ == "__main__":
    main()
