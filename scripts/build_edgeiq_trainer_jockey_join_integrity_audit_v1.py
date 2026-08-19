from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST = DATA / "edgeiq_trainer_jockey_runner_history_v1.csv"
MODEL = DATA / "edgeiq_race_reliability_replay_v1.csv"

OUT_DUP_HIST = DATA / "edgeiq_trainer_jockey_join_integrity_hist_duplicates_v1.csv"
OUT_DUP_MODEL = DATA / "edgeiq_trainer_jockey_join_integrity_model_duplicates_v1.csv"
OUT_UNMATCHED_HIST = DATA / "edgeiq_trainer_jockey_join_integrity_unmatched_hist_v1.csv"
OUT_UNMATCHED_MODEL = DATA / "edgeiq_trainer_jockey_join_integrity_unmatched_model_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_trainer_jockey_join_integrity_summary_v1.csv"
OUT_JSON = DATA / "edgeiq_trainer_jockey_join_integrity_audit_v1.json"


def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()


def key(x):
    return norm(x).replace(" ", "").replace("-", "").replace("_", "").replace("'", "")


def make_join_key(df, date_col, track_col, race_col, horse_col):
    d = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    t = df[track_col].map(key)
    r = df[race_col].astype(str).str.extract(r"(\d+)")[0].fillna("")
    h = df[horse_col].map(key)
    return d + "|" + t + "|R" + r + "|" + h


def main():
    hist = pd.read_csv(HIST, low_memory=False)
    model = pd.read_csv(MODEL, low_memory=False)

    hist["finish_position_num"] = pd.to_numeric(hist["finish_position_v1"], errors="coerce")
    hist = hist[hist["finish_position_num"].notna()].copy()

    hist["join_key"] = make_join_key(hist, "meeting_date", "track", "race_no", "horse")
    model["join_key"] = make_join_key(model, "meeting_date", "track", "race_no", "horse")

    hist_dup = (
        hist.groupby("join_key")
        .size()
        .reset_index(name="hist_count")
        .query("hist_count > 1")
        .sort_values("hist_count", ascending=False)
    )

    model_dup = (
        model.groupby("join_key")
        .size()
        .reset_index(name="model_count")
        .query("model_count > 1")
        .sort_values("model_count", ascending=False)
    )

    hist_keys = set(hist["join_key"])
    model_keys = set(model["join_key"])

    unmatched_hist = hist[~hist["join_key"].isin(model_keys)].copy()
    unmatched_model = model[~model["join_key"].isin(hist_keys)].copy()

    joined = hist[["join_key"]].merge(model[["join_key"]], on="join_key", how="inner")

    summary = pd.DataFrame(
        [
            ["hist_rows", len(hist)],
            ["model_rows", len(model)],
            ["hist_unique_join_keys", hist["join_key"].nunique()],
            ["model_unique_join_keys", model["join_key"].nunique()],
            ["hist_duplicate_keys", len(hist_dup)],
            ["model_duplicate_keys", len(model_dup)],
            ["inner_join_rows", len(joined)],
            ["expected_clean_join_rows", min(hist["join_key"].nunique(), model["join_key"].nunique())],
            ["unmatched_hist_rows", len(unmatched_hist)],
            ["unmatched_model_rows", len(unmatched_model)],
            ["join_inflation_rows", len(joined) - len(hist)],
            ["join_integrity_verdict", "PASS" if len(joined) == len(hist) == len(model) and len(hist_dup) == 0 and len(model_dup) == 0 else "FAIL_DUPLICATES_OR_MISMATCH"],
        ],
        columns=["metric", "value"],
    )

    hist_dup.to_csv(OUT_DUP_HIST, index=False)
    model_dup.to_csv(OUT_DUP_MODEL, index=False)
    unmatched_hist.to_csv(OUT_UNMATCHED_HIST, index=False)
    unmatched_model.to_csv(OUT_UNMATCHED_MODEL, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    OUT_JSON.write_text(json.dumps({
        "status": "COMPLETE",
        "hist_rows": int(len(hist)),
        "model_rows": int(len(model)),
        "inner_join_rows": int(len(joined)),
        "hist_duplicate_keys": int(len(hist_dup)),
        "model_duplicate_keys": int(len(model_dup)),
        "unmatched_hist_rows": int(len(unmatched_hist)),
        "unmatched_model_rows": int(len(unmatched_model)),
        "verdict": str(summary.loc[summary["metric"].eq("join_integrity_verdict"), "value"].iloc[0]),
    }, indent=2), encoding="utf-8")

    print("[TRAINER_JOCKEY_JOIN_INTEGRITY_AUDIT_V1] COMPLETE")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
