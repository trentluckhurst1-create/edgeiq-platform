import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
PUBLIC = DASH / "public" / "data"

SRC = ROOT / "outputs" / "enrichment" / "run_context.csv"

OUT = PUBLIC / "edgeiq_class_recovery_engine_v2.csv"
AUDIT = PUBLIC / "edgeiq_class_recovery_engine_v2_audit.csv"
SUMMARY = PUBLIC / "edgeiq_class_recovery_engine_v2_summary.csv"

print("=" * 96)
print("EDGEIQ CLASS RECOVERY ENGINE V2")
print("=" * 96)

if not SRC.exists():
    raise FileNotFoundError(SRC)

df = pd.read_csv(SRC, low_memory=False)

required = [
    "horse",
    "race_date",
    "track",
    "source_race_no",
    "distance",
    "race_name",
    "race_class",
    "race_class_raw",
    "race_class_clean",
    "race_class_band",
    "track_condition",
    "finish_pos",
    "margin",
    "source_url",
    "official_result_url",
]

missing = [c for c in required if c not in df.columns]
if missing:
    print("AVAILABLE COLUMNS:")
    print(list(df.columns))
    raise ValueError(f"Missing required columns: {missing}")

def clean_text(x):
    if pd.isna(x):
        return ""
    return str(x).upper().strip()

def compact_spaces(x):
    return re.sub(r"\s+", " ", str(x).strip())

def extract_condition_detail(*vals):
    blob = " ".join(clean_text(v) for v in vals if clean_text(v))
    blob = blob.replace("GOOD 4", "GOOD4").replace("GOOD 3", "GOOD3")
    blob = blob.replace("SOFT 5", "SOFT5").replace("SOFT 6", "SOFT6").replace("SOFT 7", "SOFT7")
    blob = blob.replace("HEAVY 8", "HEAVY8").replace("HEAVY 9", "HEAVY9").replace("HEAVY 10", "HEAVY10")
    m = re.search(r"\b(FIRM[0-9]?|GOOD[0-9]?|SOFT[0-9]?|HEAVY[0-9]{1,2}|SYNTHETIC)\b", blob)
    return m.group(1) if m else ""

def detect_trial(raw, name):
    blob = f"{clean_text(raw)} {clean_text(name)}"
    return bool(re.search(r"\b(TRIAL|TRL|JUMP\s*OUT|JUMPOUT|J/O|BT)\b", blob))

def detect_age(raw, name):
    blob = f"{clean_text(raw)} {clean_text(name)}"
    if re.search(r"\b2YO\b|\b2Y\b|TWO-YEAR|TWO YEAR", blob):
        return "2YO"
    if re.search(r"\b3YO\b|\b3Y\b|THREE-YEAR|THREE YEAR", blob):
        return "3YO"
    if re.search(r"\b4UP\b|\b4YO\+\b|\b4Y\+\b|\b4YO AND UP\b|\b4 YEARS AND OLDER\b", blob):
        return "4UP"
    if re.search(r"\b3UP\b|\b3YO\+\b|\b3Y\+\b|\b3 YEARS AND OLDER\b", blob):
        return "3UP"
    if re.search(r"\b2UP\b|\b2YO\+\b|\b2Y\+\b", blob):
        return "2UP"
    return "OPEN"

def detect_sex(raw, name):
    blob = f"{clean_text(raw)} {clean_text(name)}"
    if re.search(r"\bF&M\b|FILLIES\s*&\s*MARES|FILLIES AND MARES|\bMARES\b|\b3YF\b|\b2YF\b", blob):
        return "F&M"
    if re.search(r"\bCG&E\b|COLTS,\s*GELDINGS\s*&\s*ENTIRES|COLTS GELDINGS AND ENTIRES|COLTS.*GELDINGS.*ENTIRES|\bC&G\b", blob):
        return "CG&E"
    if re.search(r"\bFILLIES\b|\bFILLIES'", blob):
        return "FILLIES"
    return "OPEN"

def detect_race_type(raw, name, distance):
    blob = f"{clean_text(raw)} {clean_text(name)}"
    d = pd.to_numeric(distance, errors="coerce")
    if "STEEPLE" in blob or "STEEPLECHASE" in blob:
        return "JUMPS_STEEPLE"
    if "HURDLE" in blob:
        return "JUMPS_HURDLE"
    if pd.notna(d) and d >= 3000 and re.search(r"\bJUMP|HURDLE|STEEPLE|HIGHWEIGHT|BM120\b", blob):
        return "JUMPS_OR_HIGHWEIGHT"
    return "FLAT"

def recover_class(row):
    raw_clean = clean_text(row.get("race_class_clean", ""))
    race_class = clean_text(row.get("race_class", ""))
    raw = clean_text(row.get("race_class_raw", ""))
    name = clean_text(row.get("race_name", ""))

    blob = f"{name} {race_class} {raw}"
    blob = compact_spaces(blob.upper())
    blob_no_money = re.sub(r"\$[0-9,]+(?:\s*\([^)]+\))?", "", blob)

    existing = raw_clean

    if detect_trial(raw, name):
        return {
            "race_class_recovered": "TRIAL_OR_JUMPOUT",
            "class_recovery_status": "EXCLUDE_TRIAL_JUMPOUT",
            "class_recovery_reason": "trial_or_jumpout_token",
        }

    if "STEEPLE" in blob_no_money or "STEEPLECHASE" in blob_no_money:
        return {
            "race_class_recovered": "STEEPLECHASE",
            "class_recovery_status": "RECOVERED",
            "class_recovery_reason": "steeplechase_token",
        }

    if "HURDLE" in blob_no_money:
        return {
            "race_class_recovered": "HURDLE",
            "class_recovery_status": "RECOVERED",
            "class_recovery_reason": "hurdle_token",
        }

    if re.search(r"\bGROUP\s*1\b|\bG1\b|\bGRP\s*1\b", blob_no_money):
        return {"race_class_recovered": "GROUP 1", "class_recovery_status": "RECOVERED", "class_recovery_reason": "group_1_token"}
    if re.search(r"\bGROUP\s*2\b|\bG2\b|\bGRP\s*2\b", blob_no_money):
        return {"race_class_recovered": "GROUP 2", "class_recovery_status": "RECOVERED", "class_recovery_reason": "group_2_token"}
    if re.search(r"\bGROUP\s*3\b|\bG3\b|\bGRP\s*3\b", blob_no_money):
        return {"race_class_recovered": "GROUP 3", "class_recovery_status": "RECOVERED", "class_recovery_reason": "group_3_token"}
    if re.search(r"\bLISTED\b|\bLR\b", blob_no_money):
        return {"race_class_recovered": "LISTED", "class_recovery_status": "RECOVERED", "class_recovery_reason": "listed_token"}

    m = re.search(r"\bBM\s*([0-9]{2,3})\b|\bBENCHMARK\s*([0-9]{2,3})\b", blob_no_money)
    if m:
        val = m.group(1) or m.group(2)
        return {"race_class_recovered": f"BM{int(val)}", "class_recovery_status": "RECOVERED", "class_recovery_reason": "benchmark_token"}

    m = re.search(r"\b(?:RATING\s*)?0\s*[-–]\s*([0-9]{2,3})\+?\b", blob_no_money)
    if m:
        val = int(m.group(1))
        if val >= 110:
            return {
                "race_class_recovered": "JUMPS_RATING_BAND",
                "class_recovery_status": "RECOVERED",
                "class_recovery_reason": "jumps_rating_band_token"
            }
        return {
            "race_class_recovered": f"BM{val}",
            "class_recovery_status": "RECOVERED",
            "class_recovery_reason": "zero_to_rating_token"
        }

    m = re.search(r"\bRTG\s*([0-9]{2,3})\+\b|\bRATING\s*([0-9]{2,3})\+\b|\bHCP\s*([0-9]{2,3})\+\b|\bGRAD\s*HCP\s*([0-9]{2,3})\+\b|\bGRAND\s*HCP\s*([0-9]{2,3})\+\b", blob_no_money)
    if m:
        val = next(g for g in m.groups() if g)
        return {"race_class_recovered": f"BM{int(val)}", "class_recovery_status": "RECOVERED", "class_recovery_reason": "rating_plus_token"}

    m = re.search(r"\bCLASS\s*([1-6])\b|\bCL\s*([1-6])\b", blob_no_money)
    if m:
        val = m.group(1) or m.group(2)
        return {"race_class_recovered": f"CLASS {int(val)}", "class_recovery_status": "RECOVERED", "class_recovery_reason": "class_token"}

    valid_existing_patterns = [
        r"^MAIDEN$", r"^MDN$",
        r"^CLASS [1-6]$", r"^CL[1-6]$",
        r"^BM[0-9]{2,3}$",
        r"^GROUP [123]$",
        r"^LISTED$",
        r"^OPEN$",
        r"^SET WEIGHTS$", r"^SET WEIGHTS PENALTIES$",
    ]

    for pat in valid_existing_patterns:
        if re.match(pat, existing):
            recovered = existing
            if recovered == "MDN":
                recovered = "MAIDEN"
            if re.match(r"^CL[1-6]$", recovered):
                recovered = "CLASS " + recovered.replace("CL", "")
            return {"race_class_recovered": recovered, "class_recovery_status": "KEPT_EXISTING", "class_recovery_reason": "existing_valid_class"}

    if re.search(r"\bMIDWAY\b|\bMID\b", blob_no_money):
        return {"race_class_recovered": "MIDWAY", "class_recovery_status": "RECOVERED", "class_recovery_reason": "midway_token"}

    if re.search(r"\bPROV\b|PROVINCIAL", blob_no_money):
        return {"race_class_recovered": "PROVINCIAL", "class_recovery_status": "RECOVERED", "class_recovery_reason": "provincial_token"}

    if re.search(r"\bCTRY\b|COUNTRY", blob_no_money):
        return {"race_class_recovered": "COUNTRY", "class_recovery_status": "RECOVERED", "class_recovery_reason": "country_token"}

    if existing == "HANDICAP" or race_class == "HANDICAP" or raw == "HANDICAP" or raw == "HCP" or " HANDICAP" in blob_no_money or blob_no_money.endswith("HCP"):
        return {"race_class_recovered": "HANDICAP_UNRESOLVED", "class_recovery_status": "UNRESOLVED_GENERIC_HANDICAP", "class_recovery_reason": "generic_handicap_no_rating_token"}

    condition_tokens = {"GOOD", "GOOD3", "GOOD4", "SOFT", "SOFT5", "SOFT6", "SOFT7", "HEAVY8", "HEAVY9", "HEAVY10", "FIRM2", "SYNTHETIC"}
    if existing in condition_tokens or raw in condition_tokens:
        return {"race_class_recovered": "UNKNOWN", "class_recovery_status": "NON_CLASS_CONDITION_TOKEN", "class_recovery_reason": "condition_token_not_class"}

    age_tokens = {"2Y", "2YO", "3Y", "3YO", "3UP", "2UP", "4UP", "3&4Y", "4Y+", "5Y+"}
    sex_tokens = {"F&M", "CG&E", "MARES", "FILLIES", "3YF", "2YF"}

    if existing in age_tokens or raw in age_tokens:
        return {"race_class_recovered": "UNKNOWN", "class_recovery_status": "NON_CLASS_AGE_TOKEN", "class_recovery_reason": "age_token_not_class"}

    if existing in sex_tokens or raw in sex_tokens:
        return {"race_class_recovered": "UNKNOWN", "class_recovery_status": "NON_CLASS_SEX_TOKEN", "class_recovery_reason": "sex_token_not_class"}

    return {"race_class_recovered": "UNKNOWN", "class_recovery_status": "UNRESOLVED", "class_recovery_reason": "no_recoverable_class_token"}

rows = []
for _, row in df.iterrows():
    rec = recover_class(row)
    race_type = detect_race_type(row.get("race_class_raw", ""), row.get("race_name", ""), row.get("distance", ""))
    age = detect_age(row.get("race_class_raw", ""), row.get("race_name", ""))
    sex = detect_sex(row.get("race_class_raw", ""), row.get("race_name", ""))
    cond_detail = extract_condition_detail(row.get("race_class_clean", ""), row.get("race_class_raw", ""), row.get("track_condition", ""))

    rows.append({
        "horse": row.get("horse", ""),
        "race_date": row.get("race_date", ""),
        "track": row.get("track", ""),
        "source_race_no": row.get("source_race_no", ""),
        "distance": row.get("distance", ""),
        "race_name": row.get("race_name", ""),
        "race_class_original": row.get("race_class", ""),
        "race_class_raw": row.get("race_class_raw", ""),
        "race_class_clean_original": row.get("race_class_clean", ""),
        "race_class_recovered": rec["race_class_recovered"],
        "class_recovery_status": rec["class_recovery_status"],
        "class_recovery_reason": rec["class_recovery_reason"],
        "race_type_recovered": race_type,
        "age_restriction_recovered": age,
        "sex_restriction_recovered": sex,
        "track_condition_original": row.get("track_condition", ""),
        "condition_token_recovered": cond_detail,
        "finish_pos": row.get("finish_pos", ""),
        "margin": row.get("margin", ""),
        "source_url": row.get("source_url", ""),
        "official_result_url": row.get("official_result_url", ""),
    })

out = pd.DataFrame(rows)
out["built_at"] = datetime.now().isoformat(timespec="seconds")
out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "rows_loaded", "value": len(df)},
    {"metric": "rows_written", "value": len(out)},
    {"metric": "original_unknown_count", "value": int(out["race_class_clean_original"].astype(str).str.upper().eq("UNKNOWN").sum())},
    {"metric": "original_handicap_count", "value": int(out["race_class_clean_original"].astype(str).str.upper().eq("HANDICAP").sum())},
    {"metric": "recovered_count", "value": int(out["class_recovery_status"].astype(str).str.startswith("RECOVERED").sum())},
    {"metric": "kept_existing_count", "value": int(out["class_recovery_status"].eq("KEPT_EXISTING").sum())},
    {"metric": "generic_handicap_unresolved_count", "value": int(out["class_recovery_status"].eq("UNRESOLVED_GENERIC_HANDICAP").sum())},
    {"metric": "unresolved_count", "value": int(out["class_recovery_status"].eq("UNRESOLVED").sum())},
    {"metric": "trial_jumpout_excluded_count", "value": int(out["class_recovery_status"].eq("EXCLUDE_TRIAL_JUMPOUT").sum())},
    {"metric": "non_class_condition_token_count", "value": int(out["class_recovery_status"].eq("NON_CLASS_CONDITION_TOKEN").sum())},
    {"metric": "non_class_age_token_count", "value": int(out["class_recovery_status"].eq("NON_CLASS_AGE_TOKEN").sum())},
    {"metric": "non_class_sex_token_count", "value": int(out["class_recovery_status"].eq("NON_CLASS_SEX_TOKEN").sum())},
])

audit.to_csv(AUDIT, index=False)

summary = (
    out.groupby(["race_class_clean_original", "race_class_recovered", "class_recovery_status", "class_recovery_reason"], dropna=False)
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)

summary.to_csv(SUMMARY, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(f"wrote: {SUMMARY}")
print("")
print(audit.to_string(index=False))
print("=" * 96)


