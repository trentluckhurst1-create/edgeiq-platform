from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER = DATA / "edgeiq_trainer_jockey_factor_runner_v1.csv"

OUT_DETAIL = DATA / "edgeiq_trainer_jockey_rank1_failure_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_trainer_jockey_rank1_failure_audit_summary_v1.csv"
OUT_BY_REASON = DATA / "edgeiq_trainer_jockey_rank1_failure_audit_by_reason_v1.csv"
OUT_JSON = DATA / "edgeiq_trainer_jockey_rank1_failure_audit_v1.json"

BAND_SCORE = {
    "POOR": -2,
    "NEGATIVE": -1,
    "NEUTRAL": 0,
    "LOW_SAMPLE": 0,
    "UNKNOWN": 0,
    "POSITIVE": 1,
    "ELITE": 2,
}


def num(s):
    return pd.to_numeric(s, errors="coerce")


def score_band(x):
    return BAND_SCORE.get(str(x).strip().upper(), 0)


def main():
    if not RUNNER.exists():
        raise FileNotFoundError(f"Missing input. Factor V1 did not build: {RUNNER}")

    df = pd.read_csv(RUNNER, low_memory=False)
    df["runner_rank_num"] = num(df["runner_rank"])
    df["won"] = num(df["won"]).fillna(0).astype(int)

    rows = []

    for _, race in df.groupby(["meeting_date", "track", "race_no"], dropna=False):
        rank1 = race[race["runner_rank_num"] == 1].copy()
        winner = race[race["won"] == 1].copy()

        if len(rank1) != 1 or len(winner) != 1:
            continue

        r1 = rank1.iloc[0]
        win = winner.iloc[0]

        r1_won = int(r1["won"]) == 1

        trainer_delta = score_band(win.get("trainer_factor_band_v1")) - score_band(r1.get("trainer_factor_band_v1"))
        jockey_delta = score_band(win.get("jockey_factor_band_v1")) - score_band(r1.get("jockey_factor_band_v1"))
        combo_delta = score_band(win.get("combo_factor_band_v1")) - score_band(r1.get("combo_factor_band_v1"))
        blend_delta = float(win.get("trainer_jockey_blend_score_v1", 0)) - float(r1.get("trainer_jockey_blend_score_v1", 0))

        if r1_won:
            reason = "RANK1_WON"
        elif trainer_delta > 0 and jockey_delta > 0 and combo_delta > 0:
            reason = "WINNER_BETTER_ALL_THREE"
        elif jockey_delta > 0 and trainer_delta > 0:
            reason = "WINNER_BETTER_TRAINER_AND_JOCKEY"
        elif jockey_delta > 0:
            reason = "WINNER_BETTER_JOCKEY"
        elif trainer_delta > 0:
            reason = "WINNER_BETTER_TRAINER"
        elif combo_delta > 0:
            reason = "WINNER_BETTER_COMBO"
        elif blend_delta > 0:
            reason = "WINNER_BETTER_BLEND_ONLY"
        else:
            reason = "TRAINER_JOCKEY_NOT_EXPLANATORY"

        rows.append({
            "meeting_date": r1["meeting_date"],
            "track": r1["track"],
            "race_no": r1["race_no"],
            "rank1_horse": r1["horse"],
            "rank1_won": int(r1_won),
            "winner_horse": win["horse"],
            "winner_rank": win["runner_rank"],
            "rank1_trainer_band": r1.get("trainer_factor_band_v1"),
            "winner_trainer_band": win.get("trainer_factor_band_v1"),
            "rank1_jockey_band": r1.get("jockey_factor_band_v1"),
            "winner_jockey_band": win.get("jockey_factor_band_v1"),
            "rank1_combo_band": r1.get("combo_factor_band_v1"),
            "winner_combo_band": win.get("combo_factor_band_v1"),
            "rank1_blend_score": r1.get("trainer_jockey_blend_score_v1"),
            "winner_blend_score": win.get("trainer_jockey_blend_score_v1"),
            "trainer_delta": trainer_delta,
            "jockey_delta": jockey_delta,
            "combo_delta": combo_delta,
            "blend_delta": round(blend_delta, 3),
            "failure_reason_tj_v1": reason,
        })

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DETAIL, index=False)

    total = len(out)
    rank1_wins = int(out["rank1_won"].sum()) if total else 0
    rank1_losses = total - rank1_wins
    losses = out[out["rank1_won"] == 0].copy()

    better_trainer = int((losses["trainer_delta"] > 0).sum()) if len(losses) else 0
    better_jockey = int((losses["jockey_delta"] > 0).sum()) if len(losses) else 0
    better_combo = int((losses["combo_delta"] > 0).sum()) if len(losses) else 0
    better_blend = int((losses["blend_delta"] > 0).sum()) if len(losses) else 0

    summary = pd.DataFrame([
        ["races_audited", total],
        ["rank1_wins", rank1_wins],
        ["rank1_losses", rank1_losses],
        ["rank1_win_pct", round(rank1_wins / total * 100, 2) if total else 0],
        ["losses_winner_better_trainer", better_trainer],
        ["losses_winner_better_trainer_pct", round(better_trainer / rank1_losses * 100, 2) if rank1_losses else 0],
        ["losses_winner_better_jockey", better_jockey],
        ["losses_winner_better_jockey_pct", round(better_jockey / rank1_losses * 100, 2) if rank1_losses else 0],
        ["losses_winner_better_combo", better_combo],
        ["losses_winner_better_combo_pct", round(better_combo / rank1_losses * 100, 2) if rank1_losses else 0],
        ["losses_winner_better_blend", better_blend],
        ["losses_winner_better_blend_pct", round(better_blend / rank1_losses * 100, 2) if rank1_losses else 0],
        ["important_note", "Observation only. No fair price, no execution, no SP."],
    ], columns=["metric", "value"])
    summary.to_csv(OUT_SUMMARY, index=False)

    by_reason = (
        out.groupby("failure_reason_tj_v1", dropna=False)
        .agg(races=("rank1_won", "size"), rank1_wins=("rank1_won", "sum"))
        .reset_index()
        .sort_values("races", ascending=False)
    )
    by_reason["pct_of_all_races"] = np.where(total > 0, by_reason["races"] / total * 100, 0).round(2)
    by_reason.to_csv(OUT_BY_REASON, index=False)

    OUT_JSON.write_text(json.dumps({
        "status": "COMPLETE",
        "races_audited": int(total),
        "rank1_wins": int(rank1_wins),
        "rank1_losses": int(rank1_losses),
        "rank1_win_pct": round(rank1_wins / total * 100, 2) if total else 0,
        "losses_winner_better_trainer_pct": round(better_trainer / rank1_losses * 100, 2) if rank1_losses else 0,
        "losses_winner_better_jockey_pct": round(better_jockey / rank1_losses * 100, 2) if rank1_losses else 0,
        "losses_winner_better_combo_pct": round(better_combo / rank1_losses * 100, 2) if rank1_losses else 0,
        "losses_winner_better_blend_pct": round(better_blend / rank1_losses * 100, 2) if rank1_losses else 0,
        "important_note": "Observation only. No fair price, no execution, no SP.",
    }, indent=2), encoding="utf-8")

    print("[TRAINER_JOCKEY_RANK1_FAILURE_AUDIT_V1] COMPLETE")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
