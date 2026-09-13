from __future__ import annotations

from pathlib import Path
import shutil
import re

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "config": ROOT / "src" / "config" / "edgeiqFiles.ts",
    "loader": ROOT / "src" / "services" / "edgeiqDataLoader.ts",
    "enrichment": ROOT / "src" / "services" / "runnerEnrichmentService.ts",
    "metrics": ROOT / "src" / "services" / "runnerMetricsService.ts",
    "screen": ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, text: str) -> None:
    bak = path.with_suffix(path.suffix + ".v32_1.bak")
    if not bak.exists():
        shutil.copy2(path, bak)
    path.write_text(text, encoding="utf-8")


def replace_regex(path: Path, pattern: str, repl: str, label: str, flags: int = 0) -> None:
    text = read(path)
    if re.search(re.escape(repl), text):
        print(f"{label}=ALREADY_APPLIED")
        return
    new_text, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if n != 1:
        raise RuntimeError(f"V32.1 patch anchor not found: {label} in {path}")
    write(path, new_text)
    print(f"{label}=PATCHED")


def replace_literal(path: Path, old: str, new: str, label: str) -> None:
    text = read(path)
    if new in text:
        print(f"{label}=ALREADY_APPLIED")
        return
    if old not in text:
        raise RuntimeError(f"V32.1 patch anchor not found: {label} in {path}")
    write(path, text.replace(old, new, 1))
    print(f"{label}=PATCHED")


def main() -> None:
    missing = [str(p) for p in FILES.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing V32.1 target files: " + ", ".join(missing))

    # Config: insert after whichever runnerBoard path exists locally.
    path = FILES["config"]
    text = read(path)
    if 'sectionalSidecar:' not in text:
        m = re.search(r'(^\s*runnerBoard\s*:\s*"[^"]+",\s*$)', text, flags=re.M)
        if not m:
            raise RuntimeError(f"V32.1 patch anchor not found: CONFIG_SECTIONAL_SIDECAR in {path}")
        line = m.group(1)
        indent = re.match(r'\s*', line).group(0)
        new = line + f'\n{indent}sectionalSidecar: "/data/edgeiq_live_runner_board_sectionals_v31.csv",'
        write(path, text[:m.start()] + new + text[m.end():])
        print("CONFIG_SECTIONAL_SIDECAR=PATCHED")
    else:
        print("CONFIG_SECTIONAL_SIDECAR=ALREADY_APPLIED")

    # Loader type.
    replace_regex(
        FILES["loader"],
        r'(\brunner:\s*CsvRow\[\];\s*\n)(\s*runnerIntel:\s*CsvRow\[\];)',
        r'\1  sectionalSidecar: CsvRow[];\n\2',
        "LOADER_TYPE",
    )

    # Loader destructuring list: insert sectionalSidecar immediately after runner.
    path = FILES["loader"]
    text = read(path)
    if re.search(r'\brunner\s*,\s*sectionalSidecar\s*,\s*runnerIntel\b', text):
        print("LOADER_DESTRUCTURE=ALREADY_APPLIED")
    else:
        new_text, n = re.subn(r'\brunner\s*,\s*runnerIntel\b', 'runner, sectionalSidecar, runnerIntel', text, count=1)
        if n != 1:
            raise RuntimeError(f"V32.1 patch anchor not found: LOADER_DESTRUCTURE in {path}")
        write(path, new_text)
        print("LOADER_DESTRUCTURE=PATCHED")

    # Promise load.
    path = FILES["loader"]
    text = read(path)
    if 'loadCsv(FILES.sectionalSidecar)' in text:
        print("LOADER_PROMISE=ALREADY_APPLIED")
    else:
        m = re.search(r'(^\s*loadCsv\(FILES\.runnerBoard\),\s*$)', text, flags=re.M)
        if not m:
            raise RuntimeError(f"V32.1 patch anchor not found: LOADER_PROMISE in {path}")
        line = m.group(1)
        indent = re.match(r'\s*', line).group(0)
        new = line + f'\n{indent}loadCsv(FILES.sectionalSidecar),'
        write(path, text[:m.start()] + new + text[m.end():])
        print("LOADER_PROMISE=PATCHED")

    # Loader return list: second occurrence runner, runnerIntel.
    path = FILES["loader"]
    text = read(path)
    occurrences = list(re.finditer(r'\brunner\s*,\s*runnerIntel\b', text))
    if 'runner, sectionalSidecar, runnerIntel' in text and not occurrences:
        print("LOADER_RETURN=ALREADY_APPLIED")
    elif occurrences:
        m = occurrences[-1]
        new_text = text[:m.start()] + 'runner, sectionalSidecar, runnerIntel' + text[m.end():]
        write(path, new_text)
        print("LOADER_RETURN=PATCHED")
    else:
        print("LOADER_RETURN=ALREADY_APPLIED")

    # Enrichment param.
    replace_regex(
        FILES["enrichment"],
        r'(\braceRows:\s*Row\[\];\s*\n)(\s*formEnrichmentRows:\s*Row\[\];)',
        r'\1  sectionalRows: Row[];\n\2',
        "ENRICH_PARAM",
    )

    # Enrichment destructure.
    path = FILES["enrichment"]
    text = read(path)
    if re.search(r'\braceRows\s*,\s*sectionalRows\s*,\s*formEnrichmentRows\b', text):
        print("ENRICH_DESTRUCTURE=ALREADY_APPLIED")
    else:
        new_text, n = re.subn(r'\braceRows\s*,\s*formEnrichmentRows\b', 'raceRows,\n    sectionalRows,\n    formEnrichmentRows', text, count=1)
        if n != 1:
            raise RuntimeError(f"V32.1 patch anchor not found: ENRICH_DESTRUCTURE in {path}")
        write(path, new_text)
        print("ENRICH_DESTRUCTURE=PATCHED")

    # Enrichment lookup.
    path = FILES["enrichment"]
    text = read(path)
    if 'const sectionals = findSidecar(sectionalRows, row);' in text:
        print("ENRICH_LOOKUP=ALREADY_APPLIED")
    else:
        m = re.search(r'(^\s*const runnerIntel\s*=\s*findSidecar\(runnerIntelRows,\s*row\);\s*$)', text, flags=re.M)
        if not m:
            raise RuntimeError(f"V32.1 patch anchor not found: ENRICH_LOOKUP in {path}")
        indent = re.match(r'\s*', m.group(1)).group(0)
        new = f'{indent}const sectionals = findSidecar(sectionalRows, row);\n' + m.group(1)
        write(path, text[:m.start()] + new + text[m.end():])
        print("ENRICH_LOOKUP=PATCHED")

    # Enrichment return.
    path = FILES["enrichment"]
    text = read(path)
    if re.search(r'\brow\s*,\s*sectionals\s*,\s*runnerIntel\b', text):
        print("ENRICH_RETURN=ALREADY_APPLIED")
    else:
        new_text, n = re.subn(r'(return\s*\{\s*\n\s*row\s*,\s*\n)(\s*runnerIntel\s*,)', r'\1      sectionals,\n\2', text, count=1)
        if n != 1:
            raise RuntimeError(f"V32.1 patch anchor not found: ENRICH_RETURN in {path}")
        write(path, new_text)
        print("ENRICH_RETURN=PATCHED")

    # Metrics type.
    replace_regex(
        FILES["metrics"],
        r'(type\s+EnrichedRunnerLike\s*=\s*\{\s*\n\s*row:\s*Row;)',
        r'\1\n  sectionals?: Row;',
        "METRICS_TYPE",
    )

    # Screen EnrichedRunner type.
    replace_regex(
        FILES["screen"],
        r'(type\s+EnrichedRunner\s*=\s*\{\s*\n\s*row:\s*Row;)',
        r'\1\n sectionals?: Row;',
        "SCREEN_TYPE",
    )

    # Screen state.
    path = FILES["screen"]
    text = read(path)
    if 'const [sectionalRows, setSectionalRows] = useState<Row[]>([]);' in text:
        print("SCREEN_STATE=ALREADY_APPLIED")
    else:
        m = re.search(r'(^\s*const \[runnerRows, setRunnerRows\] = useState<Row\[\]>\(\[\]\);\s*$)', text, flags=re.M)
        if not m:
            raise RuntimeError(f"V32.1 patch anchor not found: SCREEN_STATE in {path}")
        indent = re.match(r'\s*', m.group(1)).group(0)
        new = m.group(1) + f'\n{indent}const [sectionalRows, setSectionalRows] = useState<Row[]>([]);'
        write(path, text[:m.start()] + new + text[m.end():])
        print("SCREEN_STATE=PATCHED")

    # Screen load.
    path = FILES["screen"]
    text = read(path)
    if 'setSectionalRows(data.sectionalSidecar);' in text:
        print("SCREEN_LOAD=ALREADY_APPLIED")
    else:
        m = re.search(r'(^\s*setRunnerRows\(data\.runner\);\s*$)', text, flags=re.M)
        if not m:
            raise RuntimeError(f"V32.1 patch anchor not found: SCREEN_LOAD in {path}")
        indent = re.match(r'\s*', m.group(1)).group(0)
        new = m.group(1) + f'\n{indent}setSectionalRows(data.sectionalSidecar);'
        write(path, text[:m.start()] + new + text[m.end():])
        print("SCREEN_LOAD=PATCHED")

    # Screen enrich arg.
    path = FILES["screen"]
    text = read(path)
    if re.search(r'buildEnrichedRunners\(\{[\s\S]{0,400}?\braceRows\s*,\s*sectionalRows\s*,', text):
        print("SCREEN_ENRICH_ARG=ALREADY_APPLIED")
    else:
        new_text, n = re.subn(r'(buildEnrichedRunners\(\{\s*\n\s*raceRows\s*,\s*\n)', r'\1  sectionalRows,\n', text, count=1)
        if n != 1:
            raise RuntimeError(f"V32.1 patch anchor not found: SCREEN_ENRICH_ARG in {path}")
        write(path, new_text)
        print("SCREEN_ENRICH_ARG=PATCHED")

    # Screen dependency.
    path = FILES["screen"]
    text = read(path)
    if re.search(r'\[raceRows,\s*sectionalRows,\s*runnerIntelRows', text):
        print("SCREEN_DEPENDENCY=ALREADY_APPLIED")
    else:
        new_text, n = re.subn(r'\[raceRows,\s*runnerIntelRows', '[raceRows, sectionalRows, runnerIntelRows', text, count=1)
        if n != 1:
            raise RuntimeError(f"V32.1 patch anchor not found: SCREEN_DEPENDENCY in {path}")
        write(path, new_text)
        print("SCREEN_DEPENDENCY=PATCHED")

    # Supplementary governed factors after existing Late Power row.
    path = FILES["screen"]
    text = read(path)
    if '{ label: "Gov Sect"' in text:
        print("SCREEN_GOVERNED_FACTORS=ALREADY_APPLIED")
    else:
        m = re.search(r'(^\s*\{\s*label:\s*"Late Power",[^\n]*\}\s*,\s*$)', text, flags=re.M)
        if not m:
            raise RuntimeError(f"V32.1 patch anchor not found: SCREEN_GOVERNED_FACTORS in {path}")
        indent = re.match(r'\s*', m.group(1)).group(0)
        extra = (
            f'\n{indent}{{ label: "Gov Sect", value: firstNum(selected.sectionals, ["sectional_weapon_score"]), max: 100, digits: 0, tone: "#a78bfa" }},'
            f'\n{indent}{{ label: "Gov Late", value: firstNum(selected.sectionals, ["sectional_late_power_score"]), max: 100, digits: 0, tone: "#ffffff" }},'
            f'\n{indent}{{ label: "Gov Early", value: firstNum(selected.sectionals, ["sectional_early_speed_score"]), max: 100, digits: 0, tone: "#60a5fa" }},'
        )
        new = m.group(1) + extra
        write(path, text[:m.start()] + new + text[m.end():])
        print("SCREEN_GOVERNED_FACTORS=PATCHED")

    print("V32.1 SECTIONAL UI WIRING")
    print("sectional_source=edgeiq_live_runner_board_sectionals_v31.csv")
    print("policy=SUPPLEMENTARY_ONLY")
    print("pricing_mutation=NO")
    print("decision_mutation=NO")
    print("FINAL STATUS: PATCH_APPLIED=YES")


if __name__ == "__main__":
    main()
