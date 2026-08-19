from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_TJ = DATA / "edgeiq_live_trainer_jockey_factor_feed_v1.csv"

OUT_TRAINER = DATA / "edgeiq_trainer_match_failures_v1.csv"
OUT_JOCKEY = DATA / "edgeiq_jockey_match_failures_v1.csv"
OUT_COMBO = DATA / "edgeiq_trainer_jockey_combo_match_failures_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_trainer_jockey_match_failures_summary_v1.csv"
OUT_JSON = DATA / "edgeiq_trainer_jockey_match_audit_v1.json"


def safe(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def fail_table(df, entity):
    if entity == "trainer":
        fail = df[df["trainer_factor_matched_v1"] != "YES"].copy()
        cols = ["trainer"]
        key = "trainer"
    elif entity == "jockey":
        fail = df[df["jockey_factor_matched_v1"] != "YES"].copy()
        cols = ["jockey"]
        key = "jockey"
    else:
        fail = df[df["combo_factor_matched_v1"] != "YES"].copy()
        cols = ["trainer", "jockey"]
        key = ["trainer", "jockey"]

    for c in cols:
        fail[c] = fail[c].map(safe)

    grouped = (
        fail.groupby(key, dropna=False)
        .agg(
            misses=("horse", "size"),
            tracks=("track", lambda s: "|".join(sorted(set(map(str, s))))),
            sample_horses=("horse", lambda s: " | ".join(list(map(str, s.head(5))))),
        )
        .reset_index()
        .sort_values("misses", ascending=False)
    )

    return grouped


def main():
    if not LIVE_TJ.exists():
        raise FileNotFoundError(f"Missing input: {LIVE_TJ}")

    df = pd.read_csv(LIVE_TJ, low_memory=False)

    required = [
        "track",
        "race_no",
        "horse",
        "trainer",
        "jockey",
        "trainer_factor_matched_v1",
        "jockey_factor_matched_v1",
        "combo_factor_matched_v1",
        "tj_factor_verdict_v1",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns from live TJ feed: {missing}")

    trainer_fail = fail_table(df, "trainer")
    jockey_fail = fail_table(df, "jockey")
    combo_fail = fail_table(df, "combo")

    trainer_fail.to_csv(OUT_TRAINER, index=False)
    jockey_fail.to_csv(OUT_JOCKEY, index=False)
    combo_fail.to_csv(OUT_COMBO, index=False)

    total = len(df)
    trainer_miss = int((df["trainer_factor_matched_v1"] != "YES").sum())
    jockey_miss = int((df["jockey_factor_matched_v1"] != "YES").sum())
    combo_miss = int((df["combo_factor_matched_v1"] != "YES").sum())
    complete = int((df["tj_factor_verdict_v1"] == "COMPLETE").sum())

    summary = pd.DataFrame([
        ["live_rows", total],
        ["trainer_matched", total - trainer_miss],
        ["trainer_unmatched", trainer_miss],
        ["trainer_match_pct", round((total - trainer_miss) / total * 100, 2) if total else 0],
        ["unique_unmatched_trainers", len(trainer_fail)],
        ["jockey_matched", total - jockey_miss],
        ["jockey_unmatched", jockey_miss],
        ["jockey_match_pct", round((total - jockey_miss) / total * 100, 2) if total else 0],
        ["unique_unmatched_jockeys", len(jockey_fail)],
        ["combo_matched", total - combo_miss],
        ["combo_unmatched", combo_miss],
        ["combo_match_pct", round((total - combo_miss) / total * 100, 2) if total else 0],
        ["unique_unmatched_combos", len(combo_fail)],
        ["complete_rows", complete],
        ["complete_pct", round(complete / total * 100, 2) if total else 0],
        ["observation_only", "YES"],
    ], columns=["metric", "value"])

    summary.to_csv(OUT_SUMMARY, index=False)

    OUT_JSON.write_text(json.dumps({
        "status": "COMPLETE",
        "live_rows": int(total),
        "trainer_unmatched": int(trainer_miss),
        "jockey_unmatched": int(jockey_miss),
        "combo_unmatched": int(combo_miss),
        "complete_rows": int(complete),
        "outputs": {
            "trainer_failures": str(OUT_TRAINER),
            "jockey_failures": str(OUT_JOCKEY),
            "combo_failures": str(OUT_COMBO),
            "summary": str(OUT_SUMMARY),
        },
        "important_note": "Match audit only. No fair price, no execution, no UI change.",
    }, indent=2), encoding="utf-8")

    print("[TRAINER_JOCKEY_MATCH_AUDIT_V1] COMPLETE")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
