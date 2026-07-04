from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
TJ_V3 = DATA / "edgeiq_live_trainer_jockey_factor_feed_v3.csv"
TERMINAL = DATA / "edgeiq_live_terminal_feed_v1.csv"

OUT_DETAIL = DATA / "edgeiq_live_blank_jockey_v2.csv"
OUT_BY_TRACK = DATA / "edgeiq_live_blank_jockey_v2_by_track.csv"
OUT_BY_RACE = DATA / "edgeiq_live_blank_jockey_v2_by_race.csv"
OUT_SUMMARY = DATA / "edgeiq_live_blank_jockey_v2_summary.csv"
OUT_JSON = DATA / "edgeiq_live_blank_jockey_v2.json"


def blank(s):
    return s.isna() | (s.astype(str).str.strip() == "")


def safe_col(df, col):
    return df[col] if col in df.columns else ""


def main():
    if not LIVE_BOARD.exists():
        raise FileNotFoundError(f"Missing live board: {LIVE_BOARD}")

    live = pd.read_csv(LIVE_BOARD, low_memory=False)

    required = ["track", "race_no", "horse", "trainer", "jockey"]
    missing = [c for c in required if c not in live.columns]
    if missing:
        raise ValueError(f"Live board missing columns: {missing}")

    live_blank = live[blank(live["jockey"])].copy()

    if TJ_V3.exists():
        tj = pd.read_csv(TJ_V3, low_memory=False)
        join_cols = ["track", "race_no", "horse"]
        tj_keep = tj[[c for c in join_cols + [
            "trainer_factor_band_v1",
            "jockey_factor_band_v1",
            "combo_factor_band_v1",
            "trainer_jockey_blend_band_v3",
            "trainer_jockey_blend_score_v3",
            "tj_factor_verdict_v3",
        ] if c in tj.columns]].copy()

        live_blank = live_blank.merge(
            tj_keep.drop_duplicates(join_cols),
            on=join_cols,
            how="left",
        )

    terminal_blank_rows = ""
    terminal_total_rows = ""
    terminal_blank_vic_rows = ""

    if TERMINAL.exists():
        terminal = pd.read_csv(TERMINAL, low_memory=False)
        terminal_total_rows = len(terminal)
        if "jockey" in terminal.columns:
            terminal_blank_rows = int(blank(terminal["jockey"]).sum())
        if "state" in terminal.columns and "jockey" in terminal.columns:
            terminal_blank_vic_rows = int((blank(terminal["jockey"]) & (terminal["state"].astype(str).str.upper() == "VIC")).sum())

    live_blank.to_csv(OUT_DETAIL, index=False)

    by_track = (
        live.groupby("track", dropna=False)
        .agg(
            live_rows=("horse", "size"),
            blank_jockey_rows=("jockey", lambda s: int(blank(s).sum())),
        )
        .reset_index()
    )
    by_track["blank_jockey_pct"] = (by_track["blank_jockey_rows"] / by_track["live_rows"] * 100).round(2)
    by_track = by_track.sort_values(["blank_jockey_rows", "live_rows"], ascending=[False, False])
    by_track.to_csv(OUT_BY_TRACK, index=False)

    by_race = (
        live.groupby(["track", "race_no"], dropna=False)
        .agg(
            race_rows=("horse", "size"),
            blank_jockey_rows=("jockey", lambda s: int(blank(s).sum())),
            sample_blank_horses=("horse", lambda s: ""),
        )
        .reset_index()
    )

    samples = []
    for _, r in by_race.iterrows():
        sub = live[(live["track"].astype(str) == str(r["track"])) & (live["race_no"].astype(str) == str(r["race_no"]))]
        bh = sub[blank(sub["jockey"])]["horse"].astype(str).head(8).tolist()
        samples.append(" | ".join(bh))

    by_race["sample_blank_horses"] = samples
    by_race["blank_jockey_pct"] = (by_race["blank_jockey_rows"] / by_race["race_rows"] * 100).round(2)
    by_race = by_race.sort_values(["blank_jockey_rows", "track", "race_no"], ascending=[False, True, True])
    by_race.to_csv(OUT_BY_RACE, index=False)

    total = len(live)
    blank_count = len(live_blank)

    summary = pd.DataFrame([
        ["live_board_rows", total],
        ["live_blank_jockey_rows", blank_count],
        ["live_blank_jockey_pct", round(blank_count / total * 100, 2) if total else 0],
        ["tracks_with_blank_jockeys", int((by_track["blank_jockey_rows"] > 0).sum())],
        ["races_with_blank_jockeys", int((by_race["blank_jockey_rows"] > 0).sum())],
        ["terminal_feed_rows", terminal_total_rows],
        ["terminal_blank_jockey_rows", terminal_blank_rows],
        ["terminal_blank_jockey_vic_rows", terminal_blank_vic_rows],
        ["tj_v3_exists", "YES" if TJ_V3.exists() else "NO"],
        ["audit_only", "YES"],
        ["price_or_execution_changed", "NO"],
    ], columns=["metric", "value"])

    summary.to_csv(OUT_SUMMARY, index=False)

    OUT_JSON.write_text(json.dumps({
        "status": "COMPLETE",
        "live_board_rows": int(total),
        "live_blank_jockey_rows": int(blank_count),
        "live_blank_jockey_pct": round(blank_count / total * 100, 2) if total else 0,
        "tracks_with_blank_jockeys": int((by_track["blank_jockey_rows"] > 0).sum()),
        "races_with_blank_jockeys": int((by_race["blank_jockey_rows"] > 0).sum()),
        "terminal_feed_rows": terminal_total_rows,
        "terminal_blank_jockey_rows": terminal_blank_rows,
        "terminal_blank_jockey_vic_rows": terminal_blank_vic_rows,
        "outputs": {
            "detail": str(OUT_DETAIL),
            "by_track": str(OUT_BY_TRACK),
            "by_race": str(OUT_BY_RACE),
            "summary": str(OUT_SUMMARY),
        },
        "important_note": "Audit only. No fair price, no execution, no UI change.",
    }, indent=2), encoding="utf-8")

    print("[LIVE_BLANK_JOCKEY_AUDIT_V2] COMPLETE")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
