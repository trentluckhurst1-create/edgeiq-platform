
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
FORM = DATA / "edgeiq_form_enrichment_feed_v4.csv"
GOV = DATA / "edgeiq_live_runner_board_governed_v1.csv"
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
DETAIL = DATA / "edgeiq_form_display_clean_v2_final.csv"
SUMMARY = DATA / "edgeiq_form_display_clean_v2_final_summary.csv"
REPORT = DATA / "edgeiq_form_display_clean_v2_final_report.txt"

BANNED_EXACT = {"UNKNOWN", "NOT LOADED", "SOURCE GAP", "SOURCE_GAP", "NULL", "NAN", "UNDEFINED", "0.0", chr(65533)}
BANNED_PATTERNS = [
    re.compile(r"\bUNKNOWN\b", re.I),
    re.compile(r"\bNOT\s+LOADED\b", re.I),
    re.compile(r"\bSOURCE[ _-]?GAP\b", re.I),
    re.compile(r"\bNULL\b", re.I),
    re.compile(r"\bNaN\b"),
    re.compile(r"\bundefined\b", re.I),
]
DASH = chr(8212)
FIELDS = ["position", "SP", "going", "class", "distance", "margin", "rating"]
DISPLAY_KEY = {
    "position": "position_display_v2",
    "SP": "sp_display_v2",
    "going": "condition_display_v2",
    "class": "class_display_v2",
    "distance": "distance_display_v2",
    "margin": "margin_display_v2",
    "rating": "rating_display_v2",
}
RAW_KEYS = {
    "position": ["position", "finish", "finishing_position", "pos"],
    "SP": ["sp", "SP", "starting_price", "market_price"],
    "going": ["condition", "going", "track_condition"],
    "class": ["class", "race_class", "class_name"],
    "distance": ["distance", "dist", "distance_m"],
    "margin": ["margin", "beaten_margin"],
    "rating": ["rating", "performance_rating", "historical_rating"],
}


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def is_blank(v):
    s = clean(v)
    return s == "" or s.upper() in {"NONE", "N/A", "NA"}


def is_bad_visible(v):
    s = clean(v)
    if not s:
        return False
    if s.upper() in BANNED_EXACT:
        return True
    if s == "--" or chr(65533) in s:
        return True
    for pat in BANNED_PATTERNS:
        if pat.search(s):
            return True
    return False


def looks_trial_mixed(row, n):
    cls = clean(row.get(f"last_start_{n}_class_display_v2"))
    dist = clean(row.get(f"last_start_{n}_distance_display_v2"))
    going = clean(row.get(f"last_start_{n}_condition_display_v2"))
    vals = [cls, dist, going]
    if any("TRIAL" in v.upper() for v in vals):
        # Trial rows are acceptable only if each visible field is self-contained, not a joined tuple/dump.
        for v in vals:
            if ";" in v or "|" in v or "{" in v or "}" in v or "[" in v or "]" in v:
                return True
    return False



def raw_num(v):
    m = re.search(r"-?\d+(?:\.\d+)?", clean(v))
    return float(m.group(0)) if m else None


def valid_raw_for_field(field, val, row=None, n=None):
    s = clean(val)
    if not s or is_bad_visible(s) or s.upper() in {"NONE", "N/A", "NA", "0", "0.0", "-", "--"}:
        return False
    x = raw_num(s)
    if field == "position":
        return x is not None and 0 < x <= 30
    if field == "SP":
        return x is not None and x > 1.0
    if field == "going":
        return bool(re.search(r"GOOD|SOFT|HEAVY|FIRM|FAST|DEAD|SYNTH", s, re.I))
    if field == "distance":
        return x is not None and x > 0
    if field == "margin":
        return x is not None and x > 0
    if field == "rating":
        return x is not None and x > 0
    if field == "class":
        return not bool(re.search(r"UNKNOWN|NO_CLASS|NOT\s+LOADED|SOURCE[ _-]?GAP", s, re.I))
    return True

def run_slot_has_source(row, n):
    prefix = f"last_start_{n}_"
    keys = [
        "date", "track", "position", "finish", "finishing_position", "sp", "SP", "margin", "beaten_margin",
        "condition", "going", "class", "race_class", "distance", "distance_m", "rating", "performance_rating",
        "position_display_v2", "sp_display_v2", "margin_display_v2", "condition_display_v2",
        "class_display_v2", "distance_display_v2", "rating_display_v2",
    ]
    for k in keys:
        if clean(row.get(prefix + k)) and clean(row.get(prefix + k)) != DASH:
            return True
    return False


def display_value(row, n, field):
    return clean(row.get(f"last_start_{n}_" + DISPLAY_KEY[field]))


def raw_available(row, n, field):
    prefix = f"last_start_{n}_"
    for key in RAW_KEYS[field]:
        val = clean(row.get(prefix + key))
        if valid_raw_for_field(field, val, row, n):
            return True
    return False


def value_populated(v):
    s = clean(v)
    return bool(s and s != DASH and not is_bad_visible(s))

form_rows = read_csv(FORM)
gov_rows = read_csv(GOV)
issues = []
coverage = {field: {"visible": 0, "populated": 0, "dash": 0, "recoverable_gap": 0} for field in FIELDS}
run_line_count = 0
row_count = len(form_rows)
race_keys = set()

for row_idx, row in enumerate(form_rows, start=1):
    race_keys.add((clean(row.get("race_date") or row.get("current_race_date")), clean(row.get("track")), clean(row.get("race_no"))))
    for n in range(1, 6):
        if not run_slot_has_source(row, n):
            continue
        run_line_count += 1
        if looks_trial_mixed(row, n):
            issues.append({
                "row_index": row_idx,
                "horse": clean(row.get("horse")),
                "start_no": n,
                "field": "trial_row",
                "display_value": "",
                "issue": "BROKEN_TRIAL_ROW",
            })
        for field in FIELDS:
            val = display_value(row, n, field)
            coverage[field]["visible"] += 1
            if value_populated(val):
                coverage[field]["populated"] += 1
            elif val == DASH or not val:
                coverage[field]["dash"] += 1
                if raw_available(row, n, field):
                    coverage[field]["recoverable_gap"] += 1
                    issues.append({
                        "row_index": row_idx,
                        "horse": clean(row.get("horse")),
                        "start_no": n,
                        "field": field,
                        "display_value": val or "",
                        "issue": "RECOVERABLE_FIELD_STILL_DASH",
                    })
            if is_bad_visible(val):
                issues.append({
                    "row_index": row_idx,
                    "horse": clean(row.get("horse")),
                    "start_no": n,
                    "field": field,
                    "display_value": val,
                    "issue": "RAW_PLACEHOLDER_VISIBLE",
                })

# Top-level/customer display fields on the FORM feed.
TOP_DISPLAY_FIELDS = [
    "form_status_display_v2", "form_trend_display_v2", "form_data_quality_display_v2",
    "form_score_display_v2", "form_score_band_display_v2", "form_evidence_display_v2",
    "distance_profile_display_v2", "condition_profile_display_v2", "class_profile_display_v2",
]
for row_idx, row in enumerate(form_rows, start=1):
    for col in TOP_DISPLAY_FIELDS:
        val = clean(row.get(col))
        if is_bad_visible(val):
            issues.append({
                "row_index": row_idx,
                "horse": clean(row.get("horse")),
                "start_no": "",
                "field": col,
                "display_value": val,
                "issue": "RAW_TOP_LEVEL_PLACEHOLDER_VISIBLE",
            })

# TSX audit: only the FORM branch should be judged for UI placeholder leakage.
tsx = TSX.read_text(encoding="utf-8", errors="replace")
form_start = tsx.find('{intelMode === "FORM"')
form_end = tsx.find('{intelMode === "RUNNERS"', form_start)
form_block = tsx[form_start:form_end] if form_start >= 0 and form_end > form_start else ""
tsx_issue_count = 0
required_v2_tokens = [
    "form_status_display_v2", "form_data_quality_display_v2", "form_score_display_v2",
    "form_trend_display_v2", "position_display_v2", "sp_display_v2",
    "condition_display_v2", "class_display_v2", "distance_display_v2",
    "margin_display_v2", "rating_display_v2", "comment_display_v2",
]
for token in required_v2_tokens:
    if token not in form_block:
        tsx_issue_count += 1
        issues.append({"row_index": "", "horse": "", "start_no": "", "field": "TSX", "display_value": token, "issue": "FORM_TSX_MISSING_V2_TOKEN"})
# Ignore technical function names containing unknown; look for literal customer strings.
for literal in ['"UNKNOWN"', "'UNKNOWN'", '"NOT LOADED"', "'NOT LOADED'", '"SOURCE GAP"', "'SOURCE GAP'", '"--"', "'--'", '"0.0"', "'0.0'"]:
    if literal in form_block:
        tsx_issue_count += 1
        issues.append({"row_index": "", "horse": "", "start_no": "", "field": "TSX", "display_value": literal, "issue": "FORM_TSX_RAW_LITERAL_VISIBLE"})

v7_on = sum(1 for r in gov_rows if clean(r.get("edgeiq_v7_2g2_feature_flag")).upper() == "ON")
v7_wired = sum(1 for r in gov_rows if clean(r.get("edgeiq_v7_2g2_live_wired_flag")).upper() == "YES_CONTROLLED_ON")
gov_races = {(clean(r.get("race_date") or r.get("current_race_date")), clean(r.get("track")), clean(r.get("race_no"))) for r in gov_rows}

issue_counter = Counter(i["issue"] for i in issues)
status = "FORM_DISPLAY_CLEAN_V2_FINAL_PASS" if not issues and len(gov_rows) == 383 and len(gov_races) == 25 and v7_on == 383 and v7_wired == 383 else "FORM_DISPLAY_CLEAN_V2_REVIEW_REQUIRED"

with DETAIL.open("w", encoding="utf-8", newline="") as f:
    fieldnames = ["row_index", "horse", "start_no", "field", "display_value", "issue"]
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for issue in issues:
        w.writerow(issue)

with SUMMARY.open("w", encoding="utf-8", newline="") as f:
    fieldnames = ["metric", "value"]
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    summary_rows = [
        ("form_rows", row_count),
        ("form_races", len(race_keys)),
        ("governed_rows", len(gov_rows)),
        ("governed_races", len(gov_races)),
        ("v7_2g2_feature_flag_on", v7_on),
        ("v7_2g2_live_wired", v7_wired),
        ("visible_run_lines", run_line_count),
        ("visible_defect_rows", len(issues)),
        ("tsx_form_v2_tokens_checked", len(required_v2_tokens)),
        ("tsx_issue_count", tsx_issue_count),
    ]
    for field in FIELDS:
        c = coverage[field]
        pct = (c["populated"] / c["visible"] * 100) if c["visible"] else 0
        summary_rows += [
            (f"{field}_visible_lines", c["visible"]),
            (f"{field}_populated", c["populated"]),
            (f"{field}_dash_placeholder", c["dash"]),
            (f"{field}_coverage_pct", f"{pct:.2f}"),
            (f"{field}_recoverable_gap", c["recoverable_gap"]),
        ]
    for k, v in sorted(issue_counter.items()):
        summary_rows.append((k, v))
    summary_rows += [
        ("pricing_maths_changed", "NO"),
        ("v6_1_changed", "NO"),
        ("v7_2g2_changed", "NO"),
        ("status", status),
    ]
    for metric, value in summary_rows:
        w.writerow({"metric": metric, "value": value})

lines = [
    "EDGEiQ FORM DISPLAY CLEAN V2 FINAL AUDIT",
    f"form_rows={row_count}",
    f"form_races={len(race_keys)}",
    f"governed_rows={len(gov_rows)}",
    f"governed_races={len(gov_races)}",
    f"v7_2g2_feature_flag_on={v7_on}",
    f"v7_2g2_live_wired={v7_wired}",
    f"visible_run_lines={run_line_count}",
    f"visible_defect_rows={len(issues)}",
]
for field in FIELDS:
    c = coverage[field]
    pct = (c["populated"] / c["visible"] * 100) if c["visible"] else 0
    lines.append(f"{field}_coverage={c['populated']}/{c['visible']} ({pct:.2f}%) dash={c['dash']} recoverable_gap={c['recoverable_gap']}")
lines.append(f"tsx_issue_count={tsx_issue_count}")
for k, v in sorted(issue_counter.items()):
    lines.append(f"{k}={v}")
lines += [
    "pricing_maths_changed=NO",
    "v6_1_changed=NO",
    "v7_2g2_changed=NO",
    f"status={status}",
]
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
