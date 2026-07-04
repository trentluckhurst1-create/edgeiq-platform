from __future__ import annotations

import csv
import hashlib
import re
import time
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_wa_telemetry_forensics_v1.csv"
SUMMARY = DATA / "edgeiq_wa_telemetry_summary_v1.csv"
FIELD_DICT = DATA / "edgeiq_wa_field_dictionary_v1.csv"
LINEAGE = DATA / "edgeiq_wa_lineage_assessment_v1.csv"

FORENSICS_FIELDS = [
    "source_file","source_path","source_kind","rows_detected","sheet_count","sheet_names",
    "column_count","schema_signature","detected_columns","trial_rows_detected",
    "race_rows_detected","race_date_min","race_date_max","tracks_detected","race_count",
    "horse_rows","sectional_fields_detected","gps_fields_detected","position_fields_detected",
    "timing_fields_detected","split_depth_detected","timestamp_fields_detected",
    "hidden_sheet_candidates","telemetry_richness_score","operational_cleanliness_score",
    "discovery_classification","recommended_next_step","notes"
]

SUMMARY_FIELDS = ["metric","value"]

FIELD_FIELDS = [
    "field_name","field_type","nullable_rate","uniqueness_rate","observed_examples",
    "suspected_meaning","telemetry_importance","schema_confidence","notes"
]

LINEAGE_FIELDS = [
    "source_file","schema_signature","races_detected","horses_detected","split_rows_detected",
    "sectional_depth_score","position_richness_score","lineage_stability_score",
    "operational_cleanliness_score","telemetry_density_score","payload_quality_grade",
    "recommended_next_step","notes"
]

GRADE_LABEL = {
    "A": "ELITE_WA_TELEMETRY_SOURCE",
    "B": "HIGH_VALUE_WA_TELEMETRY_SOURCE",
    "C": "USABLE_WA_TELEMETRY_SOURCE",
    "D": "LIMITED_WA_TELEMETRY_SOURCE",
    "F": "UNSTABLE_WA_TELEMETRY_SOURCE",
}

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

def normalise_key(v):
    text = clean(v).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "blank"

def parse_float(v):
    text = clean(v).replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None

def normalise_date(v):
    text = clean(v)
    if not text:
        return ""
    for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%Y%m%d","%m/%d/%Y"):
        try:
            src = text[:8] if fmt == "%Y%m%d" else text[:10]
            return datetime.strptime(src, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    m = re.search(r"(20\d{2})[-_ ]?(\d{2})[-_ ]?(\d{2})", text)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""

def normalise_track(v):
    text = upper(v)
    text = text.replace("&", " AND ")
    text = re.sub(r"\b(RACECOURSE|RACING|CLUB|TRACK|PARK)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    aliases = {
        "PINJARRA SCARPSIDE": "PINJARRA SCARPSIDE",
        "PINJARRA PARK": "PINJARRA",
        "ASCOT": "ASCOT",
        "BELMONT": "BELMONT",
        "ALBANY": "ALBANY",
        "KALGOORLIE": "KALGOORLIE",
        "CARNARVON": "CARNARVON",
        "GERALDTON": "GERALDTON",
        "YORK": "YORK",
        "LARK HILL": "LARK HILL",
        "PORT HEDLAND": "PORT HEDLAND",
    }
    return aliases.get(text, text)

def normalise_horse(v):
    text = upper(v)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(NZ|AUS|GB|IRE|USA|FR|JPN)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{time.time_ns()}")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({field: r.get(field, "") for field in fields})
    tmp.replace(path)

def discover_files():
    roots = [
        ROOT / "outputs" / "sectionals" / "raw" / "WA",
        DATA,
        ROOT / "dashboard" / "racing-dashboard" / "public" / "data",
        ROOT,
    ]
    files = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            low = str(path).lower()
            if "node_modules" in low or "\\.git\\" in low or "/.git/" in low or "\\dist\\" in low or "/dist/" in low:
                continue
            name = path.name.lower()
            if path.suffix.lower() in {".csv",".xlsx"} and any(t in name for t in [
                "wa","ascot","belmont","albany","kalgoorlie","carnarvon","geraldton",
                "pinjarra","lark","york","horse-performances","race-results","2026-05"
            ]):
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    files.append(path)
    return sorted(files, key=lambda p: str(p).lower())

def read_csv_file(path):
    try:
        sample = path.read_text(encoding="utf-8-sig", errors="ignore")[:8192]
        delim = "," if sample.count(",") >= sample.count(";") else ";"
        with path.open("r", newline="", encoding="utf-8-sig", errors="ignore") as f:
            return [{clean(k): clean(v) for k,v in row.items() if k is not None} for row in csv.DictReader(f, delimiter=delim)]
    except Exception:
        return []

def xlsx_shared_strings(z):
    out = []
    try:
        xml = z.read("xl/sharedStrings.xml")
    except KeyError:
        return out
    root = ET.fromstring(xml)
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    for si in root.findall("a:si", ns):
        texts = [t.text or "" for t in si.findall(".//a:t", ns)]
        out.append("".join(texts))
    return out

def col_index(cell_ref):
    letters = re.sub(r"[^A-Z]", "", cell_ref.upper())
    total = 0
    for ch in letters:
        total = total * 26 + (ord(ch) - 64)
    return total - 1

def read_xlsx_file(path):
    rows_all = []
    sheet_names = []
    try:
        with zipfile.ZipFile(path) as z:
            shared = xlsx_shared_strings(z)
            workbook = ET.fromstring(z.read("xl/workbook.xml"))
            ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            rels = {}
            try:
                rel_root = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
                for rel in rel_root:
                    rels[rel.attrib.get("Id")] = rel.attrib.get("Target")
            except Exception:
                pass

            sheets = []
            for sheet in workbook.findall(".//a:sheet", ns):
                name = sheet.attrib.get("name", "Sheet")
                rid = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                target = rels.get(rid, "")
                if target:
                    sheets.append((name, "xl/" + target.lstrip("/").replace("xl/", "")))
            for sheet_name, sheet_path in sheets:
                sheet_names.append(sheet_name)
                try:
                    root = ET.fromstring(z.read(sheet_path))
                except Exception:
                    continue
                raw_rows = []
                for row in root.findall(".//a:row", ns):
                    values = {}
                    for c in row.findall("a:c", ns):
                        ref = c.attrib.get("r","A1")
                        idx = col_index(ref)
                        t = c.attrib.get("t","")
                        v = c.find("a:v", ns)
                        value = ""
                        if v is not None and v.text is not None:
                            value = v.text
                            if t == "s":
                                try:
                                    value = shared[int(value)]
                                except Exception:
                                    pass
                        values[idx] = clean(value)
                    if values:
                        max_idx = max(values)
                        raw_rows.append([values.get(i,"") for i in range(max_idx + 1)])
                if not raw_rows:
                    continue
                header_idx = 0
                best_score = -1
                for i, r in enumerate(raw_rows[:20]):
                    score = sum(1 for x in r if clean(x))
                    if score > best_score:
                        best_score = score
                        header_idx = i
                headers = [normalise_key(x) for x in raw_rows[header_idx]]
                for r in raw_rows[header_idx+1:]:
                    row = {}
                    for i, val in enumerate(r):
                        if i < len(headers):
                            row[headers[i] or f"col_{i+1}"] = clean(val)
                    if any(row.values()):
                        row["_sheet_name"] = sheet_name
                        rows_all.append(row)
    except Exception:
        return [], []
    return rows_all, sheet_names

def read_any(path):
    if path.suffix.lower() == ".xlsx":
        rows, sheets = read_xlsx_file(path)
        return rows, sheets
    return read_csv_file(path), []

def schema_signature(fields):
    joined = "|".join(sorted(f.lower() for f in fields))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]

def field_groups(fields):
    groups = {k: [] for k in ["sectional","gps","position","timing","timestamp","race","horse","trial"]}
    for f in fields:
        low = f.lower()
        if any(t in low for t in ["sectional","last_600","last600","600m","last_400","last400","400m","last_200","last200","200m","split"]):
            groups["sectional"].append(f)
        if any(t in low for t in ["gps","speed","metre","meter","distance_travelled","top_speed","velocity"]):
            groups["gps"].append(f)
        if any(t in low for t in ["position","rank","pos","order","600m_photo","finish_photo","photo"]):
            groups["position"].append(f)
        if any(t in low for t in ["time","finish","sectional","last","split"]):
            groups["timing"].append(f)
        if any(t in low for t in ["date","timestamp","created","updated","time_utc"]):
            groups["timestamp"].append(f)
        if any(t in low for t in ["race","track","meeting","distance","class","condition","rail"]):
            groups["race"].append(f)
        if any(t in low for t in ["horse","runner","saddle","tab","barrier"]):
            groups["horse"].append(f)
        if low in {"t","trial","trial_flag","event_type","category"} or "trial" in low:
            groups["trial"].append(f)
    return groups

def is_trial_row(row):
    text = " ".join(upper(v) for v in row.values())
    for k,v in row.items():
        kl = k.lower()
        vl = upper(v)
        if kl in {"category","event_type","race_type","type"} and vl == "T":
            return True
        if "trial" in vl:
            return True
    return False

def infer_file_kind(path):
    name = path.name.lower()
    if path.suffix.lower() == ".xlsx":
        return "WA_XLSX_SECTIONAL_ARTEFACT"
    if "horse-performances" in name:
        return "WA_HORSE_PERFORMANCES_CSV"
    if "race-results" in name:
        return "WA_RACE_RESULTS_CSV"
    return "WA_DISCOVERED_CSV"

def classify(richness, clean_score, lineage, density):
    score = richness*0.35 + clean_score*0.25 + lineage*0.20 + density*0.20
    if score >= 86: return "A"
    if score >= 74: return "B"
    if score >= 58: return "C"
    if score >= 38: return "D"
    return "F"

def field_type(vals):
    vals = [clean(v) for v in vals if clean(v)]
    if not vals: return "empty"
    nums = sum(1 for v in vals if parse_float(v) is not None)
    if nums / len(vals) >= 0.85: return "numeric"
    dates = sum(1 for v in vals if normalise_date(v))
    if dates / len(vals) >= 0.5: return "date_or_timestamp"
    return "text"

def meaning(field):
    low = field.lower()
    if any(t in low for t in ["horse","runner"]): return ("Horse identity","CRITICAL",90)
    if any(t in low for t in ["race","track","meeting","distance"]): return ("Race identity / race metadata","CRITICAL",88)
    if any(t in low for t in ["last_600","600","400","200","sectional","split"]): return ("Sectional timing ladder","HIGH",88)
    if any(t in low for t in ["speed","gps","distance_travelled"]): return ("GPS / speed telemetry","HIGH",84)
    if any(t in low for t in ["rank","position","photo"]): return ("Position or visual race-state telemetry","HIGH",80)
    if any(t in low for t in ["source","url","file"]): return ("Lineage/provenance","HIGH",78)
    return ("General WA payload field","LOW",55)

def main():
    files = discover_files()
    forensics = []
    lineage = []
    all_values = defaultdict(list)
    total_rows = 0
    trial_rows = 0

    for path in files:
        rows, sheets = read_any(path)
        if not rows:
            continue
        fields = sorted({f for r in rows for f in r.keys() if not f.startswith("_")})
        sig = schema_signature(fields)
        groups = field_groups(fields)
        non_trial = [r for r in rows if not is_trial_row(r)]
        trials = len(rows) - len(non_trial)
        total_rows += len(rows)
        trial_rows += trials

        tracks = set()
        dates = []
        races = set()
        horses = set()
        split_rows = 0

        for r in non_trial:
            text = " ".join(clean(v) for v in r.values())
            date = ""
            for v in r.values():
                date = normalise_date(v)
                if date: break
            if date: dates.append(date)
            track = ""
            for k,v in r.items():
                if "track" in k.lower() or "venue" in k.lower() or "meeting" in k.lower():
                    track = normalise_track(v)
                    if track: break
            if not track:
                for known in ["ASCOT","BELMONT","ALBANY","KALGOORLIE","CARNARVON","GERALDTON","PINJARRA","YORK","LARK HILL","PORT HEDLAND"]:
                    if known in upper(text):
                        track = known
                        break
            if track: tracks.add(track)
            race_no = ""
            for k,v in r.items():
                if "race" in k.lower():
                    m = re.search(r"\d+", clean(v))
                    if m:
                        race_no = m.group(0)
                        break
            if date or track or race_no:
                races.add((date, track, race_no))
            horse = ""
            for k,v in r.items():
                if "horse" in k.lower() or "runner" in k.lower():
                    horse = normalise_horse(v)
                    if horse: break
            if horse: horses.add(horse)
            if any(clean(r.get(f)) for f in groups["sectional"] + groups["timing"]):
                split_rows += 1
            for f,v in r.items():
                if not f.startswith("_"):
                    all_values[f].append(v)

        populated = sum(sum(1 for v in r.values() if clean(v)) for r in rows)
        cells = max(1, len(rows) * max(1, len(fields)))
        density = populated / cells * 100
        split_depth = min(100, len(groups["sectional"]) * 16 + len(groups["timing"]) * 4)
        position_score = min(100, len(groups["position"]) * 20)
        gps_score = min(100, len(groups["gps"]) * 18)
        richness = min(100, split_depth*0.45 + gps_score*0.25 + position_score*0.20 + min(10, len(sheets))*1.0)
        operational = 85 if path.suffix.lower() in {".csv",".xlsx"} else 55
        if trials:
            operational -= min(15, trials / max(1, len(rows)) * 20)
        lineage_score = 78 if "outputs" in str(path).lower() or "public" in str(path).lower() else 65
        grade = classify(richness, operational, lineage_score, density)
        label = GRADE_LABEL[grade]

        forensics.append({
            "source_file": path.name,
            "source_path": str(path),
            "source_kind": infer_file_kind(path),
            "rows_detected": len(rows),
            "sheet_count": len(sheets),
            "sheet_names": "|".join(sheets),
            "column_count": len(fields),
            "schema_signature": sig,
            "detected_columns": "|".join(fields),
            "trial_rows_detected": trials,
            "race_rows_detected": len(non_trial),
            "race_date_min": min(dates) if dates else "",
            "race_date_max": max(dates) if dates else "",
            "tracks_detected": "|".join(sorted(tracks)),
            "race_count": len(races),
            "horse_rows": len(horses),
            "sectional_fields_detected": "|".join(groups["sectional"]),
            "gps_fields_detected": "|".join(groups["gps"]),
            "position_fields_detected": "|".join(groups["position"]),
            "timing_fields_detected": "|".join(groups["timing"]),
            "split_depth_detected": f"{split_depth:.2f}",
            "timestamp_fields_detected": "|".join(groups["timestamp"]),
            "hidden_sheet_candidates": len(sheets),
            "telemetry_richness_score": f"{richness:.2f}",
            "operational_cleanliness_score": f"{operational:.2f}",
            "discovery_classification": label,
            "recommended_next_step": "Build isolated WA ingestion pipeline after validating source schema and excluding trials." if grade in {"A","B","C"} else "Keep WA source in diagnostics only until richer telemetry is acquired.",
            "notes": "WA telemetry forensics only. Trials marked T are excluded from primary ontology. No modelling/execution/merge.",
        })

        lineage.append({
            "source_file": path.name,
            "schema_signature": sig,
            "races_detected": len(races),
            "horses_detected": len(horses),
            "split_rows_detected": split_rows,
            "sectional_depth_score": f"{split_depth:.2f}",
            "position_richness_score": f"{position_score:.2f}",
            "lineage_stability_score": f"{lineage_score:.2f}",
            "operational_cleanliness_score": f"{operational:.2f}",
            "telemetry_density_score": f"{density:.2f}",
            "payload_quality_grade": label,
            "recommended_next_step": "Proceed to isolated WA ingestion only; do not merge with VIC/QLD/NSW yet." if grade in {"A","B","C"} else "Repair or acquire better WA telemetry source first.",
            "notes": "WA lineage assessment. Trials excluded from primary telemetry ontology.",
        })

    field_rows = []
    for f, vals in sorted(all_values.items(), key=lambda x: x[0].lower()):
        total = len(vals)
        blanks = sum(1 for v in vals if not clean(v))
        populated = [clean(v) for v in vals if clean(v)]
        examples = " | ".join(list(dict.fromkeys(populated))[:5])
        m, importance, conf = meaning(f)
        field_rows.append({
            "field_name": f,
            "field_type": field_type(vals),
            "nullable_rate": f"{(blanks/total*100) if total else 100:.2f}",
            "uniqueness_rate": f"{(len(set(populated))/len(populated)*100) if populated else 0:.2f}",
            "observed_examples": examples[:500],
            "suspected_meaning": m,
            "telemetry_importance": importance,
            "schema_confidence": f"{conf:.2f}",
            "notes": "WA field dictionary. Offline telemetry forensics only.",
        })

    classes = Counter(r["discovery_classification"] for r in forensics)
    summary = [
        {"metric":"wa_files_discovered","value":len(files)},
        {"metric":"wa_sources_audited","value":len(forensics)},
        {"metric":"wa_rows_detected","value":total_rows},
        {"metric":"wa_trial_rows_excluded_from_primary","value":trial_rows},
        {"metric":"field_dictionary_rows","value":len(field_rows)},
        {"metric":"lineage_rows","value":len(lineage)},
        {"metric":"elite_sources","value":classes.get("ELITE_WA_TELEMETRY_SOURCE",0)},
        {"metric":"high_value_sources","value":classes.get("HIGH_VALUE_WA_TELEMETRY_SOURCE",0)},
        {"metric":"usable_sources","value":classes.get("USABLE_WA_TELEMETRY_SOURCE",0)},
        {"metric":"limited_sources","value":classes.get("LIMITED_WA_TELEMETRY_SOURCE",0)},
        {"metric":"unstable_sources","value":classes.get("UNSTABLE_WA_TELEMETRY_SOURCE",0)},
        {"metric":"sectional_candidate_sources","value":sum(1 for r in forensics if clean(r["sectional_fields_detected"]))},
        {"metric":"gps_candidate_sources","value":sum(1 for r in forensics if clean(r["gps_fields_detected"]))},
        {"metric":"position_candidate_sources","value":sum(1 for r in forensics if clean(r["position_fields_detected"]))},
        {"metric":"recommended_next_step","value":"Build isolated WA telemetry ingestion pipeline if high/usable sources exist; keep trials isolated."},
        {"metric":"merged_into_vic_qld_nsw","value":"NO"},
        {"metric":"live_modelling_yes","value":0},
        {"metric":"live_execution_yes","value":0},
        {"metric":"offline_research_only","value":"YES"},
    ]

    write_csv(OUT, forensics, FORENSICS_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    write_csv(FIELD_DICT, field_rows, FIELD_FIELDS)
    write_csv(LINEAGE, lineage, LINEAGE_FIELDS)

    print("="*88)
    print("EDGEIQ WA TELEMETRY FORENSICS V1")
    print("="*88)
    for row in summary:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {FIELD_DICT}")
    print(f"saved: {LINEAGE}")

if __name__ == "__main__":
    main()
