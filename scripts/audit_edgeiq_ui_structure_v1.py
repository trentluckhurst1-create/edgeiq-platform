from pathlib import Path
import csv
import re
from datetime import datetime, timezone
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_ui_structure_audit_v1.csv"
SUMMARY = DATA / "edgeiq_ui_structure_audit_v1_summary.csv"
REPORT = DATA / "edgeiq_ui_structure_audit_v1_report.txt"

FRONTEND_EXTS = {".tsx", ".ts", ".jsx", ".js", ".css"}
CHECKPOINT_MARKERS = ("CHECKPOINT", "BEFORE", "UI_LOCKED", "WORKING", "MASTER_LOCK", ".old", ".backup")
COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|linear-gradient|radial-gradient")
STYLE_RE = re.compile(r"style=\{\{")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def write_csv(path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        fields = []
        for row in rows:
            for key in row.keys():
                if key not in fields:
                    fields.append(key)
        fieldnames = fields
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def file_role(path: Path, text: str) -> str:
    name = path.name
    rp = rel(path)
    if name == "main.tsx":
        return "MAIN_APP_ENTRY"
    if name == "App.tsx":
        return "APP_SHELL"
    if name == "RaceIntelligenceScreen.tsx":
        return "RACE_INTELLIGENCE_COMPONENT"
    if rp.startswith("src/styles/") or path.suffix == ".css":
        return "CSS_STYLE_SURFACE"
    if "terminal/tabs" in rp:
        return "TERMINAL_TAB_COMPONENT"
    if "components" in rp and path.suffix in {".tsx", ".jsx"}:
        return "COMPONENT"
    if name in {"package.json", "package-lock.json", "vite.config.ts", "tsconfig.json"}:
        return "PACKAGE_OR_CONFIG"
    return "FRONTEND_SOURCE"


def main():
    rows = []
    files = []
    for base in [SRC, ROOT]:
        if base == ROOT:
            candidates = [ROOT / "package.json", ROOT / "package-lock.json", ROOT / "vite.config.ts", ROOT / "tsconfig.json", ROOT / "tsconfig.app.json", ROOT / "tsconfig.node.json"]
        else:
            candidates = [p for p in SRC.rglob("*") if p.is_file() and p.suffix in FRONTEND_EXTS]
        for path in candidates:
            if path.exists() and path not in files:
                files.append(path)

    for path in sorted(files):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            text = f"READ_ERROR: {exc}"
        checkpoint_like = any(marker in path.name.upper() for marker in CHECKPOINT_MARKERS)
        role = file_role(path, text)
        inline_style_count = len(STYLE_RE.findall(text)) if path.suffix in {".tsx", ".jsx"} else 0
        color_count = len(COLOR_RE.findall(text))
        class_count = text.count("className=") if path.suffix in {".tsx", ".jsx"} else text.count(".")
        requires_checkpoint = "YES" if role in {"MAIN_APP_ENTRY", "APP_SHELL", "RACE_INTELLIGENCE_COMPONENT", "CSS_STYLE_SURFACE"} and not checkpoint_like else "NO"
        issue_flags = []
        if checkpoint_like:
            issue_flags.append("LEGACY_CHECKPOINT_OR_BACKUP")
        if inline_style_count > 25:
            issue_flags.append("HEAVY_INLINE_STYLING")
        if color_count > 30:
            issue_flags.append("HEAVY_LOCAL_COLOR_USAGE")
        if role == "CSS_STYLE_SURFACE" and path.name.startswith("index_"):
            issue_flags.append("LEGACY_CSS_BACKUP")
        rows.append({
            "file_path": rel(path),
            "file_name": path.name,
            "extension": path.suffix,
            "role": role,
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "line_count": text.count("\n") + 1,
            "checkpoint_like": "YES" if checkpoint_like else "NO",
            "inline_style_count": inline_style_count,
            "local_color_usage_count": color_count,
            "class_or_selector_count": class_count,
            "requires_checkpoint_before_rewrite": requires_checkpoint,
            "issue_flags": "|".join(issue_flags) if issue_flags else "OK",
        })

    role_counts = Counter(row["role"] for row in rows)
    issue_counts = Counter()
    for row in rows:
        for flag in row["issue_flags"].split("|"):
            issue_counts[flag] += 1

    checkpoint_required = [r for r in rows if r["requires_checkpoint_before_rewrite"] == "YES"]
    active_frontend = [r for r in rows if r["checkpoint_like"] == "NO" and r["extension"] in FRONTEND_EXTS]
    summary = [
        {"metric": "status", "value": "UI_STRUCTURE_AUDIT_COMPLETE"},
        {"metric": "files_audited", "value": len(rows)},
        {"metric": "active_frontend_files", "value": len(active_frontend)},
        {"metric": "checkpoint_or_backup_like_files", "value": sum(1 for r in rows if r["checkpoint_like"] == "YES")},
        {"metric": "css_files", "value": role_counts.get("CSS_STYLE_SURFACE", 0)},
        {"metric": "main_app_entry", "value": "src/main.tsx"},
        {"metric": "home_page_component", "value": "src/components/RaceIntelligenceScreen.tsx"},
        {"metric": "race_intelligence_component", "value": "src/components/RaceIntelligenceScreen.tsx"},
        {"metric": "app_shell_component", "value": "src/App.tsx"},
        {"metric": "files_requiring_checkpoint_before_rewrite", "value": len(checkpoint_required)},
        {"metric": "heavy_inline_styling_files", "value": issue_counts.get("HEAVY_INLINE_STYLING", 0)},
        {"metric": "heavy_local_color_usage_files", "value": issue_counts.get("HEAVY_LOCAL_COLOR_USAGE", 0)},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "built_at", "value": now_iso()},
    ]

    report = [
        "EDGEiQ UI Structure Audit V1",
        "==============================",
        "Status: UI_STRUCTURE_AUDIT_COMPLETE",
        "Main app entry: src/main.tsx",
        "App shell: src/App.tsx",
        "Home / race intelligence component: src/components/RaceIntelligenceScreen.tsx",
        "Primary CSS surfaces: src/index.css, src/styles/terminal-primitives.css, src/terminal/layout/terminal-shell.css, src/components/race-intelligence-screen.css",
        f"Files audited: {len(rows)}",
        f"Active frontend files: {len(active_frontend)}",
        f"Checkpoint/backup-like files: {sum(1 for r in rows if r['checkpoint_like'] == 'YES')}",
        f"Heavy inline styling files: {issue_counts.get('HEAVY_INLINE_STYLING', 0)}",
        f"Heavy local color usage files: {issue_counts.get('HEAVY_LOCAL_COLOR_USAGE', 0)}",
        "Design finding: active RaceIntelligenceScreen owns HOME, MEETING and RACE product views but relies heavily on inline styling.",
        "Design finding: legacy checkpoint files are numerous and must be filtered out of active UI work.",
        "Files requiring checkpoint before rewrite: " + ", ".join(r["file_path"] for r in checkpoint_required[:20]),
        "Production changed: NO",
        "Pricing changed: NO",
        "Probability changed: NO",
        "V6.1 changed: NO",
        "V7.2G2 changed: NO",
    ]
    write_csv(OUT, rows)
    write_csv(SUMMARY, summary, ["metric", "value"])
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("UI_STRUCTURE_AUDIT_COMPLETE")


if __name__ == "__main__":
    main()
