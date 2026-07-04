from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_HISTORY = DATA / "edgeiq_trainer_jockey_runner_history_v1.csv"
TRAINER_QUALITY = DATA / "edgeiq_trainer_quality_audit_v1.csv"
JOCKEY_QUALITY = DATA / "edgeiq_jockey_quality_audit_v1.csv"
COMBO_QUALITY = DATA / "edgeiq_trainer_jockey_combo_quality_audit_v1.csv"

OUT_RUNNER = DATA / "edgeiq_trainer_jockey_edge_runner_dataset_v1.csv"
OUT_ENTITY = DATA / "edgeiq_trainer_jockey_edge_entity_bands_v1.csv"
OUT_RANK = DATA / "edgeiq_trainer_jockey_edge_by_rank_bucket_v1.csv"
OUT_TRUST = DATA / "edgeiq_trainer_jockey_edge_by_trust_bucket_v1.csv"
OUT_RELIABILITY = DATA / "edgeiq_trainer_jockey_edge_by_reliability_band_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_trainer_jockey_edge_audit_summary_v1.csv"
OUT_AUDIT = DATA / "edgeiq_trainer_jockey_edge_audit_v1.json"


MODEL_CANDIDATES = [
    DATA / "edgeiq_environment_score_replay_v1.csv",
    DATA / "edgeiq_race_reliability_v1.csv",
    DATA / "edgeiq_environment_v2_trust_field_core.csv",
    DATA / "edgeiq_rank1_failure_audit_v1.csv",
]


def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()


def key_clean(x):
    return norm(x).replace(" ", "").replace("-", "").replace("_", "")


def num(s):
    return pd.to_numeric(s, errors="coerce")


def find_col(df, candidates):
    lower = {c.lower(): c for c in df.columns}
    compact = {key_clean(c): c for c in df.columns}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
        if key_clean(c) in compact:
            return compact[key_clean(c)]
    return None


def make_race_key(df, date_col, track_col, race_no_col):
    date = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    track = df[track_col].map(key_clean)
    race_no = df[race_no_col].astype(str).str.extract(r"(\d+)")[0].fillna("")
    return date + "|" + track + "|R" + race_no


def bucket_rank(x):
    if pd.isna(x):
        return "UNKNOWN_RANK"
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


def band_from_rate(rate, starts, entity_type):
    if pd.isna(rate) or starts <= 0:
        return "UNKNOWN"

    if entity_type == "COMBO":
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


def agg_edge(df, group_cols, label):
    g = (
        df.groupby(group_cols, dropna=False)
        .agg(
            runners=("won_v1_num", "size"),
            wins=("won_v1_num", "sum"),
            places=("placed_v1_num", "sum"),
            races=("race_key_v1", "nunique"),
            horses=("horse_key", "nunique"),
        )
        .reset_index()
    )
    g["win_pct"] = np.where(g["runners"] > 0, g["wins"] / g["runners"] * 100, 0).round(2)
    g["place_pct"] = np.where(g["runners"] > 0, g["places"] / g["runners"] * 100, 0).round(2)
    g["audit_view"] = label
    return g.sort_values(group_cols + ["runners"])


def load_model_context():
    found = []

    for f in MODEL_CANDIDATES:
        if not f.exists():
            continue

        try:
            head = pd.read_csv(f, nrows=5, low_memory=False)
        except Exception:
            continue

        date_col = find_col(head, ["meeting_date", "race_date", "date"])
        track_col = find_col(head, ["track", "venue", "meeting_name"])
        race_no_col = find_col(head, ["race_no", "raceNumber", "race_number"])
        horse_col = find_col(head, ["horse_key", "horse", "horseName", "horse_name"])

        if not date_col or not track_col or not race_no_col:
            continue

        full = pd.read_csv(f, low_memory=False)

        date_col = find_col(full, ["meeting_date", "race_date", "date"])
        track_col = find_col(full, ["track", "venue", "meeting_name"])
        race_no_col = find_col(full, ["race_no", "raceNumber", "race_number"])
        horse_col = find_col(full, ["horse_key", "horse", "horseName", "horse_name"])

        full["join_race_key"] = make_race_key(full, date_col, track_col, race_no_col)

        if horse_col:
            full["join_horse_key"] = full[horse_col].map(key_clean)
        else:
            full["join_horse_key"] = ""

        rank_col = find_col(full, [
            "rank",
            "model_rank",
            "runner_rank",
            "selection_rank",
            "score_rank",
            "rank_v1",
            "edgeiq_rank",
        ])

        trust_col = find_col(full, [
            "trust",
            "trust_band",
            "trust_profile",
            "model_trust",
            "trust_profile_v1",
            "edgeiq_trust",
        ])

        score_share_col = find_col(full, [
            "score_share",
            "score_share_v1",
            "dominance_share",
            "model_score_share",
        ])

        dominance_col = find_col(full, [
            "dominance",
            "dominance_score",
            "dominance_score_v1",
            "model_dominance",
        ])

        reliability_col = find_col(full, [
            "race_reliability_band_v1",
            "environment_band_v2",
            "environment_band_v1",
            "race_reliability_band",
        ])

        keep = ["join_race_key", "join_horse_key"]
        rename = {}

        if rank_col:
            keep.append(rank_col)
            rename[rank_col] = "model_rank_context"
        if trust_col:
            keep.append(trust_col)
            rename[trust_col] = "trust_context"
        if score_share_col:
            keep.append(score_share_col)
            rename[score_share_col] = "score_share_context"
        if dominance_col:
            keep.append(dominance_col)
            rename[dominance_col] = "dominance_context"
        if reliability_col:
            keep.append(reliability_col)
            rename[reliability_col] = "race_reliability_context"

        out = full[keep].drop_duplicates().rename(columns=rename)

        found.append({
            "file": str(f),
            "rows": int(len(out)),
            "has_horse_key": bool(horse_col),
            "rank_col": rank_col or "",
            "trust_col": trust_col or "",
            "score_share_col": score_share_col or "",
            "dominance_col": dominance_col or "",
            "reliability_col": reliability_col or "",
            "data": out,
        })

    if not found:
        return None, []

    # Prefer the richest horse-level file.
    found = sorted(
        found,
        key=lambda x: (
            bool(x["rank_col"]),
            bool(x["trust_col"]),
            bool(x["score_share_col"]),
            bool(x["dominance_col"]),
            x["has_horse_key"],
            x["rows"],
        ),
        reverse=True,
    )

    return found[0]["data"], [{k: v for k, v in item.items() if k != "data"} for item in found]


def main():
    for f in [RUNNER_HISTORY, TRAINER_QUALITY, JOCKEY_QUALITY, COMBO_QUALITY]:
        if not f.exists():
            raise FileNotFoundError(f"Missing required input: {f}")

    hist = pd.read_csv(RUNNER_HISTORY, low_memory=False)

    hist["finish_position_num"] = num(hist["finish_position_v1"])
    hist = hist[hist["finish_position_num"].notna()].copy()

    hist["won_v1_num"] = num(hist["won_v1"]).fillna(0).astype(int)
    hist["placed_v1_num"] = num(hist["placed_v1"]).fillna(0).astype(int)
    hist["trainer_norm"] = hist["trainer"].map(norm)
    hist["jockey_norm"] = hist["jockey"].map(norm)
    hist["trainer_key_norm"] = hist["trainer_key"].map(norm)
    hist["jockey_key_norm"] = hist["jockey_key"].map(norm)
    hist["horse_key"] = hist["horse_key"].map(key_clean)
    hist["race_key_v1"] = hist["race_key_v1"].map(norm)
    hist["join_race_key"] = hist["race_key_v1"]
    hist["join_horse_key"] = hist["horse_key"]
    hist["trainer_jockey_combo"] = hist["trainer_norm"] + " + " + hist["jockey_norm"]

    trainer = pd.read_csv(TRAINER_QUALITY, low_memory=False)
    jockey = pd.read_csv(JOCKEY_QUALITY, low_memory=False)
    combo = pd.read_csv(COMBO_QUALITY, low_memory=False)

    trainer["trainer_key_norm"] = trainer["trainer_key_norm"].map(norm)
    jockey["jockey_key_norm"] = jockey["jockey_key_norm"].map(norm)
    combo["trainer_key_norm"] = combo["trainer_key_norm"].map(norm)
    combo["jockey_key_norm"] = combo["jockey_key_norm"].map(norm)

    trainer_small = trainer[["trainer_key_norm", "starts", "wins", "places", "win_pct", "place_pct"]].rename(
        columns={
            "starts": "trainer_total_starts",
            "wins": "trainer_total_wins",
            "places": "trainer_total_places",
            "win_pct": "trainer_raw_win_pct",
            "place_pct": "trainer_raw_place_pct",
        }
    )

    jockey_small = jockey[["jockey_key_norm", "starts", "wins", "places", "win_pct", "place_pct"]].rename(
        columns={
            "starts": "jockey_total_starts",
            "wins": "jockey_total_wins",
            "places": "jockey_total_places",
            "win_pct": "jockey_raw_win_pct",
            "place_pct": "jockey_raw_place_pct",
        }
    )

    combo_small = combo[["trainer_key_norm", "jockey_key_norm", "starts", "wins", "places", "win_pct", "place_pct"]].rename(
        columns={
            "starts": "combo_total_starts",
            "wins": "combo_total_wins",
            "places": "combo_total_places",
            "win_pct": "combo_raw_win_pct",
            "place_pct": "combo_raw_place_pct",
        }
    )

    df = hist.merge(trainer_small, on="trainer_key_norm", how="left")
    df = df.merge(jockey_small, on="jockey_key_norm", how="left")
    df = df.merge(combo_small, on=["trainer_key_norm", "jockey_key_norm"], how="left")

    # Leave-one-out rates so the current result does not inflate its own trainer/jockey band.
    df["trainer_loo_starts"] = num(df["trainer_total_starts"]).fillna(0) - 1
    df["trainer_loo_wins"] = num(df["trainer_total_wins"]).fillna(0) - df["won_v1_num"]
    df["trainer_loo_win_pct"] = np.where(
        df["trainer_loo_starts"] > 0,
        df["trainer_loo_wins"] / df["trainer_loo_starts"] * 100,
        np.nan,
    )

    df["jockey_loo_starts"] = num(df["jockey_total_starts"]).fillna(0) - 1
    df["jockey_loo_wins"] = num(df["jockey_total_wins"]).fillna(0) - df["won_v1_num"]
    df["jockey_loo_win_pct"] = np.where(
        df["jockey_loo_starts"] > 0,
        df["jockey_loo_wins"] / df["jockey_loo_starts"] * 100,
        np.nan,
    )

    df["combo_loo_starts"] = num(df["combo_total_starts"]).fillna(0) - 1
    df["combo_loo_wins"] = num(df["combo_total_wins"]).fillna(0) - df["won_v1_num"]
    df["combo_loo_win_pct"] = np.where(
        df["combo_loo_starts"] > 0,
        df["combo_loo_wins"] / df["combo_loo_starts"] * 100,
        np.nan,
    )

    df["trainer_edge_band_v1"] = [
        band_from_rate(r, s, "TRAINER")
        for r, s in zip(df["trainer_loo_win_pct"], df["trainer_loo_starts"])
    ]
    df["jockey_edge_band_v1"] = [
        band_from_rate(r, s, "JOCKEY")
        for r, s in zip(df["jockey_loo_win_pct"], df["jockey_loo_starts"])
    ]
    df["combo_edge_band_v1"] = [
        band_from_rate(r, s, "COMBO")
        for r, s in zip(df["combo_loo_win_pct"], df["combo_loo_starts"])
    ]

    model_context, model_audit = load_model_context()

    model_file_used = ""
    if model_context is not None:
        model_file_used = model_audit[0]["file"]

        horse_level = model_context[model_context["join_horse_key"].astype(str).str.len() > 0].copy()
        race_level = model_context[model_context["join_horse_key"].astype(str).str.len() == 0].copy()

        if len(horse_level):
            df = df.merge(horse_level, on=["join_race_key", "join_horse_key"], how="left")
        if len(race_level):
            race_level = race_level.drop(columns=["join_horse_key"], errors="ignore").drop_duplicates("join_race_key")
            df = df.merge(race_level, on="join_race_key", how="left", suffixes=("", "_race"))

    if "model_rank_context" not in df.columns:
        df["model_rank_context"] = np.nan
    if "trust_context" not in df.columns:
        df["trust_context"] = "UNKNOWN_TRUST"
    if "race_reliability_context" not in df.columns:
        df["race_reliability_context"] = "UNKNOWN_RELIABILITY"

    df["model_rank_context"] = num(df["model_rank_context"])
    df["rank_bucket_v1"] = df["model_rank_context"].map(bucket_rank)
    df["trust_bucket_v1"] = df["trust_context"].fillna("UNKNOWN_TRUST").map(norm)
    df["race_reliability_band_context"] = df["race_reliability_context"].fillna("UNKNOWN_RELIABILITY").map(norm)

    entity_views = []

    for entity_band in ["trainer_edge_band_v1", "jockey_edge_band_v1", "combo_edge_band_v1"]:
        tmp = agg_edge(df, [entity_band], entity_band)
        entity_views.append(tmp)

    entity_out = pd.concat(entity_views, ignore_index=True)

    rank_views = []
    for entity_band in ["trainer_edge_band_v1", "jockey_edge_band_v1", "combo_edge_band_v1"]:
        rank_views.append(agg_edge(df, ["rank_bucket_v1", entity_band], entity_band))

    rank_out = pd.concat(rank_views, ignore_index=True)

    trust_views = []
    for entity_band in ["trainer_edge_band_v1", "jockey_edge_band_v1", "combo_edge_band_v1"]:
        trust_views.append(agg_edge(df, ["trust_bucket_v1", entity_band], entity_band))

    trust_out = pd.concat(trust_views, ignore_index=True)

    reliability_views = []
    for entity_band in ["trainer_edge_band_v1", "jockey_edge_band_v1", "combo_edge_band_v1"]:
        reliability_views.append(agg_edge(df, ["race_reliability_band_context", entity_band], entity_band))

    reliability_out = pd.concat(reliability_views, ignore_index=True)

    def lift_for(entity_col):
        valid = df[df[entity_col].isin(["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"])].copy()
        low = valid[valid[entity_col].isin(["POOR", "NEGATIVE"])]
        high = valid[valid[entity_col].isin(["POSITIVE", "ELITE"])]
        low_wp = low["won_v1_num"].mean() * 100 if len(low) else np.nan
        high_wp = high["won_v1_num"].mean() * 100 if len(high) else np.nan
        return len(valid), len(low), round(low_wp, 2) if not pd.isna(low_wp) else "", len(high), round(high_wp, 2) if not pd.isna(high_wp) else "", round(high_wp - low_wp, 2) if not pd.isna(high_wp) and not pd.isna(low_wp) else ""

    summary_rows = []
    for col in ["trainer_edge_band_v1", "jockey_edge_band_v1", "combo_edge_band_v1"]:
        valid_n, low_n, low_wp, high_n, high_wp, lift = lift_for(col)
        summary_rows.append([col, valid_n, low_n, low_wp, high_n, high_wp, lift])

    summary = pd.DataFrame(
        summary_rows,
        columns=[
            "entity_band",
            "valid_runners",
            "poor_negative_runners",
            "poor_negative_win_pct",
            "positive_elite_runners",
            "positive_elite_win_pct",
            "raw_lift_pts",
        ],
    )

    # Add verdicts conservatively. This is not integration approval.
    def verdict(row):
        try:
            lift = float(row["raw_lift_pts"])
            n = int(row["valid_runners"])
        except Exception:
            return "INSUFFICIENT_DATA"

        if n < 5000:
            return "INSUFFICIENT_DATA"
        if lift >= 3:
            return "DIRECTIONAL_SIGNAL_NEEDS_INDEPENDENCE_REVIEW"
        if lift >= 1:
            return "WEAK_DIRECTIONAL_SIGNAL"
        return "NO_CLEAR_RAW_SIGNAL"

    summary["verdict"] = summary.apply(verdict, axis=1)

    keep_runner_cols = [
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "trainer",
        "jockey",
        "finish_position_v1",
        "won_v1_num",
        "placed_v1_num",
        "race_key_v1",
        "model_rank_context",
        "rank_bucket_v1",
        "trust_bucket_v1",
        "race_reliability_band_context",
        "trainer_loo_starts",
        "trainer_loo_win_pct",
        "trainer_edge_band_v1",
        "jockey_loo_starts",
        "jockey_loo_win_pct",
        "jockey_edge_band_v1",
        "combo_loo_starts",
        "combo_loo_win_pct",
        "combo_edge_band_v1",
    ]

    for c in keep_runner_cols:
        if c not in df.columns:
            df[c] = ""

    df[keep_runner_cols].to_csv(OUT_RUNNER, index=False)
    entity_out.to_csv(OUT_ENTITY, index=False)
    rank_out.to_csv(OUT_RANK, index=False)
    trust_out.to_csv(OUT_TRUST, index=False)
    reliability_out.to_csv(OUT_RELIABILITY, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    audit = {
        "status": "COMPLETE",
        "runner_rows": int(len(df)),
        "model_file_used": model_file_used,
        "model_sources_considered": model_audit,
        "outputs": {
            "runner_dataset": str(OUT_RUNNER),
            "entity_bands": str(OUT_ENTITY),
            "rank_bucket": str(OUT_RANK),
            "trust_bucket": str(OUT_TRUST),
            "reliability_band": str(OUT_RELIABILITY),
            "summary": str(OUT_SUMMARY),
        },
        "important_note": "This is a win-rate independence-style audit only. No Racing.com SP, no A/E, no ROI, no execution changes.",
    }

    OUT_AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print("[TRAINER_JOCKEY_EDGE_AUDIT_V1] COMPLETE")
    print(f"runner_rows={len(df)}")
    print(f"model_file_used={model_file_used}")
    print(f"wrote={OUT_SUMMARY}")
    print("")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
