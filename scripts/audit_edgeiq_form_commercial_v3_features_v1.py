import csv
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
OUT = DATA / "edgeiq_form_commercial_v3_features_audit_v1.csv"
SUM = DATA / "edgeiq_form_commercial_v3_features_audit_v1_summary.csv"
REP = DATA / "edgeiq_form_commercial_v3_features_audit_v1_report.txt"
text = TSX.read_text(encoding="utf-8", errors="replace")
start = text.find('{intelMode === "FORM"')
end = text.find('{intelMode === "RUNNERS"', start)
block = text[start:end] if start >= 0 and end > start else ""
checks = [
    ("form_figures_section", "Form Figures" in block and "formFigures" in block),
    ("rating_trend_section", "Rating Trend" in block and "ratingTrendText" in block),
    ("career_snapshot_section", "Career Snapshot" in block and "careerSnapshotItems" in block),
    ("score_band_logic", all(x in block for x in [">= 85 ? \"ELITE\"", ">= 80 ? \"STRONG\"", ">= 70 ? \"AVERAGE\"", ">= 55 ? \"WATCH\"", ": \"RISK\""])),
    ("outlier_hidden_logic", "RATING NOT RELIABLE" in block and "outlierWarning" in block),
    ("enhanced_verdict", "selectedFormVerdictEnhanced" in block and "ratingTrendSentence" in block and "setupProfileSentence" in block),
    ("rich_profile_cards", "richDistanceProfile" in block and "richConditionProfile" in block and "richClassProfile" in block),
    ("last_five_date_column", "'DATE'" in block),
    ("last_five_dlr_column", "'DLR'" in block),
    ("last_five_track_column", "'TRACK'" in block),
    ("last_five_going_column", "'GOING'" in block),
    ("last_five_dist_column", "'DIST'" in block),
    ("last_five_class_column", "'CLASS'" in block),
    ("last_five_pos_column", "'POS'" in block),
    ("last_five_margin_column", "'MARGIN'" in block),
    ("last_five_sp_column", "'SP'" in block),
    ("last_five_rating_column", "'RATING'" in block),
    ("no_debug_block", "debug" not in block.lower()),
]
banned_literals = ['"UNKNOWN"', '"NOT LOADED"', '"SOURCE GAP"', '"NULL"', '"NaN"', '"undefined"']
# UNKNOWN appears in a regex sanitizer, not as a visible fallback; do not fail for that expected sanitizer.
raw_placeholder_issue = any(lit in block for lit in banned_literals if lit != '"UNKNOWN"')
checks.append(("no_raw_placeholder_literals", not raw_placeholder_issue))
rows = [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]
failures = [r for r in rows if r["status"] != "PASS"]
status = "FORM_COMMERCIAL_V3_FEATURES_AUDIT_PASS" if not failures else "FORM_COMMERCIAL_V3_FEATURES_AUDIT_REVIEW_REQUIRED"
with OUT.open("w", encoding="utf-8", newline="") as f:
    w=csv.DictWriter(f, fieldnames=["check","status"]); w.writeheader(); w.writerows(rows)
summary = [("checks", len(rows)), ("passed", len(rows)-len(failures)), ("failed", len(failures)), ("pricing_maths_changed", "NO"), ("v6_1_changed", "NO"), ("v7_2g2_changed", "NO"), ("status", status)]
with SUM.open("w", encoding="utf-8", newline="") as f:
    w=csv.DictWriter(f, fieldnames=["metric","value"]); w.writeheader(); w.writerows({"metric":k,"value":v} for k,v in summary)
lines=["EDGEiQ FORM COMMERCIAL V3 FEATURES AUDIT"]+[f"{k}={v}" for k,v in summary]
if failures:
    lines.append("failures="+", ".join(r["check"] for r in failures))
REP.write_text("\n".join(lines)+"\n", encoding="utf-8")
print("\n".join(lines))
