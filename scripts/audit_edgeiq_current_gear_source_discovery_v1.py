from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re
import csv

DATA = Path("public/data")
GOV = DATA / "edgeiq_live_runner_board_governed_v1.csv"
OUT = DATA / "edgeiq_current_gear_source_discovery_v1.csv"
SUMMARY = DATA / "edgeiq_current_gear_source_discovery_v1_summary.csv"
REPORT = DATA / "edgeiq_current_gear_source_discovery_v1_report.txt"

GEAR_KEYWORDS = ["gear", "blink", "tongue", "winker", "gelding", "gelded", "visor", "nose", "lugging"]
MEANINGFUL_GEAR_TERMS = ["BLINK", "TONGUE", "WINKER", "GELD", "VISOR", "NOSE", "LUGGING", "EAR MUFF", "BIT", "CROSS-OVER", "NORTON", "PACIFIER", "HOOD", "BAR PLATE", "BARRIER BLANKET"]
PLACEHOLDER_TERMS = ["NO LISTED GEAR", "NO_GEAR", "NO GEAR", "NO LISTED CHANGE"]
DATE_NAMES = ["race_date", "meeting_date", "meet_date", "run_date", "date"]
TRACK_NAMES = ["track", "venue", "venue_name", "track_name"]
RACE_NAMES = ["race_no", "race_number", "race_num"]
HORSE_NAMES = ["horse_key", "horse", "horse_name", "runner", "runner_name"]

def clean(v): return "" if pd.isna(v) else str(v).strip()
def nt_series(s): return s.astype(str).str.upper().str.replace(r"\s+", " ", regex=True).str.strip()
def nr_series(s):
    raw = s.astype(str).str.upper().str.replace("R", "", regex=False).str.strip()
    nums = pd.to_numeric(raw, errors="coerce")
    out = raw.copy()
    mask = nums.notna()
    out.loc[mask] = nums.loc[mask].astype(int).astype(str)
    return out.fillna("")
def nh_series(s): return s.astype(str).str.upper().str.replace(r"[^A-Z0-9]+", "", regex=True)
def parse_dates(s):
    raw = s.astype(str).str.strip()
    parsed = pd.to_datetime(raw, errors="coerce")
    mask = parsed.isna()
    if mask.any():
        parsed2 = pd.to_datetime(raw[mask], format="%d%b%y", errors="coerce")
        parsed.loc[mask] = parsed2
    out = parsed.dt.strftime("%Y-%m-%d")
    return out.fillna(raw)

def pick_cols(columns, names, contains=False):
    cols = list(columns)
    lower = {c.lower(): c for c in cols}
    out = []
    for n in names:
        if n.lower() in lower and lower[n.lower()] not in out:
            out.append(lower[n.lower()])
    if contains:
        for c in cols:
            cl = c.lower()
            if any(n.lower() in cl for n in names) and c not in out:
                out.append(c)
    return out

def first_col(cols): return cols[0] if cols else None

def read_header(path):
    for enc in ("utf-8-sig", "latin-1"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return next(csv.reader(f))
        except Exception:
            continue
    return []

def make_keys(df, dcol, tcol, rcol, hcol):
    dates = parse_dates(df[dcol]) if dcol and dcol in df.columns else pd.Series([""] * len(df), index=df.index)
    tracks = nt_series(df[tcol]) if tcol and tcol in df.columns else pd.Series([""] * len(df), index=df.index)
    races = nr_series(df[rcol]) if rcol and rcol in df.columns else pd.Series([""] * len(df), index=df.index)
    horses = nh_series(df[hcol]) if hcol and hcol in df.columns else pd.Series([""] * len(df), index=df.index)
    return dates, tracks, races, horses

gov = pd.read_csv(GOV, dtype=str, keep_default_na=False, low_memory=False)
gdate = first_col(pick_cols(gov.columns, DATE_NAMES, True)) or "race_date"
gtrack = first_col(pick_cols(gov.columns, TRACK_NAMES, True)) or "track"
grace = first_col(pick_cols(gov.columns, RACE_NAMES, True)) or "race_no"
ghorse = "horse_key" if "horse_key" in gov.columns else first_col(pick_cols(gov.columns, HORSE_NAMES, True))
gd, gt, gr, gh = make_keys(gov, gdate, gtrack, grace, ghorse)
gov_full = set((gd + "|" + gt + "|" + gr + "|" + gh).tolist())
gov_loose = set((gt + "|" + gr + "|" + gh).tolist())
gov_horse = set(gh.tolist())
gov_dates = {x for x in gd.tolist() if x}
gov_tracks = {x for x in gt.tolist() if x}

rows=[]
files_scanned=0
candidate_files=0
safe_sources=0
for path in sorted(DATA.glob("*.csv")):
    files_scanned += 1
    header = read_header(path)
    if not header:
        continue
    gear_cols = [c for c in header if any(k in c.lower() for k in GEAR_KEYWORDS)]
    if not gear_cols:
        continue
    candidate_files += 1
    dcols = pick_cols(header, DATE_NAMES, True)
    tcols = pick_cols(header, TRACK_NAMES, True)
    rcols = pick_cols(header, RACE_NAMES, True)
    hcols = pick_cols(header, HORSE_NAMES, True)
    dcol = first_col(dcols)
    tcol = first_col(tcols)
    rcol = first_col(rcols)
    hcol = "horse_key" if "horse_key" in header else first_col(hcols)
    usecols = []
    for c in [dcol, tcol, rcol, hcol] + gear_cols:
        if c and c in header and c not in usecols:
            usecols.append(c)
    rec = {
        "file": path.name,
        "rows": 0,
        "gear_columns": "|".join(gear_cols),
        "date_columns": "|".join(dcols),
        "track_columns": "|".join(tcols),
        "race_no_columns": "|".join(rcols),
        "horse_columns": "|".join(hcols),
        "min_date": "",
        "max_date": "",
        "current_date_overlap": "NO",
        "current_track_overlap": "NO",
        "full_key_match_count": 0,
        "loose_track_race_horse_match_count": 0,
        "horse_only_match_count": 0,
        "sample_nonblank_gear_values": "",
        "meaningful_gear_rows": 0,
        "meaningful_full_key_match_count": 0,
        "meaningful_loose_match_count": 0,
        "read_status": "OK",
        "safe_source_candidate": "NO",
    }
    matched_full=set(); matched_loose=set(); matched_horse=set(); meaningful_full=set(); meaningful_loose=set(); dates_seen=set(); tracks_seen=set(); samples=[]
    try:
        for chunk in pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False, usecols=usecols, chunksize=100000):
            rec["rows"] += len(chunk)
            dates, tracks, races, horses = make_keys(chunk, dcol, tcol, rcol, hcol)
            if dcol:
                ds = {x for x in dates.tolist() if x}
                dates_seen.update(ds)
                if gov_dates & ds:
                    rec["current_date_overlap"] = "YES"
            if tcol:
                ts = {x for x in tracks.tolist() if x}
                tracks_seen.update(ts)
                if gov_tracks & ts:
                    rec["current_track_overlap"] = "YES"
            meaningful_mask = pd.Series([False] * len(chunk), index=chunk.index)
            for gc in gear_cols:
                if gc in chunk.columns:
                    txt = chunk[gc].astype(str).str.upper()
                    has_term = txt.apply(lambda x: any(term in x for term in MEANINGFUL_GEAR_TERMS))
                    has_placeholder = txt.apply(lambda x: any(term in x for term in PLACEHOLDER_TERMS))
                    meaningful_mask = meaningful_mask | (has_term & ~has_placeholder)
            rec["meaningful_gear_rows"] += int(meaningful_mask.sum())
            if all([dcol, tcol, rcol, hcol]):
                full_series = dates + "|" + tracks + "|" + races + "|" + horses
                full = set(full_series.tolist())
                matched_full.update(gov_full & full)
                if meaningful_mask.any():
                    meaningful_full.update(gov_full & set(full_series[meaningful_mask].tolist()))
            if all([tcol, rcol, hcol]):
                loose_series = tracks + "|" + races + "|" + horses
                loose = set(loose_series.tolist())
                matched_loose.update(gov_loose & loose)
                if meaningful_mask.any():
                    meaningful_loose.update(gov_loose & set(loose_series[meaningful_mask].tolist()))
            if hcol:
                hs = set(horses.tolist())
                matched_horse.update(gov_horse & hs)
            if len(samples) < 8:
                for gc in gear_cols:
                    if gc in chunk.columns:
                        ser = chunk[gc].astype(str).str.strip()
                        for v in ser[ser.ne("")].head(4).tolist():
                            if v.lower() not in ("nan", "none", "null"):
                                samples.append(f"{gc}={v[:120]}")
                                if len(samples) >= 8:
                                    break
                    if len(samples) >= 8:
                        break
        if dates_seen:
            rec["min_date"] = sorted(dates_seen)[0]
            rec["max_date"] = sorted(dates_seen)[-1]
        rec["full_key_match_count"] = len(matched_full)
        rec["loose_track_race_horse_match_count"] = len(matched_loose)
        rec["horse_only_match_count"] = len(matched_horse)
        rec["meaningful_full_key_match_count"] = len(meaningful_full)
        rec["meaningful_loose_match_count"] = len(meaningful_loose)
        rec["sample_nonblank_gear_values"] = " | ".join(samples[:8])
        if rec["current_date_overlap"] == "YES" and (rec["meaningful_full_key_match_count"] > 0 or rec["meaningful_loose_match_count"] > 0):
            rec["safe_source_candidate"] = "YES"
            safe_sources += 1
    except Exception as exc:
        rec["read_status"] = f"READ_ERROR: {exc}"
    rows.append(rec)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
best_full = int(out["meaningful_full_key_match_count"].max()) if not out.empty else 0
best_loose = int(out["meaningful_loose_match_count"].max()) if not out.empty else 0
summary_rows = [
    {"metric": "status", "value": "CURRENT_GEAR_SOURCE_FOUND" if safe_sources else "NO_CURRENT_GEAR_SOURCE_FOUND"},
    {"metric": "files_scanned", "value": files_scanned},
    {"metric": "candidate_files", "value": candidate_files},
    {"metric": "safe_source_candidates", "value": safe_sources},
    {"metric": "governed_rows", "value": len(gov)},
    {"metric": "governed_dates", "value": "|".join(sorted(gov_dates))},
    {"metric": "governed_tracks", "value": "|".join(sorted(gov_tracks))},
    {"metric": "best_full_key_match_count", "value": best_full},
    {"metric": "best_loose_match_count", "value": best_loose},
    {"metric": "production_changed", "value": "NO"},
    {"metric": "pricing_changed", "value": "NO"},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
]
pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)
if safe_sources:
    top = out[out["safe_source_candidate"] == "YES"].sort_values(["meaningful_full_key_match_count", "meaningful_loose_match_count"], ascending=False).head(10)
    top_lines = [f"- {r.file}: meaningful_full={r.meaningful_full_key_match_count}, meaningful_loose={r.meaningful_loose_match_count}, dates={r.min_date}..{r.max_date}" for _, r in top.iterrows()]
else:
    top_lines = ["- No file with current governed date overlap and safe race/horse key overlap was found."]
REPORT.write_text("\n".join([
    "EDGEIQ_CURRENT_GEAR_SOURCE_DISCOVERY_V1",
    "=======================================",
    f"Status: {'CURRENT_GEAR_SOURCE_FOUND' if safe_sources else 'NO_CURRENT_GEAR_SOURCE_FOUND'}",
    f"Files scanned: {files_scanned}",
    f"Candidate files: {candidate_files}",
    f"Safe source candidates: {safe_sources}",
    f"Best full key match count: {best_full}",
    f"Best loose match count: {best_loose}",
    f"Governed dates: {'|'.join(sorted(gov_dates))}",
    f"Governed tracks: {'|'.join(sorted(gov_tracks))}",
    "",
    "Top/source findings:",
    *top_lines,
    "",
    "Production changed: NO",
    "Pricing changed: NO",
    "Probability changed: NO",
    "V6.1 changed: NO",
    "V7.2G2 changed: NO",
    "UI changed: NO",
]) + "\n", encoding="utf-8")
print("CURRENT_GEAR_SOURCE_DISCOVERY_COMPLETE", safe_sources, candidate_files)

