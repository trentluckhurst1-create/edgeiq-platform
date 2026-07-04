from __future__ import annotations

import ast
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TAPE = DATA / "edgeiq_market_tape.csv"
BOOKMAKER = DATA / "edgeiq_bookmaker_board_v1.csv"
OUT = DATA / "edgeiq_market_fluctuations_v1.csv"

OUT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "race_key",
    "horse",
    "horse_key",
    "bookmaker",
    "live_price",
    "fluc_ladder",
    "fluc_count",
    "open_price",
    "low_price",
    "high_price",
    "first_seen",
    "last_seen",
]


def clean(v) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    s = str(v).strip()
    return "" if s.lower() in {"nan", "none", "null"} else s


def canon(v) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(v).upper())


def num(v):
    s = re.sub(r"[^0-9.\-]+", "", clean(v))
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def fmt_price(v) -> str:
    n = num(v)
    if n is None:
        return ""
    return f"{n:.2f}".rstrip("0").rstrip(".")


def parse_flucs(v) -> list[float]:
    text = clean(v)
    if not text:
        return []

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, (list, tuple)):
            vals = []
            for item in parsed:
                n = num(item)
                if n is not None and n > 0:
                    vals.append(n)
            return vals
    except Exception:
        pass

    vals = []
    for token in re.split(r"[,\s>|→\-]+", text):
        n = num(token)
        if n is not None and n > 0:
            vals.append(n)
    return vals


def collapse(values: list[float], max_points: int = 8) -> list[float]:
    cleaned = []
    for value in values:
        if value <= 0:
            continue
        if not cleaned or abs(cleaned[-1] - value) > 1e-9:
            cleaned.append(value)

    if len(cleaned) <= max_points:
        return cleaned

    return cleaned[-max_points:]


def best_price(row: pd.Series):
    for col in ["live_price", "sportsbet_price", "price_win", "market_price", "fixed_win"]:
        if col in row.index:
            n = num(row.get(col))
            if n is not None and n > 0:
                return n
    return None


if not TAPE.exists():
    raise FileNotFoundError(TAPE)

tape = pd.read_csv(TAPE, dtype=str).fillna("")
bookmaker = pd.read_csv(BOOKMAKER, dtype=str).fillna("") if BOOKMAKER.exists() else pd.DataFrame()

if tape.empty:
    pd.DataFrame(columns=OUT_FIELDS).to_csv(OUT, index=False)
    print("WROTE empty fluctuation file")
    raise SystemExit(0)

tape["_track_key"] = tape.get("track", "").map(canon) if "track" in tape.columns else ""
tape["_horse_key"] = tape.get("horse_key", "").map(canon) if "horse_key" in tape.columns else ""
if "_horse_key" in tape.columns and "horse" in tape.columns:
    tape.loc[tape["_horse_key"] == "", "_horse_key"] = tape.loc[tape["_horse_key"] == "", "horse"].map(canon)

tape["_race_no_key"] = tape.get("race_no", "").map(lambda x: fmt_price(x).replace(".0", "")) if "race_no" in tape.columns else ""
tape["_time"] = pd.to_datetime(
    tape.get("snapshot_time", tape.get("timestamp", tape.get("built_at", ""))),
    errors="coerce",
)

rows = []

for group_key, group in tape.groupby(["_track_key", "_race_no_key", "_horse_key"], dropna=False):
    track_key, race_no_key, horse_key = group_key
    if not track_key or not race_no_key or not horse_key:
        continue

    group = group.sort_values("_time", na_position="first")

    prices = []
    embedded = []

    for _, row in group.iterrows():
        embedded.extend(parse_flucs(row.get("recent_odds_fluctuations", "")))
        embedded.extend(parse_flucs(row.get("flucs", "")))

        p = best_price(row)
        if p is not None:
            prices.append(p)

    ladder_values = collapse(embedded + prices, max_points=8)
    if not ladder_values:
        continue

    last = group.iloc[-1]
    live_price = prices[-1] if prices else ladder_values[-1]
    open_price = ladder_values[0]
    low_price = min(ladder_values)
    high_price = max(ladder_values)

    first_seen = ""
    last_seen = ""
    valid_times = group["_time"].dropna()
    if not valid_times.empty:
        first_seen = valid_times.min().isoformat()
        last_seen = valid_times.max().isoformat()

    rows.append({
        "race_date": clean(last.get("race_date")),
        "track": clean(last.get("track")),
        "race_no": clean(last.get("race_no")),
        "race_key": clean(last.get("race_key")),
        "horse": clean(last.get("horse")),
        "horse_key": clean(last.get("horse_key")) or horse_key,
        "bookmaker": clean(last.get("bookmaker")) or "Sportsbet",
        "live_price": fmt_price(live_price),
        "fluc_ladder": " → ".join(fmt_price(v) for v in ladder_values if fmt_price(v)),
        "fluc_count": len(ladder_values),
        "open_price": fmt_price(open_price),
        "low_price": fmt_price(low_price),
        "high_price": fmt_price(high_price),
        "first_seen": first_seen,
        "last_seen": last_seen,
    })

out = pd.DataFrame(rows)

if not bookmaker.empty and {"track", "race_no", "horse_key"}.issubset(bookmaker.columns):
    bookmaker["_track_key"] = bookmaker["track"].map(canon)
    bookmaker["_race_no_key"] = bookmaker["race_no"].map(lambda x: fmt_price(x).replace(".0", ""))
    bookmaker["_horse_key"] = bookmaker["horse_key"].map(canon)

    active_keys = set(
        zip(
            bookmaker["_track_key"],
            bookmaker["_race_no_key"],
            bookmaker["_horse_key"],
        )
    )

    out["_track_key"] = out["track"].map(canon)
    out["_race_no_key"] = out["race_no"].map(lambda x: fmt_price(x).replace(".0", ""))
    out["_horse_key"] = out["horse_key"].map(canon)

    out = out[
        out.apply(
            lambda r: (r["_track_key"], r["_race_no_key"], r["_horse_key"]) in active_keys,
            axis=1,
        )
    ].copy()

    out = out.drop(columns=["_track_key", "_race_no_key", "_horse_key"], errors="ignore")

if out.empty:
    out = pd.DataFrame(columns=OUT_FIELDS)
else:
    out = out[OUT_FIELDS].sort_values(["track", "race_no", "live_price", "horse"], na_position="last")

out.to_csv(OUT, index=False)

print("=" * 90)
print("EDGEIQ MARKET FLUCTUATION ENGINE V1")
print("=" * 90)
print("rows:", len(out))
print("out:", OUT)
if not out.empty:
    print(out.head(20).to_string(index=False))
