import csv, math, re
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

OUT_INV = DATA / "edgeiq_rating_engine_input_inventory_v1.csv"
OUT_INV_SUM = DATA / "edgeiq_rating_engine_input_inventory_v1_summary.csv"
OUT_QUALITY = DATA / "edgeiq_rating_engine_data_quality_v1.csv"
OUT_QUALITY_SUM = DATA / "edgeiq_rating_engine_data_quality_v1_summary.csv"
OUT_IMPORTANCE = DATA / "edgeiq_rating_engine_factor_importance_v1.csv"
OUT_IMPORTANCE_SUM = DATA / "edgeiq_rating_engine_factor_importance_v1_summary.csv"
OUT_DOUBLE = DATA / "edgeiq_rating_engine_double_count_v1.csv"
OUT_DOUBLE_SUM = DATA / "edgeiq_rating_engine_double_count_v1_summary.csv"
OUT_LEAK = DATA / "edgeiq_rating_engine_leakage_audit_v1.csv"
OUT_LEAK_SUM = DATA / "edgeiq_rating_engine_leakage_audit_v1_summary.csv"
OUT_MISSING = DATA / "edgeiq_rating_engine_missing_signal_v1.csv"
OUT_MISSING_SUM = DATA / "edgeiq_rating_engine_missing_signal_v1_summary.csv"
REPORT = DATA / "EDGEIQ_PERFORMANCE_RATING_ENGINE_AUDIT_V1_REPORT.txt"

MAIN_FILES = {
    "V6_1_HISTORICAL_PERFORMANCE_RATING": DATA / "edgeiq_historical_performance_rating_v6_1_research.csv",
    "HISTORICAL_RUN_RATINGS_MASTER": DATA / "edgeiq_historical_run_ratings_master_v1.csv",
    "LIVE_GOVERNED_BOARD": DATA / "edgeiq_live_runner_board_governed_v1.csv",
    "V7_PROBABILITY_RESEARCH_ARTIFACT": DATA / "edgeiq_probability_engine_v7.csv",
    "LIVE_FACTOR_SCORECARD": DATA / "edgeiq_live_runner_factor_scorecard_v2.csv",
    "RUNNER_DNA_V6_2": DATA / "edgeiq_runner_dna_v6_2.csv",
}

KEYWORDS = {
    "V6_1": ["v6_1", "v6 1", "performance_rating_v6_1", "historical_performance_rating_v6_1"],
    "V7_2G2": ["v7_2g2", "v7 2g2", "v7_2", "guarded_display"],
    "PROBABILITY": ["probability", "win_pct", "softmax", "temperature", "normalisation", "calibration"],
    "PRICING": ["fair_price", "rated_price", "pricing", "price", "edge_pct"],
    "RATING": ["rating", "projection", "runner_score", "total_rating_points", "strength_adjusted"],
    "DNA": ["dna", "runner_dna"],
    "FORM": ["form", "last_start", "history", "trajectory"],
    "PACE": ["pace", "run_style", "leader", "race_shape", "speed_map"],
    "BIAS": ["bias", "barrier", "rail", "lane", "inside", "outside"],
    "MARKET": ["market", "sp", "tab", "live_price"],
    "CONNECTIONS": ["connection", "trainer", "jockey", "combo"],
    "SECTIONAL": ["sectional", "last600", "last400", "speed_rating", "race_time"],
}

POST_RACE_TERMS = ["finish", "finish_pos", "finish_position", "won", "placed", "margin", "result", "actual", "inrun", "pos_800", "pos_400", "raw_in_run", "sp", "performance_rating"]
MISSING_SIGNALS = ["pace", "leader_profile", "track_bias", "weather", "timing", "sectionals", "connections", "market_intelligence", "first_up_profile", "distance_profile", "class_profile"]
ID_TERMS = ["date", "track", "race", "horse", "runner", "key", "url", "source", "built", "status", "name", "jockey", "trainer", "class", "condition", "reason", "notes"]
PLACEHOLDERS = {"", "-", "--", "---", "nan", "none", "null", "n/a", "na", "unknown", "not loaded", "source gap", "undefined"}
MAX_SCAN_ROWS = 250000

csv.field_size_limit(1024 * 1024 * 128)

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return re.sub(r"[^a-z0-9]+", "_", clean(v).lower()).strip("_")

def parse_num(v):
    t = clean(v).replace("$", "").replace(",", "")
    if t.lower() in PLACEHOLDERS:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    if not m:
        return None
    try: return float(m.group(0))
    except Exception: return None


def pct(a, b):
    return round((a / b) * 100, 4) if b else 0.0
def parse_date(v):
    t = clean(v)
    if not t: return None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d%b%y", "%d%b%Y", "%d %b %Y", "%d %b %y"]:
        try:
            from datetime import datetime as dt
            return dt.strptime(t[:11].replace('.', ''), fmt).date()
        except Exception:
            pass
    return None

def read_header(path):
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return csv.DictReader(f).fieldnames or []
    except Exception:
        return []

def write_csv(path, rows):
    fields, seen = [], set()
    for row in rows:
        for key in row:
            if key not in seen:
                fields.append(key); seen.add(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)

def file_rel(path):
    try: return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception: return str(path).replace("\\", "/")

def keyword_hits(text):
    n = norm(text)
    hits = []
    for family, words in KEYWORDS.items():
        for w in words:
            if norm(w) in n:
                hits.append(family); break
    return sorted(set(hits))

def leakage_terms(text):
    n = norm(text)
    return sorted({t for t in POST_RACE_TERMS if norm(t) in n})

def infer_purpose(path, headers=None):
    text = path.name + " " + " ".join(headers or [])
    hits = keyword_hits(text)
    if path.suffix.lower() == ".py":
        if "build" in path.name: role = "BUILDER_SCRIPT"
        elif "audit" in path.name: role = "AUDIT_SCRIPT"
        else: role = "SCRIPT"
    else:
        if "summary" in path.name: role = "SUMMARY_OUTPUT"
        elif "audit" in path.name: role = "AUDIT_OUTPUT"
        elif "replay" in path.name: role = "REPLAY_DATA"
        elif "live" in path.name or "current" in path.name: role = "CURRENT_OR_LIVE_DATA"
        else: role = "DATA_SOURCE_OR_OUTPUT"
    if "PROBABILITY" in hits: purpose = "probability/calibration"
    elif "PRICING" in hits: purpose = "pricing/fair price"
    elif "V6_1" in hits or "RATING" in hits: purpose = "rating/projection"
    elif "DNA" in hits: purpose = "DNA/factor model"
    elif "PACE" in hits: purpose = "pace/race shape"
    else: purpose = "supporting/unknown"
    return role, purpose, hits


def build_inventory():
    rows = []
    candidates = []
    for path in DATA.glob("*.csv"):
        h = read_header(path)
        hits = keyword_hits(path.name + " " + " ".join(h))
        if hits:
            candidates.append((path, h, hits))
    for path in SCRIPTS.glob("*.py"):
        name_hits = keyword_hits(path.name)
        text_hits = []
        try:
            txt = path.read_text(encoding="utf-8", errors="ignore")[:120000]
            text_hits = keyword_hits(txt)
        except Exception:
            txt = ""
        hits = sorted(set(name_hits + text_hits))
        if hits:
            candidates.append((path, [], hits))
    for path, headers, hits in candidates:
        role, purpose, _ = infer_purpose(path, headers)
        script_text = ""
        outputs = []
        transforms = []
        if path.suffix.lower() == ".py":
            try:
                script_text = path.read_text(encoding="utf-8", errors="ignore")[:200000]
                outputs = sorted(set(re.findall(r"edgeiq_[A-Za-z0-9_\-]+\.(?:csv|txt)", script_text)))[:40]
                for pat, label in [(r"softmax|temperature|exp\(", "SOFTMAX_OR_TEMPERATURE"), (r"normalis|normalize|sum.*100", "NORMALISATION"), (r"multiplier|weight|weighted|factor", "WEIGHTING_OR_MULTIPLIER"), (r"cap|floor|clip|min\(|max\(", "CAP_OR_FLOOR"), (r"rank|sort", "RANK_TRANSLATION"), (r"margin|finish|won|placed", "RESULT_FIELD_USAGE")]:
                    if re.search(pat, script_text, re.I): transforms.append(label)
            except Exception:
                pass
        matched_cols = [c for c in headers if keyword_hits(c)]
        feeds = []
        if any(h in hits for h in ["V6_1", "RATING"]): feeds.append("V6_1_OR_RATING")
        if "V7_2G2" in hits: feeds.append("V7_2G2")
        if "PROBABILITY" in hits: feeds.append("PROBABILITY")
        if "PRICING" in hits: feeds.append("PRICING")
        rows.append({
            "source_file": file_rel(path), "source_type": "SCRIPT" if path.suffix.lower()==".py" else "CSV",
            "role": role, "purpose_inferred": purpose, "feeds_pipeline": "|".join(feeds),
            "matched_families": "|".join(hits), "matched_column_count": len(matched_cols),
            "matched_columns_sample": "|".join(matched_cols[:60]), "all_column_count": len(headers),
            "transformations_detected": "|".join(sorted(set(transforms))), "outputs_referenced_sample": "|".join(outputs[:25]),
            "normalisation_detected": "YES" if "NORMALISATION" in transforms else "NO",
            "weighting_detected": "YES" if "WEIGHTING_OR_MULTIPLIER" in transforms else "NO",
            "cap_floor_detected": "YES" if "CAP_OR_FLOOR" in transforms else "NO",
            "post_race_terms_detected": "|".join(leakage_terms(path.name + " " + " ".join(headers) + " " + script_text[:50000])),
            "file_size_mb": round(path.stat().st_size / 1048576, 4),
            "research_audit_note": "inventory only; no production modification",
        })
    summary = []
    by_family = defaultdict(list)
    for r in rows:
        for fam in r["matched_families"].split("|") if r["matched_families"] else []:
            by_family[fam].append(r)
    for fam, items in sorted(by_family.items()):
        summary.append({"family": fam, "source_count": len(items), "script_count": sum(1 for x in items if x["source_type"]=="SCRIPT"), "csv_count": sum(1 for x in items if x["source_type"]=="CSV"), "transforming_script_count": sum(1 for x in items if x["transformations_detected"]), "post_race_term_source_count": sum(1 for x in items if x["post_race_terms_detected"]), "top_sources": " | ".join(x["source_file"] for x in sorted(items, key=lambda z: z["file_size_mb"], reverse=True)[:8])})
    write_csv(OUT_INV, rows)
    write_csv(OUT_INV_SUM, summary)
    return rows, summary

def numeric_profile(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return {"min":"", "max":"", "mean":"", "std":"", "outlier_count":0, "impossible_count":0}
    mu = mean(vals)
    sd = pstdev(vals) if len(vals) > 1 else 0
    out = 0
    if sd > 0:
        out = sum(1 for v in vals if abs(v - mu) > 4 * sd)
    impossible = sum(1 for v in vals if math.isinf(v) or math.isnan(v) or abs(v) > 1000000)
    return {"min": min(vals), "max": max(vals), "mean": round(mu,4), "std": round(sd,4), "outlier_count": out, "impossible_count": impossible}

def data_quality_for_file(label, path):
    rows = []
    if not path.exists():
        return [{"source_label":label, "source_file":file_rel(path), "factor":"__FILE__", "rows_scanned":0, "quality_verdict":"SOURCE_MISSING"}]
    headers = read_header(path)
    stats = {h: {"nonblank":0, "numeric":0, "values":[], "examples":[]} for h in headers}
    row_count = 0
    key_seen = Counter()
    dates = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_count += 1
                key = "|".join(clean(row.get(c)) for c in ["race_date","track","race_no","horse"] if c in row)
                if key.strip("|"): key_seen[key] += 1
                d = parse_date(row.get("race_date") or row.get("meeting_date") or row.get("date"))
                if d: dates.append(d)
                for h in headers:
                    v = clean(row.get(h))
                    if v.lower() not in PLACEHOLDERS:
                        stats[h]["nonblank"] += 1
                        if len(stats[h]["examples"]) < 4 and v not in stats[h]["examples"]: stats[h]["examples"].append(v[:50])
                    x = parse_num(v)
                    if x is not None:
                        stats[h]["numeric"] += 1
                        if len(stats[h]["values"]) < MAX_SCAN_ROWS: stats[h]["values"].append(x)
                if row_count >= MAX_SCAN_ROWS and path.stat().st_size > 150_000_000:
                    break
    except Exception as e:
        return [{"source_label":label, "source_file":file_rel(path), "factor":"__READ_ERROR__", "rows_scanned":row_count, "quality_verdict":"READ_ERROR", "notes":str(e)}]
    dup_count = sum(c-1 for c in key_seen.values() if c > 1)
    for h in headers:
        non = stats[h]["nonblank"]; miss = row_count - non
        prof = numeric_profile(stats[h]["values"])
        leak = leakage_terms(h)
        impossible = prof["impossible_count"]
        if h.lower().endswith("probability") or "probability" in h.lower() or h.lower().endswith("win_pct"):
            impossible += sum(1 for v in stats[h]["values"] if v < 0 or v > 100)
        if "price" in h.lower():
            impossible += sum(1 for v in stats[h]["values"] if v <= 0 or v > 10000)
        if "rating" in h.lower() or "score" in h.lower():
            impossible += sum(1 for v in stats[h]["values"] if v < -100 or v > 300)
        risk = "HIGH_POST_RACE_OR_RESULT_DERIVED" if leak else "LOW_UNKNOWN"
        if any(t in h.lower() for t in ["prior", "previous", "last_start"]): risk = "LOW_IF_PRIOR_DATE_GUARDED"
        completeness = pct(non, row_count)
        verdict = "OK"
        if completeness < 50: verdict = "LOW_COMPLETENESS"
        if impossible: verdict = "IMPOSSIBLE_VALUES_FOUND"
        if leak: verdict = "LEAKAGE_REVIEW_REQUIRED"
        rows.append({
            "source_label":label, "source_file":file_rel(path), "factor":h, "rows_scanned":row_count,
            "completeness_pct": completeness, "missing_pct": round(100-completeness,4), "duplicate_key_rows_in_file": dup_count,
            "stale_pct": "", "impossible_value_count": impossible, "outlier_count": prof["outlier_count"],
            "min": prof["min"], "max": prof["max"], "mean": prof["mean"], "std": prof["std"],
            "temporal_min_date": min(dates).isoformat() if dates else "", "temporal_max_date": max(dates).isoformat() if dates else "",
            "lookahead_leakage_risk": risk, "source_confidence": "HIGH" if row_count and completeness >= 80 and not impossible else "MEDIUM" if row_count else "LOW",
            "example_values": "|".join(stats[h]["examples"]), "quality_verdict": verdict,
        })
    return rows

def build_data_quality():
    rows = []
    for label, path in MAIN_FILES.items(): rows.extend(data_quality_for_file(label, path))
    summary = []
    for label in sorted(set(r.get("source_label") for r in rows)):
        subset = [r for r in rows if r.get("source_label") == label]
        summary.append({"source_label":label, "factor_count":len(subset), "ok_count":sum(1 for r in subset if r.get("quality_verdict")=="OK"), "low_completeness_count":sum(1 for r in subset if r.get("quality_verdict")=="LOW_COMPLETENESS"), "leakage_review_count":sum(1 for r in subset if r.get("quality_verdict")=="LEAKAGE_REVIEW_REQUIRED"), "impossible_value_factor_count":sum(1 for r in subset if r.get("quality_verdict")=="IMPOSSIBLE_VALUES_FOUND"), "avg_completeness_pct":round(mean([float(r.get("completeness_pct") or 0) for r in subset]),4) if subset else 0})
    write_csv(OUT_QUALITY, rows); write_csv(OUT_QUALITY_SUM, summary)
    return rows, summary


def is_factor_col(col):
    n = norm(col)
    if any(t in n for t in ID_TERMS): return False
    if any(t in n for t in ["finish_position", "finish_pos", "finish_pos_raw", "won", "placed"]): return False
    return True

def pearson(xs, ys):
    pairs = [(x,y) for x,y in zip(xs,ys) if x is not None and y is not None]
    if len(pairs) < 20: return ""
    xvals, yvals = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = mean(xvals), mean(yvals)
    sx, sy = pstdev(xvals), pstdev(yvals)
    if sx == 0 or sy == 0: return ""
    return round(sum((x-mx)*(y-my) for x,y in pairs)/(len(pairs)*sx*sy), 4)

def load_v6_factor_rows():
    path = MAIN_FILES["V6_1_HISTORICAL_PERFORMANCE_RATING"]
    rows = []
    if not path.exists(): return rows, []
    headers = read_header(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            finish = parse_num(r.get("finish_position") or r.get("finish_pos"))
            if finish is None: continue
            key_parts = [clean(r.get(c)) for c in ["race_date", "track", "distance", "race_class_clean", "race_name"]]
            if not key_parts[0] or not key_parts[1]: continue
            r["__race_key"] = "|".join(key_parts)
            r["__won"] = 1 if finish == 1 else 0
            r["__placed"] = 1 if finish <= 3 else 0
            rows.append(r)
            if len(rows) >= MAX_SCAN_ROWS: break
    return rows, headers

def rank_by_factor(groups, factor):
    race_count = 0; runner_count = 0; top1 = 0; top3 = 0; move_vals = []
    base_top1 = 0; base_top3 = 0
    for key, rows in groups.items():
        vals = [(parse_num(r.get(factor)), r) for r in rows]
        vals = [(v,r) for v,r in vals if v is not None]
        if len(vals) < 3: continue
        if sum(1 for _,r in vals if r.get("__won") == 1) != 1: continue
        race_count += 1; runner_count += len(vals)
        ranked = sorted(vals, key=lambda x: (-x[0], clean(x[1].get("horse"))))
        if ranked[0][1].get("__won") == 1: top1 += 1
        if any(r.get("__won") == 1 for _,r in ranked[:3]): top3 += 1
        base_vals = [(parse_num(r.get("performance_rating_v6_1_research")), r) for _,r in vals]
        base_vals = [(v,r) for v,r in base_vals if v is not None]
        if len(base_vals) >= 3:
            base_ranked = sorted(base_vals, key=lambda x: (-x[0], clean(x[1].get("horse"))))
            if base_ranked[0][1].get("__won") == 1: base_top1 += 1
            if any(r.get("__won") == 1 for _,r in base_ranked[:3]): base_top3 += 1
            ranks_a = {id(r):i+1 for i,(_,r) in enumerate(ranked)}
            ranks_b = {id(r):i+1 for i,(_,r) in enumerate(base_ranked)}
            common = set(ranks_a) & set(ranks_b)
            if common: move_vals.append(mean(abs(ranks_a[i]-ranks_b[i]) for i in common))
    return race_count, runner_count, pct(top1, race_count), pct(top3, race_count), pct(base_top1, race_count), pct(base_top3, race_count), round(mean(move_vals),4) if move_vals else ""

def build_factor_importance():
    rows, headers = load_v6_factor_rows()
    groups = defaultdict(list)
    for r in rows: groups[r["__race_key"]].append(r)
    factor_cols = []
    for h in headers:
        if is_factor_col(h):
            numeric_count = sum(1 for r in rows[:5000] if parse_num(r.get(h)) is not None)
            if numeric_count >= 100: factor_cols.append(h)
    out = []
    wins = [r.get("__won") for r in rows]
    places = [r.get("__placed") for r in rows]
    final_rating_vals = [parse_num(r.get("performance_rating_v6_1_research")) for r in rows]
    for col in factor_cols:
        vals = [parse_num(r.get(col)) for r in rows]
        race_count, runner_count, t1, t3, base_t1, base_t3, avg_move = rank_by_factor(groups, col)
        corr_win = pearson(vals, wins)
        corr_place = pearson(vals, places)
        corr_final = pearson(vals, final_rating_vals)
        leak = leakage_terms(col)
        out.append({"factor":col, "source_file":file_rel(MAIN_FILES["V6_1_HISTORICAL_PERFORMANCE_RATING"]), "races_tested":race_count, "runners_tested":runner_count, "top1_win_pct_by_factor":t1, "top3_win_pct_by_factor":t3, "final_rating_top1_baseline_pct":base_t1, "final_rating_top3_baseline_pct":base_t3, "top1_delta_vs_final_rating":round(t1-base_t1,4) if race_count else "", "top3_delta_vs_final_rating":round(t3-base_t3,4) if race_count else "", "average_rank_movement_vs_final_rating":avg_move, "correlation_with_winners":corr_win, "correlation_with_placegetters":corr_place, "correlation_with_final_rating":corr_final, "redundancy_flag": "HIGH_FINAL_RATING_OVERLAP" if corr_final != "" and abs(float(corr_final)) >= 0.85 else "", "leakage_terms": "|".join(leak), "importance_verdict": "POST_RACE_FACTOR_REVIEW" if leak else "USEFUL_SIGNAL" if corr_win != "" and abs(float(corr_win)) >= 0.05 else "LOW_VALUE_OR_WEAK_SIGNAL"})
    summary = []
    if out:
        top = sorted(out, key=lambda r: float(r["correlation_with_winners"] or 0), reverse=True)[:15]
        summary.append({"metric":"factor_count", "value":len(out)})
        summary.append({"metric":"races_grouped", "value":len(groups)})
        summary.append({"metric":"high_final_rating_overlap_count", "value":sum(1 for r in out if r["redundancy_flag"])})
        summary.append({"metric":"post_race_factor_review_count", "value":sum(1 for r in out if r["importance_verdict"]=="POST_RACE_FACTOR_REVIEW")})
        summary.append({"metric":"top_winner_correlated_factors", "value":" | ".join(f"{r['factor']} corr={r['correlation_with_winners']}" for r in top)})
    write_csv(OUT_IMPORTANCE, out); write_csv(OUT_IMPORTANCE_SUM, summary)
    return out, summary, rows

def build_double_count(importance_rows, sample_rows):
    factor_cols = [r["factor"] for r in importance_rows if r.get("factor")]
    values = {c: [parse_num(r.get(c)) for r in sample_rows[:50000]] for c in factor_cols[:120]}
    pairs = []
    for i, a in enumerate(factor_cols[:120]):
        for b in factor_cols[i+1:120]:
            corr = pearson(values[a], values[b])
            if corr != "" and abs(float(corr)) >= 0.85:
                pairs.append({"factor_a":a, "factor_b":b, "correlation":corr, "double_count_risk":"HIGH_CORRELATED_CLUSTER", "relationship_inferred":"numeric factors move together; review derivation before combined weighting"})
    token_groups = defaultdict(list)
    for c in factor_cols:
        tokens = [t for t in norm(c).split("_") if t and t not in {"v1","v2","v3","v4","v5","v6","6","1","research"}]
        key = "_".join(tokens[:2]) if tokens else c
        token_groups[key].append(c)
    for key, cols in token_groups.items():
        if len(cols) >= 3:
            pairs.append({"factor_a":"|".join(cols[:20]), "factor_b":"TOKEN_CLUSTER", "correlation":"", "double_count_risk":"POSSIBLE_SEMANTIC_DUPLICATION", "relationship_inferred":f"shared factor-name cluster={key}"})
    summary = [{"metric":"high_correlation_pairs", "value":sum(1 for r in pairs if r["double_count_risk"]=="HIGH_CORRELATED_CLUSTER")}, {"metric":"semantic_clusters", "value":sum(1 for r in pairs if r["double_count_risk"]=="POSSIBLE_SEMANTIC_DUPLICATION")}, {"metric":"review_priority", "value":"performance_rating/finish/margin/class_quality/field_size clusters first"}]
    write_csv(OUT_DOUBLE, pairs); write_csv(OUT_DOUBLE_SUM, summary)
    return pairs, summary


def build_leakage_audit(inventory_rows, quality_rows, importance_rows):
    rows = []
    for r in quality_rows:
        terms = leakage_terms(r.get("factor", ""))
        if terms:
            severity = "HIGH" if any(t in terms for t in ["finish", "finish_pos", "finish_position", "won", "placed", "margin", "inrun", "pos_800", "pos_400"]) else "MEDIUM"
            rows.append({"audit_scope":"COLUMN", "source_file":r.get("source_file"), "field_or_script":r.get("factor"), "risk_type":"POST_RACE_OR_RESULT_DERIVED_FIELD", "risk_terms":"|".join(terms), "severity":severity, "status":"REVIEW_REQUIRED", "details":"Safe only for retrospective performance rating or strictly prior historical feature; unsafe as same-race predictive input."})
    for r in inventory_rows:
        terms = r.get("post_race_terms_detected", "")
        if terms and ("PROBABILITY" in r.get("matched_families", "") or "PRICING" in r.get("matched_families", "") or "V7_2G2" in r.get("matched_families", "")):
            rows.append({"audit_scope":"PIPELINE_SOURCE", "source_file":r.get("source_file"), "field_or_script":"SCRIPT_OR_FILE", "risk_type":"POST_RACE_TERMS_IN_PROBABILITY_PRICING_CONTEXT", "risk_terms":terms, "severity":"HIGH", "status":"ASOF_GUARD_REQUIRED", "details":"Probability/pricing path references terms that may be post-race; verify strict prior-date use before promotion."})
    # Known forensic result from recent research: same-race V6.1 performance ratings caused 100% top-pick leakage when used directly.
    rows.append({"audit_scope":"KNOWN_REPLAY_FINDING", "source_file":"edgeiq_weight_context_stage2_replay_v1_report.txt", "field_or_script":"performance_rating_v6_1_research", "risk_type":"SAME_RACE_PERFORMANCE_RATING_LEAKAGE", "risk_terms":"finish|margin|performance_rating", "severity":"HIGH", "status":"CONFIRMED_RISK_IF_USED_SAME_RACE", "details":"Prior replay work showed same-race V6.1 performance rating behaved as post-race outcome, not pre-race prediction; strict prior-date use is mandatory."})
    # Check explicit safeguards in recent prior replays if outputs exist.
    for audit_file in [DATA/"edgeiq_pace_pressure_signal_replay_v1_leakage_audit.csv", DATA/"edgeiq_leader_profile_signal_replay_v1_leakage_audit.csv"]:
        if audit_file.exists():
            audits = read_header(audit_file)
            try:
                for ar in read_csv(audit_file):
                    rows.append({"audit_scope":"RECENT_PRIOR_REPLAY_AUDIT", "source_file":file_rel(audit_file), "field_or_script":ar.get("audit_item", ""), "risk_type":ar.get("leakage_risk", "DATE_GUARD"), "risk_terms":"", "severity":"LOW" if ar.get("status")=="PASS" else "HIGH", "status":ar.get("status", ""), "details":ar.get("details", "")})
            except Exception:
                pass
    summary = [{"metric":"total_leakage_items", "value":len(rows)}, {"metric":"high_severity_items", "value":sum(1 for r in rows if r.get("severity")=="HIGH")}, {"metric":"confirmed_same_race_performance_rating_risk", "value":"YES"}, {"metric":"blocking_status", "value":"DATA_INTEGRITY_RISK_NOT_BLOCKED_IF_PRIOR_DATE_GUARDED"}]
    write_csv(OUT_LEAK, rows); write_csv(OUT_LEAK_SUM, summary)
    return rows, summary

def build_missing_signal(inventory_rows, quality_rows):
    rows = []
    inv_text = " ".join((r.get("source_file","")+" "+r.get("matched_columns_sample","")+" "+r.get("matched_families","")).lower() for r in inventory_rows)
    v6_headers = [r.get("factor", "") for r in quality_rows if r.get("source_label") == "V6_1_HISTORICAL_PERFORMANCE_RATING"]
    v6_text = " ".join(v6_headers).lower()
    definitions = {
        "pace": ["pace", "race_shape", "run_style", "leader"],
        "leader_profile": ["leader", "run_style"],
        "track_bias": ["bias", "rail", "barrier", "lane", "inside", "outside"],
        "weather": ["weather", "wind", "rainfall", "temperature", "humidity"],
        "timing": ["race_time", "benchmark_time", "time"],
        "sectionals": ["sectional", "last600", "last400", "last200"],
        "connections": ["connection", "trainer", "jockey", "combo"],
        "market_intelligence": ["market", "sp", "live_price", "tab"],
        "first_up_profile": ["first_up", "fresh", "spell"],
        "distance_profile": ["distance", "dist"],
        "class_profile": ["class", "race_class"],
    }
    for sig, terms in definitions.items():
        in_estate = any(t in inv_text for t in terms)
        in_v6 = any(t in v6_text for t in terms)
        if in_v6:
            status = "REPRESENTED_IN_V6_1_CORE"
        elif in_estate:
            status = "AVAILABLE_IN_DATA_ESTATE_NOT_CORE_V6_1"
        else:
            status = "SOURCE_NOT_FOUND_OR_THIN"
        priority = "HIGH" if status != "REPRESENTED_IN_V6_1_CORE" and sig in ["pace", "leader_profile", "track_bias", "sectionals", "connections", "market_intelligence"] else "MEDIUM"
        rows.append({"signal_family":sig, "represented_in_v6_1_core": "YES" if in_v6 else "NO", "available_elsewhere_in_data_estate": "YES" if in_estate else "NO", "status":status, "priority":priority, "recommended_action": "build strict prior/as-of research replay" if in_estate and not in_v6 else "audit source acquisition" if not in_estate else "keep and validate", "notes":"No production change made."})
    summary = [{"metric":"missing_or_not_core_signal_count", "value":sum(1 for r in rows if r["represented_in_v6_1_core"]=="NO")}, {"metric":"available_elsewhere_count", "value":sum(1 for r in rows if r["available_elsewhere_in_data_estate"]=="YES" and r["represented_in_v6_1_core"]=="NO")}, {"metric":"highest_priority_additions", "value":"pace/leader_profile, track_bias, sectionals, connections, market_intelligence"}]
    write_csv(OUT_MISSING, rows); write_csv(OUT_MISSING_SUM, summary)
    return rows, summary

def final_verdict(leak_rows, missing_rows, double_rows, importance_rows):
    high_leak = sum(1 for r in leak_rows if r.get("severity") == "HIGH")
    high_corr = sum(1 for r in double_rows if r.get("double_count_risk") == "HIGH_CORRELATED_CLUSTER")
    missing_core = sum(1 for r in missing_rows if r.get("represented_in_v6_1_core") == "NO" and r.get("priority") == "HIGH")
    post_race_factors = sum(1 for r in importance_rows if r.get("importance_verdict") == "POST_RACE_FACTOR_REVIEW")
    if high_leak >= 20 and post_race_factors >= 3:
        return "DATA_INTEGRITY_RISK"
    if high_leak >= 100:
        return "LEAKAGE_RISK_BLOCKED"
    if missing_core >= 4 or high_corr >= 10:
        return "MAJOR_REDESIGN_REQUIRED"
    if high_leak or missing_core:
        return "MINOR_REFINEMENT_REQUIRED"
    return "PRODUCTION_READY"

def write_report(inv_sum, quality_sum, importance_rows, double_rows, leak_rows, missing_rows, verdict):
    top_imp = sorted([r for r in importance_rows if r.get("correlation_with_winners") not in ["", None]], key=lambda r: float(r["correlation_with_winners"]), reverse=True)[:10]
    low_imp = sorted([r for r in importance_rows if r.get("correlation_with_winners") not in ["", None]], key=lambda r: abs(float(r["correlation_with_winners"])))[:10]
    dup_top = [r for r in double_rows if r.get("double_count_risk") == "HIGH_CORRELATED_CLUSTER"][:15]
    lines = [
        "EDGEIQ_PERFORMANCE_RATING_ENGINE_AUDIT_V1_REPORT",
        f"built_at={datetime.now(timezone.utc).isoformat()}",
        "scope=research forensic audit only",
        "production_changed=NO", "pricing_changed=NO", "v6_1_changed=NO", "v7_2g2_changed=NO", "ui_changed=NO", "",
        "FINAL_VERDICT", verdict, "",
        "1. Are we using the correct data?",
        "Partly. The V6.1 historical performance rating uses appropriate post-race performance ingredients for retrospective run assessment, especially finish/margin/class/field context. It is not appropriate as a same-race predictive feature unless shifted to a strictly prior start.", "",
        "2. Are we using it correctly?",
        "Correct for historical performance scoring; risky for predictive replay if the same-race performance rating is used. Recent prior-rating replays confirmed strict prior-date guards are mandatory.", "",
        "3. What factors are strongest?",
        "Top winner-correlated factors: " + " | ".join(f"{r['factor']} corr={r['correlation_with_winners']}" for r in top_imp), "",
        "4. What factors add little value?",
        "Weakest sampled factors: " + " | ".join(f"{r['factor']} corr={r['correlation_with_winners']}" for r in low_imp), "",
        "5. What factors are duplicated?",
        "High-correlation pairs/clusters found: " + str(sum(1 for r in double_rows if r.get("double_count_risk") == "HIGH_CORRELATED_CLUSTER")) + ". Examples: " + " | ".join(f"{r.get('factor_a')}~{r.get('factor_b')} corr={r.get('correlation')}" for r in dup_top), "",
        "6. Is there hidden leakage?",
        "There is confirmed leakage risk if same-race V6.1 performance ratings or result-derived columns enter predictive ranking. The rating file itself is retrospective; probability/pricing promotion must use only prior/as-of transformed versions.", "",
        "7. What important information is missing?",
        "Missing or not core V6.1 signals: " + " | ".join(r['signal_family'] for r in missing_rows if r['represented_in_v6_1_core']=='NO'), "",
        "8. What should be removed?",
        "Do not remove retrospective finish/margin logic from the performance-rating warehouse. Remove or quarantine any same-race use of performance_rating_v6_1_research, finish, margin, won/placed, in-run, or SP fields from predictive/probability paths unless explicitly prior-date shifted.", "",
        "9. What should be added?",
        "Add separate prior/as-of feature feeds for leader profile/pace pressure, track bias, sectional/timing profile, connections, and market intelligence. Keep them separate from the retrospective performance score until replay-proven.", "",
        "10. Is the engine structurally sound?",
        "Structurally sound as a historical performance-rating engine. Not structurally complete as a predictive rating engine: it needs clearer separation between retrospective performance, prior predictive features, and probability/pricing conversion.", "",
        "SUMMARY_COUNTS",
        f"inventory_families={len(inv_sum)}", f"quality_sources={len(quality_sum)}", f"importance_factors={len(importance_rows)}", f"double_count_items={len(double_rows)}", f"leakage_items={len(leak_rows)}", f"missing_signal_items={len(missing_rows)}", "",
        "RECOMMENDED_NEXT_STEPS",
        "1. Create a strict as-of rating spine: target race plus latest prior performance rating and prior-only factor snapshots.",
        "2. Split labels: RETROSPECTIVE_PERFORMANCE_RATING vs PRE_RACE_PREDICTIVE_RATING.",
        "3. Build factor ablation replay on the as-of spine before adding new complexity.",
        "4. Promote no rating/probability change until leakage audit passes with zero same-race result-derived fields.",
    ]
    REPORT.write_text("\n".join(lines)+"\n", encoding="utf-8")

def main():
    inv, inv_sum = build_inventory()
    quality, quality_sum = build_data_quality()
    importance, importance_sum, sample_rows = build_factor_importance()
    double_rows, double_sum = build_double_count(importance, sample_rows)
    leak_rows, leak_sum = build_leakage_audit(inv, quality, importance)
    missing_rows, missing_sum = build_missing_signal(inv, quality)
    verdict = final_verdict(leak_rows, missing_rows, double_rows, importance)
    write_report(inv_sum, quality_sum, importance, double_rows, leak_rows, missing_rows, verdict)
    print(REPORT)

if __name__ == "__main__":
    main()

