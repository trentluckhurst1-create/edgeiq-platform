import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_runner_form_engine_v1_1.csv"
SUMMARY = DATA / "edgeiq_runner_form_engine_v1_1_summary.csv"

def read_csv(name):
    path = DATA / name
    if not path.exists():
        print(f"[WARN] missing {name}")
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")

def norm(v):
    return str(v).strip().upper()

def to_num(v):
    try:
        s = str(v).replace("$", "").replace("%", "").strip()
        if not s:
            return None
        n = float(s)
        return n if pd.notna(n) else None
    except:
        return None

def fmt(v, digits=1):
    if v is None:
        return ""
    return round(float(v), digits)

print("[RUNNER_FORM_ENGINE_V1_1] START")

live = read_csv("edgeiq_live_runner_board_v1.csv")
ratings = read_csv("edgeiq_historical_performance_rating_v6_1_research.csv")
form_v1 = read_csv("edgeiq_runner_form_engine_v1.csv")

if live.empty:
    raise SystemExit("[FAIL] edgeiq_live_runner_board_v1.csv missing/empty")

if ratings.empty:
    raise SystemExit("[FAIL] edgeiq_historical_performance_rating_v6_1_research.csv missing/empty")

live["_runner_key"] = live["horse"].map(norm)
ratings["_runner_key"] = ratings["horse"].map(norm)
ratings["_race_date_sort"] = pd.to_datetime(ratings["race_date"], errors="coerce")
ratings["_rating_num"] = ratings["performance_rating_v6_1_research"].map(to_num)
ratings["_finish_num"] = ratings["finish_position"].map(to_num)
ratings["_margin_num"] = ratings["margin"].map(to_num)

if not form_v1.empty:
    form_v1["_runner_key"] = form_v1["horse"].map(norm)

rows = []

for _, r in live.iterrows():
    horse = r.get("horse", "")
    runner_key = r["_runner_key"]
    track = r.get("track", "")
    race_no = r.get("race_no", "")

    h = ratings[ratings["_runner_key"] == runner_key].copy()
    h = h.sort_values("_race_date_sort", ascending=False)

    last5 = h.head(5).copy()
    rating_vals = [x for x in last5["_rating_num"].tolist() if x is not None]
    finish_vals = [x for x in last5["_finish_num"].tolist() if x is not None]
    margin_vals = [x for x in last5["_margin_num"].tolist() if x is not None]

    rating_1 = fmt(rating_vals[0], 2) if len(rating_vals) >= 1 else ""
    rating_2 = fmt(rating_vals[1], 2) if len(rating_vals) >= 2 else ""
    rating_3 = fmt(rating_vals[2], 2) if len(rating_vals) >= 3 else ""
    rating_4 = fmt(rating_vals[3], 2) if len(rating_vals) >= 4 else ""
    rating_5 = fmt(rating_vals[4], 2) if len(rating_vals) >= 5 else ""

    avg_rating_last5 = fmt(sum(rating_vals) / len(rating_vals), 2) if rating_vals else ""
    best_rating_last5 = fmt(max(rating_vals), 2) if rating_vals else ""
    last_start_rating = rating_1

    career_ratings = [x for x in h["_rating_num"].tolist() if x is not None]
    peak_rating = fmt(max(career_ratings), 2) if career_ratings else ""

    rating_trend = "NO RATING TREND"
    trend_delta = ""

    if len(rating_vals) >= 3:
        recent = sum(rating_vals[:2]) / 2
        older = sum(rating_vals[-2:]) / 2
        delta = recent - older
        trend_delta = fmt(delta, 2)

        if delta >= 5:
            rating_trend = "STRONG UPTREND"
        elif delta >= 2:
            rating_trend = "UPTREND"
        elif delta <= -5:
            rating_trend = "STRONG DOWNTREND"
        elif delta <= -2:
            rating_trend = "DOWNTREND"
        else:
            rating_trend = "STABLE"

    form_cycle = "LIMITED FORM"
    peaking_signal = "NO PEAK SIGNAL"

    if rating_vals:
        if peak_rating != "" and last_start_rating != "" and float(last_start_rating) >= float(peak_rating) - 0.5:
            peaking_signal = "NEAR CAREER PEAK"

        if len(rating_vals) >= 3:
            if rating_trend in ["STRONG UPTREND", "UPTREND"]:
                form_cycle = "IMPROVING"
            elif rating_trend in ["STRONG DOWNTREND", "DOWNTREND"]:
                form_cycle = "DECLINING"
            elif peaking_signal == "NEAR CAREER PEAK":
                form_cycle = "PEAKING"
            else:
                form_cycle = "HOLDING FORM"
        elif len(rating_vals) >= 1:
            form_cycle = "SOME FORM"

    last5_wins = sum(1 for f in finish_vals if f == 1)
    last5_places = sum(1 for f in finish_vals if f <= 3)
    avg_finish_last5 = fmt(sum(finish_vals) / len(finish_vals), 2) if finish_vals else ""
    avg_margin_last5 = fmt(sum(margin_vals) / len(margin_vals), 2) if margin_vals else ""

    recent_runs_found = len(last5)

    last5_summary = []
    for _, rr in last5.iterrows():
        bits = [
            str(rr.get("race_date", "")).strip(),
            str(rr.get("track", "")).strip(),
            str(rr.get("distance", "")).strip(),
            f"F{str(rr.get('finish_position', '')).strip()}" if str(rr.get("finish_position", "")).strip() else "",
            f"R{str(rr.get('performance_rating_v6_1_research', '')).strip()}" if str(rr.get("performance_rating_v6_1_research", "")).strip() else "",
        ]
        last5_summary.append(" / ".join([b for b in bits if b]))

    if recent_runs_found == 0:
        form_signal = "LIMITED FORM"
        narrative = f"{horse} has no recent rated form rows available in the EDGEiQ rating history."
    else:
        if last5_wins >= 2:
            form_signal = "WINNING FORM"
        elif last5_places >= 3:
            form_signal = "CONSISTENT"
        elif form_cycle == "IMPROVING":
            form_signal = "IMPROVING"
        elif form_cycle == "DECLINING":
            form_signal = "DECLINING"
        elif form_cycle == "PEAKING":
            form_signal = "PEAKING"
        elif finish_vals and sum(1 for f in finish_vals[:3] if f > 6) >= 2:
            form_signal = "OUT OF FORM"
        else:
            form_signal = "MIXED FORM"

        bits = [f"{horse} has {recent_runs_found} recent rated runs"]
        if last_start_rating != "":
            bits.append(f"last-start rating {last_start_rating}")
        if best_rating_last5 != "":
            bits.append(f"best recent rating {best_rating_last5}")
        if rating_trend not in ["NO RATING TREND", "STABLE"]:
            bits.append(f"ratings show {rating_trend.lower()}")
        if peaking_signal == "NEAR CAREER PEAK":
            bits.append("last-start profile is near career peak")
        bits.append(f"form signal: {form_signal.lower()}")
        narrative = ". ".join(bits) + "."

    rows.append({
        "track": track,
        "race_no": race_no,
        "horse": horse,
        "runner_key": runner_key,
        "historical_source_used": "edgeiq_historical_performance_rating_v6_1_research.csv",
        "recent_runs_found": recent_runs_found,
        "last5_wins": last5_wins,
        "last5_places": last5_places,
        "avg_finish_last5": avg_finish_last5,
        "avg_margin_last5": avg_margin_last5,
        "rating_1": rating_1,
        "rating_2": rating_2,
        "rating_3": rating_3,
        "rating_4": rating_4,
        "rating_5": rating_5,
        "last_start_rating": last_start_rating,
        "avg_rating_last5": avg_rating_last5,
        "best_rating_last5": best_rating_last5,
        "peak_rating": peak_rating,
        "rating_trend": rating_trend,
        "rating_trend_delta": trend_delta,
        "form_cycle": form_cycle,
        "peaking_signal": peaking_signal,
        "form_signal": form_signal,
        "last5_summary": " | ".join(last5_summary),
        "form_narrative": narrative,
        "built_at": datetime.now(timezone.utc).isoformat()
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RUNNER_FORM_ENGINE_V1_1_BUILT",
    "rows": len(out),
    "source_used": "edgeiq_historical_performance_rating_v6_1_research.csv",
    "with_recent_runs": int((out["recent_runs_found"].astype(int) > 0).sum()),
    "without_recent_runs": int((out["recent_runs_found"].astype(int) == 0).sum()),
    "with_rating_trend": int((out["rating_trend"].astype(str) != "NO RATING TREND").sum()),
    "improving": int((out["form_signal"] == "IMPROVING").sum()),
    "declining": int((out["form_signal"] == "DECLINING").sum()),
    "peaking": int((out["form_signal"] == "PEAKING").sum()),
    "winning_form": int((out["form_signal"] == "WINNING FORM").sum()),
    "consistent": int((out["form_signal"] == "CONSISTENT").sum()),
    "mixed_form": int((out["form_signal"] == "MIXED FORM").sum()),
    "out_of_form": int((out["form_signal"] == "OUT OF FORM").sum()),
    "built_at": datetime.now(timezone.utc).isoformat()
}])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_FORM_ENGINE_V1_1] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"summary={SUMMARY}")
