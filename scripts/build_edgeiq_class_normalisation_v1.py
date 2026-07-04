from __future__ import annotations

import csv
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDITS = ROOT / "outputs" / "audits"
AUDITS.mkdir(parents=True, exist_ok=True)

SRC = DATA / "edgeiq_official_runs_master_v1.csv"
OUT = DATA / "edgeiq_class_normalised_master_v1.csv"
AUDIT = AUDITS / "edgeiq_class_normalised_master_v1_audit.csv"

COND_RE = re.compile(r"\b(GOOD|SOFT|HEAVY|FIRM|SYNTHETIC|POLY|TAPETA)\s*([0-9]{0,2})\b", re.I)
BM_RE = re.compile(r"\b(?:BM|BENCH\s*MARK|BENCHMARK)\s*([0-9]{2,3})\b", re.I)
RTG_RE = re.compile(r"\bRTG\s*([0-9]{2,3})\+?\b", re.I)
ZERO_RTG_RE = re.compile(r"\b[-]?\s*([0-9]{2,3})\b")
CLASS_RE = re.compile(r"\b(?:CLASS|CL)\s*([0-9])\b", re.I)
GROUP_RE = re.compile(r"\b(?:GROUP|GRP|G)\s*([123])\b", re.I)

FEATURE_TERMS = [
    "DERBY", "OAKS", "GUINEAS", "GNEAS", "CUP", "STAKES", "STKS", "CLASSIC", "PRELUDE",
    "PREMIER", "MILLIONS", "SLIPPER", "SIRES", "CHAMPIONS", "DONCASTER", "GOODWOOD",
    "EVEREST", "TRISCAY", "AJAX", "WENONA", "KARRAKATTA", "FUTURITY", "NEWMARKET",
    "TOORAK", "UNDERWOOD", "MEMSIE", "ALL STAR", "COX PLATE", "BIG DANCE", "JERICHO",
    "GIMCRACK", "GOLDEN MILE", "BELMONT SPRINT", "P J BELL", "RAILWAY", "SAPPHIRE",
    "VRC ST LEGER", "CARBINE CLUB", "THE HUNTER", "BURGESS QUEEN", "DARBYMUNRO",
    "CS HAYES", "FIREBALL", "SAND GNEAS", "GNEAS PREL", "SPRING STK", "WANGOOM",
    "INGHAM", "HAWK CROWN", "HAWK RUSH", "HAWK GNEAS", "WOODFORD", "WINTER CSHIP",
    "SHANNON", "ANZAC DAY", "CRYSTAL", "BELGRAVIA", "S/PACIFIC", "FESTIVAL"
]

MEETING_NOISE = [
    "BAIRNSDALE", "GEEL CLSC", "GEELONG", "BALLARAT", "WARRNAMBOOL",
    "MORNINGTON", "PAKENHAM", "SALE", "MOE", "COLAC", "BENDIGO",
    "ARARAT", "TERANG", "WERRIBEE"
]

RESTRICTION_PATTERNS = [
    (re.compile(r"\bF&M\b|\bFILLIES\s*&?\s*MARES\b|\bMARES\b", re.I), "F&M"),
    (re.compile(r"\bCG&E\b|\bCGE\b|\bC&G\b|\bCOLTS.*GELDINGS", re.I), "CG&E"),
    (re.compile(r"\b3YC&G\b|\b3Y\s*C&G\b|\b3YCG\b", re.I), "3YO_COLTS_GELDINGS"),
    (re.compile(r"\b3YF\b|\b3YO\s*F\b", re.I), "3YO_FILLIES"),
    (re.compile(r"\b3&4Y\b", re.I), "3YO_4YO"),
    (re.compile(r"\b3UP\b|\b3Y\+\b", re.I), "3UP"),
    (re.compile(r"\b4UP\b|\b4Y\+\b", re.I), "4UP"),
    (re.compile(r"\b5Y\+\b", re.I), "5UP"),
    (re.compile(r"\b2UP\b", re.I), "2UP"),
    (re.compile(r"\b3YO?\b|\b3Y\b", re.I), "3YO"),
    (re.compile(r"\b2YO?\b|\b2Y\b", re.I), "2YO"),
]

RACE_TYPE_PATTERNS = [
    (re.compile(r"\bPROVMID\b|\bMIDWAY\b|\bMID\b", re.I), "MIDWAY"),
    (re.compile(r"\bPROV\b|\bPROVINCIAL\b", re.I), "PROVINCIAL"),
    (re.compile(r"\bCTRY\b|\bCOUNTRY\b", re.I), "COUNTRY"),
    (re.compile(r"\bQLTY\b|\bQUALITY\b", re.I), "QUALITY"),
    (re.compile(r"\bSUPER\b", re.I), "SUPER"),
    (re.compile(r"\bWESTSPEED\b|\bW/SPEED\b", re.I), "WESTSPEED"),
    (re.compile(r"\bVOBIS\b|\bVGOLD\b|\bVG\b|\bVOBIS GOLD\b", re.I), "VOBIS"),
    (re.compile(r"\bMM\b|\bINGLIS\b|\bGOLD\b", re.I), "SALES_INCENTIVE"),
    (re.compile(r"\bNMW\b|\b0MWLY\b|\b1MW-LY\b", re.I), "NO_METRO_WIN"),
    (re.compile(r"\bPIC\b", re.I), "PICNIC"),
    (re.compile(r"\bREGIONAL\b", re.I), "REGIONAL"),
]

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

def boolish(v):
    return upper(v) in {"TRUE", "YES", "Y", "1"}

def norm_cond(v):
    u = upper(v).replace(" ", "")
    m = re.search(r"(GOOD|SOFT|HEAVY|FIRM|SYNTHETIC|POLY|TAPETA)(\d{0,2})", u)
    if not m:
        return ""
    word = m.group(1)
    num = m.group(2)
    if word in {"POLY", "TAPETA"}:
        word = "SYNTHETIC"
    return f"{word}{num}"

def detect_restriction(u):
    found = []
    for pat, label in RESTRICTION_PATTERNS:
        if pat.search(u):
            found.append(label)
    return "+".join(dict.fromkeys(found))

def detect_race_type(u):
    found = []
    for pat, label in RACE_TYPE_PATTERNS:
        if pat.search(u):
            found.append(label)
    return "+".join(dict.fromkeys(found))

def base_result(raw, raw_condition):
    return {
        "race_class_raw": clean(raw),
        "race_class_clean": "UNKNOWN",
        "race_class_band": "UNKNOWN",
        "race_restriction": "",
        "race_type": "",
        "feature_race_flag": "NO",
        "feature_race_name": "",
        "condition_recovered": norm_cond(raw_condition),
        "class_confidence": "UNKNOWN",
        "class_reason": "",
    }

def normalise(raw_class, raw_condition, race_name):
    raw = clean(raw_class)
    u = upper(raw)
    rn = upper(race_name)
    result = base_result(raw, raw_condition)

    if not u:
        result["class_reason"] = "blank race_class"
        return result

    restriction = detect_restriction(u)
    race_type = detect_race_type(u)
    result["race_restriction"] = restriction
    result["race_type"] = race_type

    cond_match = COND_RE.search(u.replace("-", " "))
    if cond_match and len(u) <= 14:
        result["condition_recovered"] = norm_cond(u) or result["condition_recovered"]
        result["class_confidence"] = "LOW"
        result["class_reason"] = "track condition leaked into race_class"
        return result

    g = GROUP_RE.search(u)
    if g:
        result.update({
            "race_class_clean": f"G{g.group(1)}",
            "race_class_band": "BLACKTYPE",
            "feature_race_flag": "YES",
            "feature_race_name": raw,
            "class_confidence": "HIGH",
            "class_reason": "group pattern detected",
        })
        return result

    if "LISTED" in u or re.search(r"\bLR\b", u):
        result.update({
            "race_class_clean": "LISTED",
            "race_class_band": "BLACKTYPE",
            "feature_race_flag": "YES",
            "feature_race_name": raw,
            "class_confidence": "HIGH",
            "class_reason": "listed pattern detected",
        })
        return result

    rtg = RTG_RE.search(u)
    if rtg:
        result.update({
            "race_class_clean": f"RTG{rtg.group(1)}",
            "race_class_band": "RATINGS_BAND",
            "class_confidence": "HIGH",
            "class_reason": "ratings band detected",
        })
        return result

    if re.fullmatch(r"-\s*[0-9]{2,3}", u):
        n = re.sub(r"\D", "", u)
        result.update({
            "race_class_clean": f"RTG{n}",
            "race_class_band": "RATINGS_BAND",
            "class_confidence": "MEDIUM",
            "class_reason": "dash ratings band detected",
        })
        return result

    bm = BM_RE.search(u)
    if bm:
        result.update({
            "race_class_clean": f"BM{bm.group(1)}",
            "race_class_band": "BENCHMARK",
            "class_confidence": "HIGH",
            "class_reason": "benchmark pattern detected",
        })
        return result

    zero_band = re.search(r"\b0\s*-\s*([0-9]{2,3})\b", u)
    if zero_band:
        result.update({
            "race_class_clean": f"BM{zero_band.group(1)}",
            "race_class_band": "BENCHMARK",
            "class_confidence": "MEDIUM",
            "class_reason": "0-rating band mapped to benchmark",
        })
        return result

    if "MAIDEN" in u or re.search(r"\bMDN\b", u):
        result.update({
            "race_class_clean": "MAIDEN",
            "race_class_band": "MAIDEN",
            "class_confidence": "HIGH",
            "class_reason": "maiden pattern detected",
        })
        return result

    cl = CLASS_RE.search(u)
    if cl:
        result.update({
            "race_class_clean": f"CL{cl.group(1)}",
            "race_class_band": "CLASS",
            "class_confidence": "HIGH",
            "class_reason": "class pattern detected",
        })
        return result

    if u == "OPEN" or "OPEN" in u:
        result.update({
            "race_class_clean": "OPEN",
            "race_class_band": "OPEN",
            "class_confidence": "HIGH",
            "class_reason": "open class detected",
        })
        return result

    if u in {"SWP", "SET WEIGHTS PENALTIES", "SET WEIGHTS PLUS PENALTIES"}:
        result.update({
            "race_class_clean": "SET_WEIGHTS_PENALTIES",
            "race_class_band": "SET_WEIGHTS",
            "class_confidence": "HIGH",
            "class_reason": "set weights penalties detected",
        })
        return result

    if u == "COND" or "CONDITION" in u:
        result.update({
            "race_class_clean": "CONDITIONS",
            "race_class_band": "CONDITIONS",
            "class_confidence": "MEDIUM",
            "class_reason": "conditions race detected",
        })
        return result

    if "HANDICAP" in u or re.search(r"\bHCP\b", u):
        result.update({
            "race_class_clean": "HANDICAP",
            "race_class_band": "HANDICAP",
            "class_confidence": "MEDIUM",
            "class_reason": "generic handicap detected",
        })
        return result

    if "SET WEIGHTS" in u or "SW" == u:
        result.update({
            "race_class_clean": "SET_WEIGHTS",
            "race_class_band": "SET_WEIGHTS",
            "class_confidence": "MEDIUM",
            "class_reason": "set weights detected",
        })
        return result

    if any(t in u for t in FEATURE_TERMS) or any(t in rn for t in FEATURE_TERMS):
        result.update({
            "race_class_clean": "FEATURE_RACE",
            "race_class_band": "FEATURE",
            "feature_race_flag": "YES",
            "feature_race_name": raw,
            "class_confidence": "MEDIUM",
            "class_reason": "feature-race name detected but exact grade unknown",
        })
        return result

    if race_type:
        result.update({
            "race_class_clean": race_type.split("+")[0],
            "race_class_band": "RACE_TYPE",
            "class_confidence": "MEDIUM",
            "class_reason": "race type/program detected without class",
        })
        return result

    if restriction:
        result.update({
            "race_class_clean": "RESTRICTED",
            "race_class_band": "RESTRICTED",
            "class_confidence": "MEDIUM",
            "class_reason": "race restriction detected without class",
        })
        return result

    if any(t in u for t in MEETING_NOISE):
        result.update({
            "class_confidence": "LOW",
            "class_reason": "meeting/track name leakage",
        })
        return result

    result["class_reason"] = "unrecognised class token"
    return result

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

out_rows = []
for r in rows:
    n = normalise(r.get("race_class"), r.get("track_condition"), r.get("race_name"))
    merged = dict(r)
    merged.update(n)
    out_rows.append(merged)

fields = list(out_rows[0].keys()) if out_rows else []
with OUT.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out_rows)

official = [r for r in out_rows if boolish(r.get("official_run_flag")) and not boolish(r.get("trial_flag")) and not boolish(r.get("jumpout_flag"))]

band_counts = Counter(r["race_class_band"] for r in official)
clean_counts = Counter(r["race_class_clean"] for r in official)
restriction_counts = Counter(r["race_restriction"] for r in official if r["race_restriction"])
type_counts = Counter(r["race_type"] for r in official if r["race_type"])
reason_counts = Counter(r["class_reason"] for r in official)

audit_rows = []
for name, count in band_counts.most_common():
    audit_rows.append({"audit_type": "band_count", "name": name, "count": count})
for name, count in clean_counts.most_common(120):
    audit_rows.append({"audit_type": "clean_class_count", "name": name, "count": count})
for name, count in restriction_counts.most_common(100):
    audit_rows.append({"audit_type": "restriction_count", "name": name, "count": count})
for name, count in type_counts.most_common(100):
    audit_rows.append({"audit_type": "race_type_count", "name": name, "count": count})
for name, count in reason_counts.most_common(120):
    audit_rows.append({"audit_type": "reason_count", "name": name, "count": count})

with AUDIT.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["audit_type", "name", "count"])
    w.writeheader()
    w.writerows(audit_rows)

official_count = len(official)
unknown_count = sum(1 for r in official if r["race_class_clean"] == "UNKNOWN")
print("=" * 90)
print("EDGEIQ CLASS NORMALISED MASTER V3")
print("=" * 90)
print(f"source_rows: {len(rows)}")
print(f"official_non_trial_rows: {official_count}")
print(f"unknown_official_rows: {unknown_count}")
print(f"unknown_pct: {round((unknown_count / official_count) * 100, 2) if official_count else 0}")
print(f"out: {OUT}")
print(f"audit: {AUDIT}")
