from pathlib import Path
import pandas as pd

DATA = Path("./public/data")

DNA = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
BOARD = DATA / "edgeiq_live_runner_board_v1.csv"

BACKUP = DATA / "edgeiq_runner_dna_drawer_feed_v2_BEFORE_JOIN_KEY_FIX.csv"
SUMMARY = DATA / "edgeiq_runner_dna_drawer_feed_v2_join_key_fix_summary.csv"

dna = pd.read_csv(DNA, dtype=str).fillna("")
board = pd.read_csv(BOARD, dtype=str).fillna("")

dna.to_csv(BACKUP, index=False)

def norm_track(x):
    return str(x).strip()

def norm_race_no(x):
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s

def norm_horse(x):
    return str(x).strip().upper()

for df in [dna, board]:
    df["_join_track"] = df["track"].map(norm_track)
    df["_join_race_no"] = df["race_no"].map(norm_race_no)
    df["_join_horse"] = df["horse"].map(norm_horse)

keep_cols = [
    "_join_track",
    "_join_race_no",
    "_join_horse",
    "race_date",
    "race_key",
    "meeting_key",
    "runner_key",
    "join_key",
]

available = [c for c in keep_cols if c in board.columns]

board_small = board[available].drop_duplicates(
    subset=["_join_track", "_join_race_no", "_join_horse"]
)

merged = dna.merge(
    board_small,
    on=["_join_track", "_join_race_no", "_join_horse"],
    how="left",
    suffixes=("", "_board")
)

def set_from_board(col):
    board_col = f"{col}_board"
    if col not in merged.columns:
        merged[col] = ""
    if board_col in merged.columns:
        merged[col] = merged[col].where(
            merged[col].astype(str).str.strip() != "",
            merged[board_col]
        )

for c in ["race_date", "race_key", "meeting_key", "runner_key", "join_key"]:
    set_from_board(c)

# If join_key is still blank, use runner_key.
if "join_key" not in merged.columns:
    merged["join_key"] = ""
if "runner_key" in merged.columns:
    merged["join_key"] = merged["join_key"].where(
        merged["join_key"].astype(str).str.strip() != "",
        merged["runner_key"]
    )

drop_cols = [c for c in merged.columns if c.startswith("_join_") or c.endswith("_board")]
merged = merged.drop(columns=drop_cols)

merged.to_csv(DNA, index=False)

summary = pd.DataFrame([
    {"metric": "status", "value": "RUNNER_DNA_DRAWER_FEED_V2_JOIN_KEY_FIX_COMPLETE"},
    {"metric": "rows", "value": len(merged)},
    {"metric": "runner_key_populated", "value": int((merged.get("runner_key", "").astype(str).str.strip() != "").sum())},
    {"metric": "join_key_populated", "value": int((merged.get("join_key", "").astype(str).str.strip() != "").sum())},
    {"metric": "dna_score_populated", "value": int((merged.get("dna_v6_2_score", "").astype(str).str.strip() != "").sum())},
    {"metric": "positive_factor_populated", "value": int((merged.get("positive_1_factor", "").astype(str).str.strip() != "").sum())},
    {"metric": "backup", "value": BACKUP.name},
])
summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_DRAWER_FEED_V2_JOIN_KEY_FIX] COMPLETE")
print(summary.to_string(index=False))
print(
    merged[
        [
            "horse",
            "race_date",
            "track",
            "race_no",
            "runner_key",
            "join_key",
            "dna_v6_2_score",
            "dna_v6_2_band",
            "positive_1_factor",
            "negative_1_factor",
        ]
    ].head(10).to_string(index=False)
)
