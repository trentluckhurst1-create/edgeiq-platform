from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

ROOT = Path(".")
DATA = Path("public/data")
OUT_INV = DATA / "edgeiq_repository_inventory_v1.csv"
OUT_ACTIVE = DATA / "edgeiq_active_file_manifest_v1.csv"
OUT_DEP = DATA / "edgeiq_script_dependency_map_v1.csv"
OUT_DEPR = DATA / "edgeiq_deprecated_file_candidates_v1.csv"
OUT_PLAN = DATA / "EDGEIQ_REPOSITORY_CONSOLIDATION_PLAN_V1.txt"

SCAN_ROOTS = [Path("."), Path("scripts"), Path("public/data"), Path("src")]
ACTIVE_PRODUCTION_DATA = {
    "edgeiq_live_runner_board_governed_v1.csv",
    "edgeiq_live_runner_board_v1.csv",
    "edgeiq_live_terminal_feed_v1.csv",
    "edgeiq_vic_three_day_meeting_universe.csv",
    "edgeiq_intelligence_mode_engine_v2.csv",
    "edgeiq_runner_drawer_feed_v3.csv",
    "edgeiq_gear_signal_engine_v1.csv",
    "edgeiq_debutant_intelligence_engine_v1.csv",
    "edgeiq_market_alignment_engine_v1.csv",
}
ACTIVE_SCRIPTS = {
    "run_edgeiq_vic_master_orchestrator.py",
    "build_edgeiq_live_terminal_feed_v1.py",
    "build_edgeiq_live_runner_board_from_terminal_v1.py",
    "build_edgeiq_live_runner_board_governed_v1.py",
    "build_edgeiq_market_alignment_engine_v1.py",
    "build_edgeiq_dynamic_confidence_engine_v1.py",
    "build_edgeiq_debutant_intelligence_engine_v1.py",
    "build_edgeiq_gear_profile_engine_v1.py",
    "build_edgeiq_gear_signal_engine_v1.py",
    "build_edgeiq_intelligence_mode_engine_v2.py",
    "build_edgeiq_runner_drawer_feed_v3.py",
    "build_edgeiq_current_gear_live_join_v1.py",
    "apply_edgeiq_current_gear_to_governed_board_v1.py",
}
ACTIVE_FEED_TERMS = ["feed", "engine", "live_runner_board", "live_terminal", "meeting_universe"]

def rel(path): return str(path.as_posix())
def upper_name(path): return path.name.upper()
def classify(path):
    name = path.name
    uname = upper_name(path)
    lower = name.lower()
    parts = [p.lower() for p in path.parts]
    if any(x in uname for x in ["RECOVERY"]):
        return "RECOVERY"
    if any(x in uname for x in ["BACKUP", "CHECKPOINT", "PRE_"]):
        return "CHECKPOINT_BACKUP"
    if any(x in uname for x in ["CANDIDATE", "STAGING", "PREVIEW"]):
        if any(x in uname for x in ["OLD", "DEPRECATED", "STALE"]):
            return "DEPRECATED_CANDIDATE"
        return "CANDIDATE"
    if name in ACTIVE_PRODUCTION_DATA or name in {"RaceIntelligenceScreen.tsx", "App.tsx", "main.tsx"}:
        return "ACTIVE_PRODUCTION"
    if name in ACTIVE_SCRIPTS:
        return "ACTIVE_ENGINE"
    if path.suffix.lower() == ".py" and path.parts and path.parts[0] == "scripts":
        if lower.startswith("audit_") or "audit" in lower:
            return "AUDIT"
        if lower.startswith("build_") or lower.startswith("run_") or lower.startswith("apply_"):
            return "ACTIVE_ENGINE" if any(term in lower for term in ["live", "governed", "market_alignment", "debutant", "gear", "intelligence_mode", "runner_drawer", "terminal"]) else "RESEARCH"
        return "UNKNOWN_REVIEW"
    if any(term in lower for term in ["summary", "report"]):
        return "SUMMARY_REPORT"
    if "audit" in lower:
        return "AUDIT"
    if any(term in lower for term in ["research", "replay", "sensitivity", "impact"]):
        return "RESEARCH"
    if path.suffix.lower() == ".csv" and any(term in lower for term in ACTIVE_FEED_TERMS):
        return "ACTIVE_FEED"
    if path.suffix.lower() in [".tsx", ".ts", ".css", ".html", ".json"] and "src" in parts:
        return "ACTIVE_PRODUCTION"
    return "UNKNOWN_REVIEW"

def target_folder(classification, path):
    if classification == "ACTIVE_PRODUCTION": return "EDGEiQ_RACING/01_app" if "src" in [p.lower() for p in path.parts] else "EDGEiQ_RACING/03_data_active"
    if classification == "ACTIVE_ENGINE": return "EDGEiQ_RACING/02_scripts_active"
    if classification == "ACTIVE_FEED": return "EDGEiQ_RACING/03_data_active"
    if classification == "RESEARCH": return "EDGEiQ_RACING/04_data_research"
    if classification in ["AUDIT", "SUMMARY_REPORT"]: return "EDGEiQ_RACING/06_audits"
    if classification == "CHECKPOINT_BACKUP": return "EDGEiQ_RACING/07_checkpoints"
    if classification in ["CANDIDATE", "RECOVERY", "DEPRECATED_CANDIDATE"]: return "EDGEiQ_RACING/10_deprecated"
    return "EDGEiQ_RACING/09_handover"

def purpose_from_name(name):
    stem = Path(name).stem.replace("edgeiq_", "").replace("build_", "").replace("audit_", "").replace("_", " ")
    return stem[:120]

# Avoid duplicate files from overlapping scan roots.
seen = set()
files = []
for root in SCAN_ROOTS:
    if not root.exists():
        continue
    if root == Path("."):
        iterable = [p for p in root.iterdir() if p.is_file()]
    else:
        iterable = [p for p in root.rglob("*") if p.is_file()]
    for p in iterable:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        files.append(p)

rows=[]
for p in sorted(files, key=lambda x: rel(x).lower()):
    cls = classify(p)
    try:
        st = p.stat()
        size = st.st_size
        modified = datetime.fromtimestamp(st.st_mtime).isoformat()
    except Exception:
        size = 0; modified = ""
    rows.append({
        "file_path": rel(p),
        "file_name": p.name,
        "extension": p.suffix.lower(),
        "size_bytes": size,
        "last_modified": modified,
        "classification": cls,
        "proposed_folder": target_folder(cls, p),
        "purpose_inferred": purpose_from_name(p.name),
        "move_now": "NO",
    })
inv = pd.DataFrame(rows)
inv.to_csv(OUT_INV, index=False)
active = inv[inv["classification"].isin(["ACTIVE_PRODUCTION", "ACTIVE_ENGINE", "ACTIVE_FEED"])].copy()
active.to_csv(OUT_ACTIVE, index=False)
dep = inv[inv["classification"].isin(["CHECKPOINT_BACKUP", "CANDIDATE", "RECOVERY", "DEPRECATED_CANDIDATE", "UNKNOWN_REVIEW"])].copy()
dep["review_reason"] = dep["classification"].map({
    "CHECKPOINT_BACKUP": "Backup/checkpoint should be archived after approval.",
    "CANDIDATE": "Candidate/staging artifact; keep out of active chain unless promoted.",
    "RECOVERY": "Recovery artifact; archive after current production path is verified.",
    "DEPRECATED_CANDIDATE": "Likely stale candidate.",
    "UNKNOWN_REVIEW": "Could not classify safely; manual review required.",
})
dep.to_csv(OUT_DEPR, index=False)

script_rows=[]
file_ref_pattern = re.compile(r"[A-Za-z0-9_./\\-]+\.(?:csv|txt|json|tsx|ts|py)")
for p in sorted(Path("scripts").glob("*.py")) if Path("scripts").exists() else []:
    text = ""
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass
    refs = sorted(set(m.group(0).replace("\\", "/") for m in file_ref_pattern.finditer(text)))
    outputs = [r for r in refs if any(token in r.lower() for token in ["out", "summary", "report", "audit", "public/data"])]
    script_rows.append({
        "script": rel(p),
        "classification": classify(p),
        "purpose_inferred": purpose_from_name(p.name),
        "referenced_files": "|".join(refs[:80]),
        "referenced_file_count": len(refs),
        "possible_output_refs": "|".join(outputs[:80]),
        "manual_review_needed": "YES" if not refs else "NO",
    })
pd.DataFrame(script_rows).to_csv(OUT_DEP, index=False)

counts = inv["classification"].value_counts().to_dict()
active_counts = active["classification"].value_counts().to_dict() if not active.empty else {}
review_count = int((inv["classification"] == "UNKNOWN_REVIEW").sum())
plan_lines = [
    "EDGEIQ_REPOSITORY_CONSOLIDATION_PLAN_V1",
    "========================================",
    "Status: AUDIT_ONLY_NO_FILES_MOVED",
    "",
    "Target future folder:",
    "EDGEiQ_RACING/",
    "01_app/",
    "02_scripts_active/",
    "03_data_active/",
    "04_data_research/",
    "05_data_archives/",
    "06_audits/",
    "07_checkpoints/",
    "08_docs/",
    "09_handover/",
    "10_deprecated/",
    "",
    "Inventory counts:",
]
for k in sorted(counts):
    plan_lines.append(f"- {k}: {counts[k]}")
plan_lines.extend([
    "",
    "Files to keep active:",
])
for _, r in active.head(80).iterrows():
    plan_lines.append(f"- {r.file_path} -> {r.proposed_folder}")
plan_lines.extend([
    "",
    "Files to archive/review:",
    f"- Deprecated/checkpoint/candidate/unknown rows listed in {OUT_DEPR.name}: {len(dep)}",
    f"- Unknown manual review rows: {review_count}",
    "",
    "Proposed folder mapping:",
    "- ACTIVE_PRODUCTION src files -> EDGEiQ_RACING/01_app/",
    "- ACTIVE_PRODUCTION data and ACTIVE_FEED -> EDGEiQ_RACING/03_data_active/",
    "- ACTIVE_ENGINE scripts -> EDGEiQ_RACING/02_scripts_active/",
    "- RESEARCH -> EDGEiQ_RACING/04_data_research/",
    "- AUDIT and SUMMARY_REPORT -> EDGEiQ_RACING/06_audits/",
    "- CHECKPOINT_BACKUP -> EDGEiQ_RACING/07_checkpoints/",
    "- CANDIDATE/RECOVERY/DEPRECATED_CANDIDATE -> EDGEiQ_RACING/10_deprecated/",
    "- UNKNOWN_REVIEW -> EDGEiQ_RACING/09_handover/ until manually classified",
    "",
    "Migration risks:",
    "- Scripts often reference public/data relative paths; moving files before path refactor will break builds.",
    "- UI/public assets expect /data/... paths under public/data.",
    "- Candidate and checkpoint files may share similar names with active feeds; do not bulk delete.",
    "- OneDrive sync can preserve stale duplicates; use hashes before archival.",
    "",
    "DO NOT MOVE FILES UNTIL APPROVED",
    "Production changed: NO",
    "Pricing changed: NO",
    "Probability changed: NO",
    "V6.1 changed: NO",
    "V7.2G2 changed: NO",
    "UI changed: NO",
    f"Built at: {datetime.now(timezone.utc).isoformat()}",
])
OUT_PLAN.write_text("\n".join(plan_lines) + "\n", encoding="utf-8")
print("REPOSITORY_CONSOLIDATION_AUDIT_COMPLETE", len(inv), counts)

