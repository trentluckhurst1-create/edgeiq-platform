from pathlib import Path
import re
from collections import defaultdict

ROOT = Path(".")
SRC = ROOT / "src"
OUT_DIR = ROOT / "public" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT = OUT_DIR / "edgeiq_production_dependency_audit_v1.txt"
CSV = OUT_DIR / "edgeiq_production_dependency_audit_v1.csv"
MANIFEST = OUT_DIR / "edgeiq_production_manifest_v1.txt"

EXTS = {".ts", ".tsx"}

IGNORE_PARTS = {
    "node_modules",
    "dist",
    ".git",
    "__pycache__",
}

PRODUCTION_ROOT_HINTS = [
    "src/edgeiq-os/",
]

LEGACY_HINTS = [
    "src/components/",
    "src/services/",
    "src/lib/",
    "src/utils/",
    "src/terminal/",
]

CHECKPOINT_HINTS = [
    "BEFORE_",
    "CHECKPOINT",
    "_LOCKED",
    "checkpoint",
    "checkpoints",
    "before_",
]

SERVICE_KEYWORDS = [
    "race-file",
    "raceFile",
    "RunnerHistory",
    "SpeedProfile",
    "TrackSignature",
    "RaceFlow",
    "RaceStrength",
    "RunRating",
    "RunnerDNA",
    "MarketBehaviour",
    "Pressure",
    "Tempo",
    "Position",
    "Evidence",
    "Command",
    "operational-state",
    "intelligence",
]

IMPORT_RE = re.compile(r'^\s*import\s+(?:type\s+)?(?:[\s\S]*?)\s+from\s+[\'"]([^\'"]+)[\'"]', re.MULTILINE)
EXPORT_RE = re.compile(r'^\s*export\s+(?:type\s+)?(?:[\s\S]*?)\s+from\s+[\'"]([^\'"]+)[\'"]', re.MULTILINE)

def norm(path: Path) -> str:
    return path.as_posix()

def skip(path: Path) -> bool:
    return any(part in IGNORE_PARTS for part in path.parts)

def is_code(path: Path) -> bool:
    return path.suffix in EXTS and not skip(path)

def is_checkpoint(path: str) -> bool:
    return any(hint in path for hint in CHECKPOINT_HINTS)

def is_production(path: str) -> bool:
    return any(path.startswith(hint) for hint in PRODUCTION_ROOT_HINTS) and not is_checkpoint(path)

def is_legacy(path: str) -> bool:
    return any(path.startswith(hint) for hint in LEGACY_HINTS) or is_checkpoint(path)

def classify(path: str) -> str:
    if is_production(path):
        return "PRODUCTION"
    if is_checkpoint(path):
        return "CHECKPOINT"
    if is_legacy(path):
        return "LEGACY"
    return "OTHER"

def resolve_import(base: Path, spec: str) -> str:
    if not spec.startswith("."):
        return spec

    raw = (base.parent / spec).resolve()
    project = ROOT.resolve()

    candidates = []
    if raw.suffix:
        candidates.append(raw)
    else:
        for ext in [".ts", ".tsx"]:
            candidates.append(raw.with_suffix(ext))
        for ext in [".ts", ".tsx"]:
            candidates.append(raw / ("index" + ext))

    for candidate in candidates:
        if candidate.exists():
            try:
                return candidate.relative_to(project).as_posix()
            except ValueError:
                return candidate.as_posix()

    try:
        return raw.relative_to(project).as_posix()
    except ValueError:
        return str(raw)

files = sorted([p for p in SRC.rglob("*") if p.is_file() and is_code(p)], key=lambda p: norm(p))

imports_by_file = defaultdict(list)
imported_by = defaultdict(list)
classes = {}
service_candidates = []

for file in files:
    rel = norm(file)
    classes[rel] = classify(rel)

    text = file.read_text(encoding="utf-8", errors="ignore")
    specs = IMPORT_RE.findall(text) + EXPORT_RE.findall(text)

    for spec in specs:
        target = resolve_import(file, spec)
        imports_by_file[rel].append(target)
        imported_by[target].append(rel)

    if any(keyword.lower() in rel.lower() for keyword in SERVICE_KEYWORDS):
        service_candidates.append(rel)

unused_files = []
for file in files:
    rel = norm(file)
    if rel.endswith("main.tsx") or rel.endswith("App.tsx"):
        continue
    if len(imported_by.get(rel, [])) == 0:
        unused_files.append(rel)

production_files = [rel for rel, c in classes.items() if c == "PRODUCTION"]
legacy_files = [rel for rel, c in classes.items() if c == "LEGACY"]
checkpoint_files = [rel for rel, c in classes.items() if c == "CHECKPOINT"]

production_legacy_imports = []
for src, targets in imports_by_file.items():
    if classes.get(src) == "PRODUCTION":
        for target in targets:
            if target.startswith("src/") and classify(target) in {"LEGACY", "CHECKPOINT"}:
                production_legacy_imports.append((src, target))

groups = defaultdict(list)
for rel in service_candidates:
    lower = rel.lower()
    if "race-file" in lower or "racefile" in lower:
        groups["RaceFile"].append(rel)
    elif "runner" in lower and "dna" in lower:
        groups["RunnerDNA"].append(rel)
    elif "runner" in lower and ("history" in lower or "profile" in lower or "metric" in lower):
        groups["RunnerHistory"].append(rel)
    elif "speed" in lower or "standard" in lower:
        groups["SpeedProfile"].append(rel)
    elif "track" in lower:
        groups["TrackSignature"].append(rel)
    elif "raceflow" in lower or "race-flow" in lower or "race_shape" in lower:
        groups["RaceFlow"].append(rel)
    elif "strength" in lower:
        groups["RaceStrength"].append(rel)
    elif "rating" in lower:
        groups["RunRating"].append(rel)
    elif "market" in lower:
        groups["MarketBehaviour"].append(rel)
    elif "pressure" in lower:
        groups["Pressure"].append(rel)
    elif "tempo" in lower:
        groups["Tempo"].append(rel)
    elif "position" in lower:
        groups["Position"].append(rel)
    elif "evidence" in lower:
        groups["Evidence"].append(rel)
    elif "command" in lower:
        groups["Command"].append(rel)
    else:
        groups["OtherIntelligence"].append(rel)

def section(title: str, rows: list[str]) -> str:
    out = [title, "-" * len(title)]
    if rows:
        out.extend(rows)
    else:
        out.append("NONE")
    return "\n".join(out)

report_lines = []
report_lines.append("EDGEIQ PRODUCTION DEPENDENCY AUDIT V1")
report_lines.append("=" * 44)
report_lines.append("")
report_lines.append(f"Total TS/TSX files: {len(files)}")
report_lines.append(f"Production files: {len(production_files)}")
report_lines.append(f"Legacy files: {len(legacy_files)}")
report_lines.append(f"Checkpoint files: {len(checkpoint_files)}")
report_lines.append(f"Unused/unreferenced files: {len(unused_files)}")
report_lines.append(f"Production -> legacy imports: {len(production_legacy_imports)}")
report_lines.append("")

report_lines.append(section("PRODUCTION FILES", production_files[:300]))
report_lines.append("")
report_lines.append(section("PRODUCTION IMPORTS FROM LEGACY/CHECKPOINT", [f"{a} -> {b}" for a,b in production_legacy_imports]))
report_lines.append("")
report_lines.append(section("UNUSED OR UNREFERENCED FILES", unused_files[:500]))
report_lines.append("")
report_lines.append(section("LEGACY FILES", legacy_files[:500]))
report_lines.append("")
report_lines.append(section("CHECKPOINT FILES", checkpoint_files[:500]))
report_lines.append("")

report_lines.append("INTELLIGENCE SERVICE CANDIDATE GROUPS")
report_lines.append("-------------------------------------")
for group, paths in sorted(groups.items()):
    report_lines.append("")
    report_lines.append(f"{group} ({len(paths)})")
    for p in sorted(paths):
        report_lines.append(f"  - {p}")

REPORT.write_text("\n".join(report_lines), encoding="utf-8")

csv_lines = ["path,classification,import_count,imported_by_count"]
for rel in sorted(classes):
    csv_lines.append(f'"{rel}","{classes[rel]}",{len(imports_by_file.get(rel, []))},{len(imported_by.get(rel, []))}')
CSV.write_text("\n".join(csv_lines), encoding="utf-8")

manifest_lines = []
manifest_lines.append("EDGEIQ PRODUCTION MANIFEST V1")
manifest_lines.append("=" * 34)
manifest_lines.append("")
manifest_lines.append("PRODUCTION ROOT")
manifest_lines.append("src/edgeiq-os")
manifest_lines.append("")
manifest_lines.append("CANONICAL SERVICE TARGETS")
manifest_lines.append("-------------------------")
for name in [
    "RaceFileService",
    "RunnerHistoryService",
    "RunnerDNAService",
    "SpeedProfileService",
    "RaceStrengthService",
    "RunRatingService",
    "RaceFlowService",
    "TrackSignatureService",
    "PressureService",
    "TempoService",
    "PositionService",
    "MarketBehaviourService",
    "CommandService",
    "EvidenceService",
]:
    manifest_lines.append(f"- {name}")
manifest_lines.append("")
manifest_lines.append("CURRENT PRODUCTION FILES")
manifest_lines.append("------------------------")
manifest_lines.extend(production_files)

MANIFEST.write_text("\n".join(manifest_lines), encoding="utf-8")

print("[EDGEIQ] Production dependency audit built")
print(f"report={REPORT}")
print(f"csv={CSV}")
print(f"manifest={MANIFEST}")
