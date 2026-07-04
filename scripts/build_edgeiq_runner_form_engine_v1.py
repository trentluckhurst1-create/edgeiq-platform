import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_runner_form_engine_v1.csv"
SUMMARY = DATA / "edgeiq_runner_form_engine_v1_summary.csv"

def read_csv(name):
    path = DATA / name
    if not path.exists():
        print(f"[WARN] missing {name}")
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")

def norm(v):
    return str(v).strip().upper()

def pick(df, cols):
    for c in cols:
        if c in df.columns:
            return c
    return None

def to_num(v):
    try:
        s = str(v).replace("$", "").replace("%", "").strip()
        if not s:
            return None
        n = float(s)
        return n if pd.notna(n) else None
    except:
        return None

def text(v, fallback=""):
    s = str(v).strip()
    return s if s else fallback

print("[RUNNER_FORM_ENGINE_V1] START")

live = read_csv("edgeiq_live_runner_board_v1.csv")

sources = [
    "edgeiq_canonical_results_truth_v1.csv",
    "edgeiq_full_execution_runner_replay_v1.csv",
    "all_horse_runs_rated.csv",
    "edgeiq_context_warehouse_v1.csv",
]

hist = pd.DataFrame()
source_used = ""

for src in sources:
    df = read_csv(src)
    if not df.empty:
        horse_col = pick(df, ["horse", "runner", "runner_name", "entity_name"])
        if horse_col:
            hist = df
            source_used = src
            break

if live.empty:
    raise SystemExit("[FAIL] edgeiq_live_runner_board_v1.csv missing/empty")

if hist.empty:
    raise SystemExit("[FAIL] no usable historical form source found")

live_horse = pick(live, ["horse", "runner", "runner_name"])
live_track = pick(live, ["track"])
live_race_no = pick(live, ["race_no", "race_number"])

hist_horse = pick(hist, ["horse", "runner", "runner_name", "entity_name"])
hist_date = pick(hist, ["race_date", "meeting_date", "date"])
hist_track = pick(hist, ["track", "meeting", "meeting_name"])
hist_distance = pick(hist, ["distance", "distance_m", "race_distance"])
hist_finish = pick(hist, ["finish_position", "finish", "placing", "position"])
hist_margin = pick(hist, ["margin", "beaten_margin", "beaten_margin_l"])
hist_sp = pick(hist, ["sp", "starting_price", "fixed_win", "market_price"])
hist_class = pick(hist, ["race_class_clean", "race_class", "class", "grade"])
hist_rating = pick(hist, [
    "performance_rating_v6_1_research",
    "performance_rating",
    "rating",
    "rated_price_score",
    "projected_rating_v5_2",
    "projected_rating_V6_1_RESEARCH"
])

live["_runner_key"] = live[live_horse].map(norm)
hist["_runner_key"] = hist[hist_horse].map(norm)

if hist_date:
    hist["_date_sort"] = pd.to_datetime(hist[hist_date], errors="coerce")
else:
    hist["_date_sort"] = pd.NaT

rows = []

for _, r in live.iterrows():
    horse = r.get(live_horse, "")
    runner_key = r["_runner_key"]
    track = r.get(live_track, "")
    race_no = r.get(live_race_no, "")

    h = hist[hist["_runner_key"] == runner_key].copy()

    if "_date_sort" in h.columns:
        h = h.sort_values("_date_sort", ascending=False)

    last5 = h.head(5).copy()

    starts = len(h)
    recent_starts = len(last5)

    finishes = []
    ratings = []
    margins = []

    for _, rr in last5.iterrows():
        if hist_finish:
            f = to_num(rr.get(hist_finish, ""))
            if f is not None:
                finishes.append(int(f))
        if hist_rating:
            rat = to_num(rr.get(hist_rating, ""))
            if rat is not None:
                ratings.append(rat)
        if hist_margin:
            m = to_num(rr.get(hist_margin, ""))
            if m is not None:
                margins.append(m)

    last5_wins = sum(1 for f in finishes if f == 1)
    last5_places = sum(1 for f in finishes if f <= 3)

    avg_finish = round(sum(finishes) / len(finishes), 2) if finishes else ""
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else ""
    best_rating = round(max(ratings), 2) if ratings else ""
    avg_margin = round(sum(margins) / len(margins), 2) if margins else ""

    rating_trend = "NO RATING TREND"
    if len(ratings) >= 3:
        recent_avg = sum(ratings[:2]) / 2
        older_avg = sum(ratings[-2:]) / 2
        diff = recent_avg - older_avg
        if diff >= 3:
            rating_trend = "UPTREND"
        elif diff <= -3:
            rating_trend = "DOWNTREND"
        else:
            rating_trend = "STABLE"

    form_signal = "LIMITED FORM"
    if recent_starts >= 3:
        if last5_wins >= 2:
            form_signal = "WINNING FORM"
        elif last5_places >= 3:
            form_signal = "CONSISTENT"
        elif rating_trend == "UPTREND":
            form_signal = "IMPROVING"
        elif rating_trend == "DOWNTREND":
            form_signal = "DECLINING"
        elif finishes and sum(1 for f in finishes[:3] if f > 6) >= 2:
            form_signal = "OUT OF FORM"
        else:
            form_signal = "MIXED FORM"

    last5_summary = []
    for _, rr in last5.iterrows():
        d = text(rr.get(hist_date, "")) if hist_date else ""
        tr = text(rr.get(hist_track, "")) if hist_track else ""
        dist = text(rr.get(hist_distance, "")) if hist_distance else ""
        fin = text(rr.get(hist_finish, "")) if hist_finish else ""
        cls = text(rr.get(hist_class, "")) if hist_class else ""
        bits = [x for x in [d, tr, dist, f"F{fin}" if fin else "", cls] if x]
        if bits:
            last5_summary.append(" / ".join(bits))

    if recent_starts == 0:
        narrative = f"{horse} has no recent historical form rows available in the current EDGEiQ form source."
    else:
        narrative_bits = [f"{horse} has {recent_starts} recent runs available"]
        if last5_wins:
            narrative_bits.append(f"{last5_wins} wins from the recent sample")
        if last5_places:
            narrative_bits.append(f"{last5_places} placings from the recent sample")
        if rating_trend not in ["NO RATING TREND", "STABLE"]:
            narrative_bits.append(f"ratings profile is {rating_trend.lower()}")
        narrative_bits.append(f"form signal: {form_signal.lower()}")
        narrative = ". ".join(narrative_bits) + "."

    rows.append({
        "track": track,
        "race_no": race_no,
        "horse": horse,
        "runner_key": runner_key,
        "historical_source_used": source_used,
        "career_rows_found": starts,
        "recent_runs_found": recent_starts,
        "last5_wins": last5_wins,
        "last5_places": last5_places,
        "avg_finish_last5": avg_finish,
        "avg_margin_last5": avg_margin,
        "avg_rating_last5": avg_rating,
        "best_rating_last5": best_rating,
        "rating_trend": rating_trend,
        "form_signal": form_signal,
        "last5_summary": " | ".join(last5_summary),
        "form_narrative": narrative,
        "built_at": datetime.now(timezone.utc).isoformat()
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RUNNER_FORM_ENGINE_V1_BUILT",
    "rows": len(out),
    "source_used": source_used,
    "with_recent_runs": int((out["recent_runs_found"].astype(int) > 0).sum()),
    "without_recent_runs": int((out["recent_runs_found"].astype(int) == 0).sum()),
    "with_rating_trend": int((out["rating_trend"].astype(str) != "NO RATING TREND").sum()),
    "winning_form": int((out["form_signal"] == "WINNING FORM").sum()),
    "consistent": int((out["form_signal"] == "CONSISTENT").sum()),
    "improving": int((out["form_signal"] == "IMPROVING").sum()),
    "declining": int((out["form_signal"] == "DECLINING").sum()),
    "mixed_form": int((out["form_signal"] == "MIXED FORM").sum()),
    "built_at": datetime.now(timezone.utc).isoformat()
}])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_FORM_ENGINE_V1] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"summary={SUMMARY}")
