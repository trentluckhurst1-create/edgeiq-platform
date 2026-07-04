from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TERMINAL = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
RATED = DATA / "rated_market_v2.csv"
AUDIT = DATA / "edgeiq_terminal_feed_scratching_status_repair_audit_v1.csv"

def norm_horse(x):
    s = str(x or "").upper()
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^A-Z0-9]", "", s)

def norm_track(x):
    s = str(x or "").upper()
    for bad in ["LADBROKES", "SPORTSBET", "BET365", "NEDS", "TAB"]:
        s = s.replace(bad, " ")
    s = re.sub(r"[^A-Z0-9]", " ", s)
    return " ".join(s.split())

def race_no(x):
    s = str(x or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    m = re.search(r"\d+", s)
    return m.group(0) if m else s

def boolish(x):
    return str(x or "").strip().lower() in {"1", "true", "yes", "y", "scr", "scratched", "withdrawn"}

def read(path):
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")

def add_keys(df):
    df = df.copy()
    horse_col = "horse"
    if horse_col not in df.columns:
        for c in ["runner", "runner_name", "horse_name"]:
            if c in df.columns:
                horse_col = c
                break
    df["_k_track"] = df.get("track", "").map(norm_track)
    df["_k_race"] = df.get("race_no", "").map(race_no)
    df["_k_horse"] = df.get(horse_col, "").map(norm_horse)
    return df

terminal = read(TERMINAL)
rated = read(RATED)

if terminal.empty:
    raise SystemExit(f"Missing/empty terminal feed: {TERMINAL}")
if rated.empty:
    raise SystemExit(f"Missing/empty rated market: {RATED}")

terminal = add_keys(terminal)
rated = add_keys(rated)

for c in ["is_scratched", "scratch_status", "runner_status", "signal"]:
    if c not in rated.columns:
        rated[c] = ""

rated["_rated_scratched"] = (
    rated["is_scratched"].map(boolish) |
    rated["runner_status"].astype(str).str.upper().str.contains("SCRATCH|WITHDRAW", na=False) |
    rated["scratch_status"].astype(str).str.upper().str.contains("SCRATCH|WITHDRAW", na=False) |
    rated["signal"].astype(str).str.upper().str.contains("SCRATCH|WITHDRAW", na=False)
)

scratch_map = rated.loc[rated["_rated_scratched"], [
    "_k_track", "_k_race", "_k_horse", "is_scratched", "scratch_status", "runner_status", "signal"
]].drop_duplicates(["_k_track", "_k_race", "_k_horse"], keep="last")

before_scratched = 0
if "is_scratched" in terminal.columns:
    before_scratched = int(terminal["is_scratched"].map(boolish).sum())

terminal = terminal.merge(
    scratch_map,
    on=["_k_track", "_k_race", "_k_horse"],
    how="left",
    suffixes=("", "_rated"),
)

matched = terminal["runner_status_rated"].astype(str).str.upper().str.contains("SCRATCH|WITHDRAW", na=False)

for c in ["is_scratched", "scratch_status", "runner_status"]:
    if c not in terminal.columns:
        terminal[c] = ""

terminal.loc[matched, "is_scratched"] = "TRUE"
terminal.loc[matched, "scratch_status"] = "SCRATCHED"
terminal.loc[matched, "runner_status"] = "SCRATCHED"

if "ui_status" not in terminal.columns:
    terminal["ui_status"] = ""
terminal.loc[matched, "ui_status"] = "SCRATCHED"

if "ui_price" in terminal.columns:
    terminal.loc[matched, "ui_price"] = ""
if "market_price" in terminal.columns:
    terminal.loc[matched, "market_price"] = ""

audit = terminal.loc[matched].copy()

drop_cols = [c for c in terminal.columns if c.startswith("_k_") or c.endswith("_rated")]
terminal = terminal.drop(columns=drop_cols, errors="ignore")
audit = audit.drop(columns=[c for c in audit.columns if c.startswith("_k_") or c.endswith("_rated")], errors="ignore")

terminal.to_csv(TERMINAL, index=False)
audit.to_csv(AUDIT, index=False)

print("=" * 90)
print("EDGEIQ TERMINAL FEED SCRATCHING STATUS REPAIR V1")
print("=" * 90)
print("terminal rows:", len(terminal))
print("rated rows:", len(rated))
print("before terminal scratched:", before_scratched)
print("matched scratched from rated:", int(matched.sum()))
print("updated:", TERMINAL)
print("audit:", AUDIT)
print("=" * 90)
