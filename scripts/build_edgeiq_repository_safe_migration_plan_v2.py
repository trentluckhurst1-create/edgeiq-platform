from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import hashlib

DATA = Path("public/data")
V1 = DATA / "EDGEIQ_REPOSITORY_CONSOLIDATION_PLAN_V1.txt"
INV = DATA / "edgeiq_repository_inventory_v1.csv"
ACTIVE = DATA / "edgeiq_active_file_manifest_v1.csv"
CHAIN = DATA / "edgeiq_active_build_chain_manifest_v1.csv"
OUT_TXT = DATA / "EDGEIQ_REPOSITORY_SAFE_MIGRATION_PLAN_V2.txt"
OUT_MANIFEST = DATA / "edgeiq_repository_safe_migration_plan_v2_active_copy_manifest.csv"
OUT_SUMMARY = DATA / "edgeiq_repository_safe_migration_plan_v2_summary.csv"

def is_checkpoint_like(name):
    upper = name.upper()
    return any(token in upper for token in ["BEFORE", "CHECKPOINT", "BACKUP", "PRE_", "RECOVERY", "CANDIDATE", "STAGING", "PREVIEW"])

def sha256_file(path):
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
if not V1.exists():
    raise FileNotFoundError(V1)
if not INV.exists():
    raise FileNotFoundError(INV)
if not CHAIN.exists():
    raise FileNotFoundError(CHAIN)

inv = pd.read_csv(INV, dtype=str, keep_default_na=False)
chain = pd.read_csv(CHAIN, dtype=str, keep_default_na=False)
active = pd.read_csv(ACTIVE, dtype=str, keep_default_na=False) if ACTIVE.exists() else pd.DataFrame()

# V2 tight active allow-list: production-critical app files, active chain scripts, and direct chain outputs/inputs.
chain_scripts = set(chain["script"].astype(str))
chain_refs = set()
for col in ["input_files", "output_files"]:
    for val in chain[col].astype(str):
        for part in val.replace("|", ";").split(";"):
            p = part.strip()
            if p and not p.lower().startswith(("raw/", "raw", "terminal/")) and p not in ["dynamic confidence outputs if present"]:
                chain_refs.add(Path(p).name)

always_keep_data = {
    "edgeiq_live_runner_board_governed_v1.csv",
    "edgeiq_live_runner_board_v1.csv",
    "edgeiq_live_terminal_feed_v1.csv",
    "edgeiq_vic_three_day_meeting_universe.csv",
    "edgeiq_intelligence_mode_engine_v2.csv",
    "edgeiq_runner_drawer_feed_v3.csv",
    "edgeiq_gear_signal_engine_v1.csv",
    "edgeiq_debutant_intelligence_engine_v1.csv",
    "edgeiq_market_alignment_engine_v1.csv",
    "edgeiq_historical_results_warehouse_v2_graphql.csv",
    "gear_changes.csv",
}
app_keep_suffixes = (".tsx", ".ts", ".css", ".html", ".json")
app_keep_roots = ("src/", "public/")

rows = []
for _, r in inv.iterrows():
    path = r.get("file_path", "")
    name = r.get("file_name", "")
    classification = r.get("classification", "")
    keep = False
    reason = ""
    target = ""
    lower_path = path.replace("\\", "/").lower()
    if lower_path.startswith("src/") and Path(name).suffix.lower() in app_keep_suffixes and not is_checkpoint_like(name):
        keep = True; reason = "APP_SOURCE_REQUIRED"; target = "EDGEiQ_RACING/01_app/" + path.replace("\\", "/")
    elif name in chain_scripts:
        keep = True; reason = "ACTIVE_BUILD_CHAIN_SCRIPT"; target = "EDGEiQ_RACING/02_scripts_active/"
    elif name in always_keep_data or name in chain_refs:
        keep = True; reason = "ACTIVE_CHAIN_DATA_DEPENDENCY"; target = "EDGEiQ_RACING/03_data_active/"
    elif lower_path in ["package.json", "package-lock.json", "vite.config.ts", "tsconfig.json", "tsconfig.app.json", "tsconfig.node.json", "index.html"]:
        keep = True; reason = "APP_BUILD_CONFIG"; target = "EDGEiQ_RACING/01_app/" + path.replace("\\", "/")
    elif classification in ["AUDIT", "SUMMARY_REPORT"] and name.startswith(("EDGEIQ_REPOSITORY", "edgeiq_repository", "edgeiq_active_build_chain", "edgeiq_current_gear_source")):
        keep = True; reason = "MIGRATION_AUDIT_DOC"; target = "EDGEiQ_RACING/08_docs/"
    if keep:
        rows.append({
            "source_path": path,
            "file_name": name,
            "classification_v1": classification,
            "copy_to": target if not target.endswith("/") else target + name,
            "keep_reason": reason,
            "source_exists": "YES" if Path(path).exists() else "NO",
            "source_size_bytes": Path(path).stat().st_size if Path(path).exists() else 0,
            "source_sha256": sha256_file(path),
            "copy_mode": "COPY_ONLY_DO_NOT_MOVE",
            "path_rewrite_required": "NO" if reason in ["ACTIVE_CHAIN_DATA_DEPENDENCY", "APP_SOURCE_REQUIRED", "APP_BUILD_CONFIG"] else "REVIEW",
        })

manifest = pd.DataFrame(rows).drop_duplicates(["source_path"]).sort_values(["copy_to", "source_path"])
manifest.to_csv(OUT_MANIFEST, index=False)
summary_rows = [
    {"metric": "status", "value": "SAFE_MIGRATION_PLAN_V2_CREATED_NO_FILES_MOVED"},
    {"metric": "active_copy_manifest_rows", "value": len(manifest)},
    {"metric": "app_source_files", "value": int((manifest["keep_reason"] == "APP_SOURCE_REQUIRED").sum()) if not manifest.empty else 0},
    {"metric": "active_build_chain_scripts", "value": int((manifest["keep_reason"] == "ACTIVE_BUILD_CHAIN_SCRIPT").sum()) if not manifest.empty else 0},
    {"metric": "active_chain_data_dependencies", "value": int((manifest["keep_reason"] == "ACTIVE_CHAIN_DATA_DEPENDENCY").sum()) if not manifest.empty else 0},
    {"metric": "app_build_config_files", "value": int((manifest["keep_reason"] == "APP_BUILD_CONFIG").sum()) if not manifest.empty else 0},
    {"metric": "migration_audit_docs", "value": int((manifest["keep_reason"] == "MIGRATION_AUDIT_DOC").sum()) if not manifest.empty else 0},
    {"metric": "files_moved", "value": "NO"},
    {"metric": "production_changed", "value": "NO"},
    {"metric": "pricing_changed", "value": "NO"},
    {"metric": "probability_changed", "value": "NO"},
    {"metric": "v6_1_changed", "value": "NO"},
    {"metric": "v7_2g2_changed", "value": "NO"},
    {"metric": "ui_changed", "value": "NO"},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
]
pd.DataFrame(summary_rows).to_csv(OUT_SUMMARY, index=False)

by_reason = manifest["keep_reason"].value_counts().to_dict() if not manifest.empty else {}
missing_scripts = chain[chain["script_exists"] != "YES"]["script"].tolist() if "script_exists" in chain.columns else []

lines = [
    "EDGEIQ_REPOSITORY_SAFE_MIGRATION_PLAN_V2",
    "==========================================",
    "Status: PLAN_ONLY_NO_FILES_MOVED",
    "",
    "Objective:",
    "Create a clean EDGEiQ_RACING structure with active files only, while preserving the current racing-dashboard app paths and build behaviour.",
    "",
    "Core safety decision:",
    "- Do not move, rename, or delete anything inside the current racing-dashboard workspace during V2.",
    "- Create EDGEiQ_RACING as a COPY-ONLY mirror/staging structure after approval.",
    "- The current app remains the source of truth until the copied structure passes validation.",
    "- public/data must remain available at the current app path because UI fetches use /data/... and scripts use public/data relative paths.",
    "",
    "Why V1 needs tightening:",
    "- V1 correctly warned not to move files, but its active list included many checkpoint files under public/data/checkpoints.",
    "- V2 treats checkpoint, backup, candidate, recovery, and unknown-review files as non-active unless explicitly referenced by the active build chain.",
    "- V2 active files are selected from app source files, build config, active chain scripts, and direct active chain data dependencies only.",
    "",
    "Proposed clean structure:",
    "EDGEiQ_RACING/",
    "01_app/                 copied app source/config only",
    "02_scripts_active/      active build-chain scripts only",
    "03_data_active/         active data dependencies and live feeds only",
    "04_data_research/       empty initially; add only approved research packs later",
    "05_data_archives/       empty initially; archival copy only after approval",
    "06_audits/              empty initially or selected audit CSVs after approval",
    "07_checkpoints/         empty initially; checkpoints stay in current repo until archive pass",
    "08_docs/                migration docs and handover notes",
    "09_handover/            manual review notes",
    "10_deprecated/          empty initially; no delete/move in V2",
    "",
    "V2 copy manifest:",
    f"- Manifest file: {OUT_MANIFEST.as_posix()}",
    f"- Active copy rows: {len(manifest)}",
]
for k in sorted(by_reason):
    lines.append(f"- {k}: {by_reason[k]}")
lines.extend([
    "",
    "Migration phases:",
    "Phase 0 - Freeze and verify current app",
    "1. Confirm current racing-dashboard build still passes before copying.",
    "2. Record hashes for active files in the V2 copy manifest.",
    "3. Do not touch pricing/probability/V6.1/V7.2G2 outputs.",
    "",
    "Phase 1 - Create empty EDGEiQ_RACING structure after approval",
    "1. Create folders only; do not copy data yet.",
    "2. Keep racing-dashboard as the working app.",
    "3. Add README/HANDOVER noting this is a mirror, not production path.",
    "",
    "Phase 2 - Copy active files only",
    "1. Copy rows from edgeiq_repository_safe_migration_plan_v2_active_copy_manifest.csv.",
    "2. Preserve relative app/public paths inside 01_app if a runnable mirror is desired.",
    "3. Do not copy checkpoints, recovery candidates, stale candidates, or unknown-review files.",
    "4. Do not delete originals.",
    "",
    "Phase 3 - Path-safe app strategy",
    "Recommended safest option: keep the runnable app in racing-dashboard and use EDGEiQ_RACING as a clean handover/mirror.",
    "If EDGEiQ_RACING must become runnable later, copy the app with its expected structure intact under EDGEiQ_RACING/01_app/racing-dashboard/ so /public/data and src imports remain unchanged.",
    "Do not flatten src/public/data into separate folders for a runnable app until scripts and UI fetch paths are rewritten and tested.",
    "",
    "Phase 4 - Validation in mirror only",
    "1. In the copied app root, run npm install only if node_modules is not copied and package files are present.",
    "2. Run npm run build from the copied app root, not from reorganised top-level folders.",
    "3. Run the active build-chain scripts with dry-run/copy outputs first if possible.",
    "4. Compare row counts and hashes against current active files.",
    "",
    "Phase 5 - Promotion decision",
    "1. Only after mirror validation passes, decide whether EDGEiQ_RACING becomes the new working root.",
    "2. If promoted, update scripts to use a central DATA_ROOT/APP_ROOT configuration rather than hard-coded public/data.",
    "3. Keep old racing-dashboard untouched until at least one full build cycle passes from the new root.",
    "",
    "Explicit no-go items:",
    "- Do not move files in V2.",
    "- Do not delete deprecated candidates in V2.",
    "- Do not rewrite app imports or /data fetch paths in V2.",
    "- Do not replace public/data with symlinks in V2 unless separately approved.",
    "- Do not copy all public/data; copy active manifest only.",
    "- Do not include stale gear refresh candidates as active files.",
    "",
    "Pre-migration validation commands:",
    "python -m py_compile .\\scripts\\audit_edgeiq_repository_consolidation_v1.py",
    "python -m py_compile .\\scripts\\build_edgeiq_active_build_chain_manifest_v1.py",
    "python -m py_compile .\\scripts\\build_edgeiq_repository_safe_migration_plan_v2.py",
    "npm run build",
    "",
    "Post-copy validation commands after approval:",
    "Get-ChildItem EDGEiQ_RACING -Recurse | Measure-Object",
    "Import-Csv .\\public\\data\\edgeiq_repository_safe_migration_plan_v2_active_copy_manifest.csv | Measure-Object",
    "npm run build  # from copied runnable app root only",
    "",
    "Blockers / risks:",
    f"- Active build-chain missing scripts: {len(missing_scripts)}",
    "- Current repository still has 5,000+ UNKNOWN_REVIEW files; do not classify them by filename alone for deletion.",
    "- public/data path dependence is the main breakage risk.",
    "- OneDrive may retain duplicate/stale files; use hash validation before any future archive/delete pass.",
    "",
    "Approval gate:",
    "Proceed to physical folder creation only after explicit approval for V2 Phase 1.",
    "",
    "Production changed: NO",
    "Pricing changed: NO",
    "Probability changed: NO",
    "V6.1 changed: NO",
    "V7.2G2 changed: NO",
    "UI changed: NO",
    "Files moved: NO",
    f"Built at: {datetime.now(timezone.utc).isoformat()}",
])
OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("SAFE_MIGRATION_PLAN_V2_CREATED", len(manifest), by_reason)




