from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

FIELDS = DATA / "race_fields.csv"
FORM = DATA / "full_career_form.csv"
SUMMARY = DATA / "form_card_summary.csv"
SPEED = DATA / "speed_map_report.csv"
MARKET = DATA / "rated_market_v2.csv"

OUT = DATA / "ratings_audit_elite_v2.csv"
OUT_RACE = DATA / "ratings_audit_by_race_v2.csv"
OUT_CURRENT = DATA / "ratings_audit_elite.csv"
OUT_RACE_CURRENT = DATA / "ratings_audit_by_race.csv"


def compact(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).upper().strip()
    s = re.sub(r"\([A-Z]{2,4}\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s


def clean_track(x) -> str:
    return text(x).upper().strip()


def num(x):
    try:
        if pd.isna(x):
            return None
        s = str(x).replace("$", "").replace("%", "").replace(",", "").strip()
        if not s or s.lower() in {"nan", "none", "null", "-", "—"}:
            return None
        v = float(s)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def text(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    return "" if s.lower() in {"nan", "none", "null"} else s


def clip(v, lo, hi):
    return max(lo, min(hi, v))


def load(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def parse_condition_band(x: str) -> str:
    s = text(x).upper()
    if "FAST" in s:
        return "FAST"
    if "GOOD" in s:
        return "GOOD"
    if "SOFT" in s:
        return "SOFT"
    if "HEAVY" in s:
        return "HEAVY"
    return ""


def race_key(row) -> str:
    return f"{text(row.get('race_date'))}|{clean_track(row.get('track'))}|{int(num(row.get('race_no')) or 0)}"


def runner_key(row) -> str:
    return f"{race_key(row)}|{compact(row.get('horse_key') or row.get('horse'))}"


def safe_mean(vals):
    vals = [v for v in vals if v is not None and math.isfinite(v)]
    return sum(vals) / len(vals) if vals else None


def safe_std(vals):
    vals = [v for v in vals if v is not None and math.isfinite(v)]
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def decay_peak(peak, days_since_peak):
    if peak is None:
        return None
    if days_since_peak is None:
        return peak * 0.92
    if days_since_peak <= 60:
        return peak
    if days_since_peak <= 120:
        return peak * 0.985
    if days_since_peak <= 240:
        return peak * 0.955
    if days_since_peak <= 365:
        return peak * 0.925
    return peak * 0.88


def run_style_from_speed_row(row: dict | None) -> str:
    if not row:
        return ""
    raw = (
        row.get("speed_map")
        or row.get("map_bucket")
        or row.get("run_style")
        or row.get("pace_bucket")
        or row.get("settling_position")
        or ""
    )
    s = text(raw).upper()
    if "LEADER" in s:
        return "LEADER"
    if "ON" in s or "PACE" in s:
        return "ON PACE"
    if "MID" in s:
        return "MIDFIELD"
    if "BACK" in s:
        return "BACKMARKER"
    if "FIRST" in s:
        return "FIRST START"
    return s


def get_market_price(row, market_row):
    candidates = [
        row.get("market_price"),
        row.get("fixed_odds"),
        row.get("win_odds"),
        market_row.get("market_price") if market_row else None,
        market_row.get("fixed_odds") if market_row else None,
        market_row.get("win_odds") if market_row else None,
    ]
    for c in candidates:
        v = num(c)
        if v is not None and v > 0:
            return v
    return None


fields = load(FIELDS)
form = load(FORM)
summary = load(SUMMARY)
speed = load(SPEED)
market = load(MARKET)

if fields.empty:
    raise SystemExit("MISSING public/data/race_fields.csv")

fields["horse_key_norm"] = fields.apply(lambda r: compact(r.get("horse_key") or r.get("horse")), axis=1)
fields["race_key"] = fields.apply(race_key, axis=1)
fields["runner_key"] = fields.apply(runner_key, axis=1)

if not form.empty:
    form["horse_key_norm"] = form.apply(lambda r: compact(r.get("horse_key") or r.get("horse")), axis=1)
    form["run_date_dt"] = pd.to_datetime(form.get("run_date"), errors="coerce")
    form["run_rating_num"] = form.get("run_rating").map(num)
    form["distance_num"] = form.get("distance").map(num)
    form["track_norm"] = form.get("track", "").map(clean_track)
    form["condition_band"] = form.get("track_condition", "").map(parse_condition_band)
    form["is_race"] = form.get("run_type", "").astype(str).str.upper().eq("RACE")
else:
    form = pd.DataFrame(columns=["horse_key_norm"])

if not summary.empty:
    summary["horse_key_norm"] = summary.apply(lambda r: compact(r.get("horse_key") or r.get("horse")), axis=1)

if not speed.empty:
    speed["horse_key_norm"] = speed.apply(lambda r: compact(r.get("horse_key") or r.get("horse")), axis=1)
    speed["race_key"] = speed.apply(race_key, axis=1)

if not market.empty:
    market["runner_key"] = market.apply(runner_key, axis=1)

summary_map = {}
for _, r in summary.iterrows():
    summary_map[r["horse_key_norm"]] = {
        "ls1": num(r.get("1LS")),
        "ls2": num(r.get("2LS")),
        "ls3": num(r.get("3LS")),
        "ls4": num(r.get("4LS")),
        "ls5": num(r.get("5LS")),
        "avg3": num(r.get("3LSA")),
        "avg5": num(r.get("5LSA")),
        "peak": num(r.get("PEAK")),
        "official_run_count": num(r.get("official_run_count")),
        "gap": num(r.get("gap")),
    }

speed_map = {}
for _, r in speed.iterrows():
    speed_map[f"{r.get('race_key')}|{r.get('horse_key_norm')}"] = r.to_dict()

market_map = {}
for _, r in market.iterrows():
    market_map[r.get("runner_key")] = r.to_dict()

# Race-level pace context
race_pace_context = {}
for rk, group in fields.groupby("race_key"):
    leaders = 0
    onpace = 0
    backmarkers = 0
    first_starters = 0
    styles = {}

    for _, runner in group.iterrows():
        hk = runner["horse_key_norm"]
        sm = speed_map.get(f"{rk}|{hk}")
        style = run_style_from_speed_row(sm)
        styles[hk] = style

        if style == "LEADER":
            leaders += 1
        elif style == "ON PACE":
            onpace += 1
        elif style == "BACKMARKER":
            backmarkers += 1
        elif style == "FIRST START":
            first_starters += 1

    pressure_score = leaders * 2.0 + onpace * 1.0
    if leaders == 0 and onpace <= 1:
        pace_shape = "NO SPEED"
    elif leaders <= 1 and onpace <= 3:
        pace_shape = "SOFT / CONTROL"
    elif pressure_score <= 5:
        pace_shape = "GENUINE"
    else:
        pace_shape = "HIGH PRESSURE"

    race_pace_context[rk] = {
        "leaders": leaders,
        "onpace": onpace,
        "backmarkers": backmarkers,
        "first_starters": first_starters,
        "pressure_score": pressure_score,
        "pace_shape": pace_shape,
        "styles": styles,
    }

rows = []
today = pd.Timestamp.today().normalize()

for _, runner in fields.iterrows():
    hk = runner["horse_key_norm"]
    rk = runner["race_key"]
    run_key = runner["runner_key"]

    horse_form = form[(form["horse_key_norm"] == hk) & (form["is_race"])].copy()
    horse_form = horse_form.sort_values("run_date_dt", ascending=False)

    ratings = horse_form["run_rating_num"].dropna().tolist()
    recent = ratings[:5]
    recent3 = ratings[:3]

    today_dist = num(runner.get("distance"))
    today_cond = parse_condition_band(runner.get("track_condition"))
    today_track = clean_track(runner.get("track"))
    race_class = text(runner.get("race_class")).upper()

    s = summary_map.get(hk, {})
    ls = [s.get("ls1"), s.get("ls2"), s.get("ls3"), s.get("ls4"), s.get("ls5")]
    valid_ls = [x for x in ls if x is not None]

    official_runs = int(s.get("official_run_count") or len(horse_form))

    # V2 BASE: expected rating with regression + peak decay
    weighted_recent = None
    source_note = ""

    if len(valid_ls) >= 3:
        weights = [0.34, 0.24, 0.18, 0.14, 0.10]
        weighted_recent = sum(v * weights[i] for i, v in enumerate(valid_ls[:5])) / sum(weights[: len(valid_ls[:5])])
        source_note = "summary weighted LS"
    elif recent:
        weights = [0.34, 0.24, 0.18, 0.14, 0.10]
        weighted_recent = sum(v * weights[i] for i, v in enumerate(recent[:5])) / sum(weights[: len(recent[:5])])
        source_note = "form weighted runs"

    avg5 = s.get("avg5") or safe_mean(recent[:5])
    avg3 = s.get("avg3") or safe_mean(recent[:3])
    peak = s.get("peak") or (max(ratings) if ratings else None)

    days_since_last = None
    days_since_peak = None
    if not horse_form.empty and pd.notna(horse_form.iloc[0]["run_date_dt"]):
        days_since_last = int((today - horse_form.iloc[0]["run_date_dt"]).days)

    if peak is not None and not horse_form.empty:
        peak_rows = horse_form[horse_form["run_rating_num"].eq(peak)]
        if len(peak_rows) and pd.notna(peak_rows.iloc[0]["run_date_dt"]):
            days_since_peak = int((today - peak_rows.iloc[0]["run_date_dt"]).days)

    decayed_peak = decay_peak(peak, days_since_peak)

    if weighted_recent is not None:
        mean_anchor = avg5 or weighted_recent
        peak_anchor = decayed_peak or weighted_recent
        # Regression to mean. If recent spike is huge, pull it back. If recent shocker, do not destroy the horse.
        raw_base = (weighted_recent * 0.58) + (mean_anchor * 0.27) + (peak_anchor * 0.15)
        if weighted_recent > mean_anchor + 8:
            raw_base -= min(4.0, (weighted_recent - mean_anchor) * 0.30)
        elif weighted_recent < mean_anchor - 8:
            raw_base += min(3.0, (mean_anchor - weighted_recent) * 0.22)
        base_rating = raw_base
    elif peak is not None:
        base_rating = peak * 0.88
        source_note = "peak fallback"
    else:
        base_rating = 45.0
        source_note = "no-data fallback"

    # Distance fit
    dist_adj = 1.0
    dist_note = "neutral"
    if today_dist and not horse_form.empty:
        near = horse_form[horse_form["distance_num"].apply(lambda d: d is not None and abs(d - today_dist) <= 200)]
        if len(near):
            near_avg = near["run_rating_num"].dropna().mean()
            all_avg = horse_form["run_rating_num"].dropna().mean()
            if pd.notna(near_avg) and pd.notna(all_avg):
                diff = near_avg - all_avg
                dist_adj = 1 + clip(diff / 100, -0.065, 0.065)
                dist_note = f"near-distance diff {diff:.1f}"
        elif official_runs >= 4:
            dist_adj = 0.975
            dist_note = "limited distance evidence"

    # Condition fit
    cond_adj = 1.0
    cond_note = "neutral"
    if today_cond and not horse_form.empty:
        same_cond = horse_form[horse_form["condition_band"].eq(today_cond)]
        if len(same_cond):
            same_avg = same_cond["run_rating_num"].dropna().mean()
            all_avg = horse_form["run_rating_num"].dropna().mean()
            if pd.notna(same_avg) and pd.notna(all_avg):
                diff = same_avg - all_avg
                cond_adj = 1 + clip(diff / 100, -0.065, 0.065)
                cond_note = f"{today_cond} diff {diff:.1f}"
        elif today_cond in {"SOFT", "HEAVY"}:
            cond_adj = 0.975
            cond_note = f"no {today_cond} evidence"

    # Track fit
    track_adj = 1.0
    track_note = "neutral"
    if today_track and not horse_form.empty:
        same_track = horse_form[horse_form["track_norm"].eq(today_track)]
        if len(same_track):
            same_avg = same_track["run_rating_num"].dropna().mean()
            all_avg = horse_form["run_rating_num"].dropna().mean()
            if pd.notna(same_avg) and pd.notna(all_avg):
                diff = same_avg - all_avg
                track_adj = 1 + clip(diff / 120, -0.045, 0.045)
                track_note = f"track diff {diff:.1f}"

    # Recency
    recency_adj = 1.0
    recency_note = "unknown"
    if days_since_last is not None:
        if days_since_last <= 7:
            recency_adj = 0.975
            recency_note = f"{days_since_last}d quick backup"
        elif days_since_last <= 35:
            recency_adj = 1.015
            recency_note = f"{days_since_last}d ideal"
        elif days_since_last <= 70:
            recency_adj = 1.0
            recency_note = f"{days_since_last}d okay"
        elif days_since_last <= 140:
            recency_adj = 0.965
            recency_note = f"{days_since_last}d fresh"
        else:
            recency_adj = 0.925
            recency_note = f"{days_since_last}d long break"

    # Pace pressure model
    ctx = race_pace_context.get(rk, {})
    pressure_score = ctx.get("pressure_score", 0)
    pace_shape = ctx.get("pace_shape", "")
    sm = speed_map.get(f"{rk}|{hk}")
    style = run_style_from_speed_row(sm)
    barrier = num(runner.get("barrier"))
    field_size = len(fields[fields["race_key"].eq(rk)])

    map_adj = 1.0
    map_note = "no map"

    if style:
        map_note = f"{style} / {pace_shape}"

        if style == "LEADER":
            if pace_shape == "SOFT / CONTROL" or pace_shape == "NO SPEED":
                map_adj += 0.045
            elif pace_shape == "HIGH PRESSURE":
                map_adj -= 0.035
            else:
                map_adj += 0.010

        elif style == "ON PACE":
            if pace_shape in {"SOFT / CONTROL", "GENUINE"}:
                map_adj += 0.020
            elif pace_shape == "HIGH PRESSURE":
                map_adj -= 0.010

        elif style == "MIDFIELD":
            if pace_shape == "HIGH PRESSURE":
                map_adj += 0.018
            elif pace_shape == "NO SPEED":
                map_adj -= 0.015

        elif style == "BACKMARKER":
            if pace_shape == "HIGH PRESSURE":
                map_adj += 0.030
            elif pace_shape in {"NO SPEED", "SOFT / CONTROL"}:
                map_adj -= 0.030
            else:
                map_adj -= 0.006

        elif style == "FIRST START":
            map_adj -= 0.018

        if barrier and field_size:
            if barrier <= 3 and style in {"LEADER", "ON PACE"}:
                map_adj += 0.014
                map_note += " + inside speed"
            if barrier >= max(10, field_size - 2) and style in {"LEADER", "ON PACE"}:
                map_adj -= 0.018
                map_note += " + wide speed risk"
            if barrier <= 2 and style == "BACKMARKER" and field_size >= 12:
                map_adj -= 0.010
                map_note += " + inside backmarker traffic"

    # Variance / confidence
    rating_std = safe_std(recent)
    consistency_score = 100.0
    if rating_std is not None:
        consistency_score = clip(100 - (rating_std * 5.2), 20, 100)

    evidence_score = 0
    if official_runs >= 5:
        evidence_score += 30
    elif official_runs >= 3:
        evidence_score += 22
    elif official_runs >= 1:
        evidence_score += 10

    if today_dist and not horse_form.empty:
        distance_hits = horse_form["distance_num"].apply(lambda d: d is not None and abs(d - today_dist) <= 200).sum()
        if distance_hits >= 2:
            evidence_score += 15
        elif distance_hits == 1:
            evidence_score += 7

    if today_cond and not horse_form.empty:
        cond_hits = horse_form["condition_band"].eq(today_cond).sum()
        if cond_hits >= 2:
            evidence_score += 12
        elif cond_hits == 1:
            evidence_score += 6

    if style:
        evidence_score += 10

    if days_since_last is not None and days_since_last <= 70:
        evidence_score += 10

    evidence_score = clip(evidence_score, 0, 80)
    confidence_score = clip((consistency_score * 0.45) + (evidence_score * 0.55), 5, 100)

    if official_runs == 0:
        reliability_adj = 0.82
    elif official_runs == 1:
        reliability_adj = 0.90
    elif official_runs == 2:
        reliability_adj = 0.95
    elif official_runs >= 8 and confidence_score >= 60:
        reliability_adj = 1.025
    else:
        reliability_adj = 1.0

    # Race difficulty score
    race_field_size = len(fields[fields["race_key"].eq(rk)])
    first_starters = ctx.get("first_starters", 0)
    chaos = 0
    chaos += clip((race_field_size - 8) * 3, 0, 30)
    chaos += clip(pressure_score * 3, 0, 25)
    chaos += clip(first_starters * 4, 0, 20)
    chaos += 10 if today_cond in {"SOFT", "HEAVY"} else 0
    chaos += 10 if race_class in {"MDN", "MAIDEN"} or "MDN" in race_class else 0
    race_difficulty = clip(chaos, 0, 100)

    # Class placeholder, but audit-ready
    class_adj = 1.0
    class_note = "neutral - pars not wired yet"

    elite_today_rating = (
        base_rating
        * class_adj
        * dist_adj
        * cond_adj
        * track_adj
        * recency_adj
        * map_adj
        * reliability_adj
    )

    # Uncertainty shrink: low confidence pulls rating slightly toward field-neutral 50
    uncertainty_weight = clip((100 - confidence_score) / 100, 0, 0.35)
    elite_today_rating = elite_today_rating * (1 - uncertainty_weight) + 50 * uncertainty_weight
    elite_today_rating = clip(elite_today_rating, 20, 120)

    market_row = market_map.get(run_key, {})
    market_price = get_market_price(runner, market_row)
    old_rated_price = num(market_row.get("rated_price")) if market_row else None

    rows.append({
        "race_date": runner.get("race_date"),
        "track": runner.get("track"),
        "race_no": runner.get("race_no"),
        "horse_no": runner.get("horse_no"),
        "horse": runner.get("horse"),
        "horse_key": hk,
        "jockey": runner.get("jockey"),
        "trainer": runner.get("trainer"),
        "barrier": runner.get("barrier"),
        "race_class": race_class,
        "distance": today_dist,
        "track_condition": runner.get("track_condition"),

        "official_runs": official_runs,
        "source_note": source_note,
        "base_rating_v2": round(base_rating, 3),
        "elite_today_rating": round(elite_today_rating, 3),

        "ls1": s.get("ls1"),
        "avg3": avg3,
        "avg5": avg5,
        "peak": peak,
        "decayed_peak": round(decayed_peak, 3) if decayed_peak is not None else None,
        "days_since_last": days_since_last,
        "days_since_peak": days_since_peak,

        "class_adj": round(class_adj, 4),
        "distance_adj": round(dist_adj, 4),
        "condition_adj": round(cond_adj, 4),
        "track_adj": round(track_adj, 4),
        "recency_adj": round(recency_adj, 4),
        "map_adj": round(map_adj, 4),
        "reliability_adj": round(reliability_adj, 4),

        "pace_shape": pace_shape,
        "pace_pressure_score": pressure_score,
        "leaders_in_race": ctx.get("leaders", 0),
        "onpace_in_race": ctx.get("onpace", 0),
        "runner_style": style,
        "map_note": map_note,

        "rating_std_last5": round(rating_std, 3) if rating_std is not None else None,
        "consistency_score": round(consistency_score, 2),
        "evidence_score": round(evidence_score, 2),
        "confidence_score": round(confidence_score, 2),
        "race_difficulty_score": round(race_difficulty, 2),

        "distance_note": dist_note,
        "condition_note": cond_note,
        "track_note": track_note,
        "recency_note": recency_note,
        "class_note": class_note,

        "market_price": market_price,
        "old_rated_price": old_rated_price,
        "race_key": rk,
        "runner_key": run_key,
    })

audit = pd.DataFrame(rows)

audit["elite_prob_raw"] = 0.0
audit["elite_prob_confidence_adjusted"] = 0.0
audit["elite_rated_price"] = None
audit["elite_rated_price_fair"] = None

for rk, g in audit.groupby("race_key"):
    idx = g.index

    raw_rating = g["elite_today_rating"].fillna(0).clip(lower=0)
    raw_total = raw_rating.sum()

    if raw_total > 0:
        raw_probs = raw_rating / raw_total
        audit.loc[idx, "elite_prob_raw"] = raw_probs
        audit.loc[idx, "elite_rated_price_fair"] = raw_probs.apply(lambda p: round(1 / p, 3) if p > 0 else None)

    # Confidence-adjusted price: widen low confidence, especially chaotic races
    confidence = g["confidence_score"].fillna(35).clip(5, 100)
    difficulty = g["race_difficulty_score"].fillna(50).clip(0, 100)

    adjusted_rating = raw_rating * (0.72 + (confidence / 100) * 0.28)
    adjusted_rating = adjusted_rating * (1 - (difficulty / 100) * 0.035)

    adjusted_total = adjusted_rating.sum()
    if adjusted_total > 0:
        adj_probs = adjusted_rating / adjusted_total
        audit.loc[idx, "elite_prob_confidence_adjusted"] = adj_probs
        audit.loc[idx, "elite_rated_price"] = adj_probs.apply(lambda p: round(1 / p, 3) if p > 0 else None)

audit["elite_edge_pct"] = audit.apply(
    lambda r: round(((r["market_price"] / r["elite_rated_price"]) - 1) * 100, 2)
    if pd.notna(r["market_price"]) and pd.notna(r["elite_rated_price"]) and r["elite_rated_price"] > 0
    else None,
    axis=1,
)

def grade(row):
    edge = row.get("elite_edge_pct")
    conf = row.get("confidence_score")
    diff = row.get("race_difficulty_score")

    if pd.isna(edge):
        return "NO MARKET"
    if edge < 0:
        return "PASS"
    if conf < 35 or diff > 75:
        if edge >= 80:
            return "SPEC B"
        if edge >= 35:
            return "SPEC C"
        return "PASS"
    if edge >= 100 and conf >= 55:
        return "A+"
    if edge >= 50 and conf >= 45:
        return "A"
    if edge >= 20:
        return "B"
    if edge >= 0:
        return "C"
    return "PASS"

audit["bet_grade"] = audit.apply(grade, axis=1)

audit["decision_note"] = audit.apply(
    lambda r:
    "STRONG OVERLAY" if r["bet_grade"] in {"A+", "A"} else
    "PLAYABLE / CHECK MARKET" if r["bet_grade"] == "B" else
    "SPECULATIVE ONLY" if str(r["bet_grade"]).startswith("SPEC") else
    "NO BET / WATCH",
    axis=1,
)

audit.to_csv(OUT, index=False)
audit.to_csv(OUT_CURRENT, index=False)

race = audit.groupby(["race_date", "track", "race_no"]).agg(
    runners=("horse", "count"),
    avg_rating=("elite_today_rating", "mean"),
    max_rating=("elite_today_rating", "max"),
    avg_confidence=("confidence_score", "mean"),
    race_difficulty=("race_difficulty_score", "mean"),
    pace_pressure=("pace_pressure_score", "max"),
    top_edge=("elite_edge_pct", "max"),
    missing_market=("market_price", lambda s: int(s.isna().sum())),
    no_data_fallbacks=("source_note", lambda s: int((s == "no-data fallback").sum())),
).reset_index()

race.to_csv(OUT_RACE, index=False)
race.to_csv(OUT_RACE_CURRENT, index=False)

print("ELITE RATINGS AUDIT V2 BUILT")
print("Rows:", len(audit))
print("Wrote:", OUT)
print("Wrote:", OUT_RACE)
print()
print(audit[[
    "track", "race_no", "horse_no", "horse",
    "source_note", "base_rating_v2", "elite_today_rating",
    "elite_rated_price", "market_price", "elite_edge_pct", "bet_grade",
    "confidence_score", "race_difficulty_score", "pace_shape", "runner_style",
    "distance_adj", "condition_adj", "recency_adj", "map_adj", "reliability_adj"
]].head(40).to_string(index=False))
