from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

TARGETS = {
    "config": ROOT / "src" / "config" / "edgeiqFiles.ts",
    "loader": ROOT / "src" / "services" / "edgeiqDataLoader.ts",
    "enrichment": ROOT / "src" / "services" / "runnerEnrichmentService.ts",
    "screen": ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx",
}


def backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".v32_2.bak")
    if not bak.exists():
        shutil.copy2(path, bak)


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    if new in text:
        print(f"{label}=ALREADY_APPLIED")
        return
    if old not in text:
        raise RuntimeError(f"V32.2 exact local anchor not found: {label} in {path}")
    backup(path)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"{label}=PATCHED")


def main() -> None:
    missing = [str(p) for p in TARGETS.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing V32.2 targets: " + ", ".join(missing))

    # ------------------------------------------------------------------
    # edgeiqFiles.ts — exact active-local structure uses edgeiqDataPath().
    # ------------------------------------------------------------------
    replace_once(
        TARGETS["config"],
        '  runnerBoard: edgeiqDataPath("/data/edgeiq_live_runner_board_governed_v1.csv"),\n',
        '  runnerBoard: edgeiqDataPath("/data/edgeiq_live_runner_board_governed_v1.csv"),\n'
        '  sectionalSidecar: edgeiqDataPath("/data/edgeiq_live_runner_board_sectionals_v31.csv"),\n',
        "CONFIG_SECTIONAL_SIDECAR",
    )

    # ------------------------------------------------------------------
    # edgeiqDataLoader.ts — load the V31 board as a separate sidecar.
    # ------------------------------------------------------------------
    replace_once(
        TARGETS["loader"],
        '  runner: CsvRow[];\n  runnerIntel: CsvRow[];\n',
        '  runner: CsvRow[];\n  sectionalSidecar: CsvRow[];\n  runnerIntel: CsvRow[];\n',
        "LOADER_TYPE",
    )
    replace_once(
        TARGETS["loader"],
        '    runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel,\n',
        '    runner, sectionalSidecar, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel,\n',
        "LOADER_DESTRUCTURE",
    )
    replace_once(
        TARGETS["loader"],
        '    loadCsv(FILES.runnerBoard),\n    loadCsv(FILES.runnerIntel),\n',
        '    loadCsv(FILES.runnerBoard),\n    loadCsv(FILES.sectionalSidecar),\n    loadCsv(FILES.runnerIntel),\n',
        "LOADER_PROMISE",
    )
    # After the destructuring replacement above, this exact old string still
    # occurs once in the return block.
    replace_once(
        TARGETS["loader"],
        '    runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel,\n',
        '    runner, sectionalSidecar, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel,\n',
        "LOADER_RETURN",
    )

    # ------------------------------------------------------------------
    # runnerEnrichmentService.ts — attach one V31 sidecar row to each live
    # runner using the repository's existing governed sidecar lookup logic.
    # ------------------------------------------------------------------
    replace_once(
        TARGETS["enrichment"],
        '  raceRows: Row[];\n  formEnrichmentRows: Row[];\n',
        '  raceRows: Row[];\n  sectionalRows: Row[];\n  formEnrichmentRows: Row[];\n',
        "ENRICH_PARAM",
    )
    replace_once(
        TARGETS["enrichment"],
        '    raceRows,\n    formEnrichmentRows,\n',
        '    raceRows,\n    sectionalRows,\n    formEnrichmentRows,\n',
        "ENRICH_DESTRUCTURE",
    )
    replace_once(
        TARGETS["enrichment"],
        '  return raceRows.map((row) => {\n    const runnerIntel = findSidecar(runnerIntelRows, row);\n',
        '  return raceRows.map((row) => {\n    const sectionals = findSidecar(sectionalRows, row);\n    const runnerIntel = findSidecar(runnerIntelRows, row);\n',
        "ENRICH_LOOKUP",
    )
    replace_once(
        TARGETS["enrichment"],
        '    return {\n      row,\n      runnerIntel,\n',
        '    return {\n      row,\n      sectionals,\n      runnerIntel,\n',
        "ENRICH_RETURN",
    )

    # ------------------------------------------------------------------
    # RaceIntelligenceScreen.tsx — keep V31 evidence separate from the base
    # runner board. It is display-only supplementary evidence.
    # ------------------------------------------------------------------
    replace_once(
        TARGETS["screen"],
        'type EnrichedRunner = {\n row: Row;\n runnerIntel?: Row;\n',
        'type EnrichedRunner = {\n row: Row;\n sectionals?: Row;\n runnerIntel?: Row;\n',
        "SCREEN_TYPE",
    )
    replace_once(
        TARGETS["screen"],
        ' const [runnerRows, setRunnerRows] = useState<Row[]>([]);\n const [runnerIntelRows, setRunnerIntelRows] = useState<Row[]>([]);\n',
        ' const [runnerRows, setRunnerRows] = useState<Row[]>([]);\n const [sectionalRows, setSectionalRows] = useState<Row[]>([]);\n const [runnerIntelRows, setRunnerIntelRows] = useState<Row[]>([]);\n',
        "SCREEN_STATE",
    )
    replace_once(
        TARGETS["screen"],
        ' setRunnerRows(data.runner);\n setRunnerIntelRows(data.runnerIntel);\n',
        ' setRunnerRows(data.runner);\n setSectionalRows(data.sectionalSidecar);\n setRunnerIntelRows(data.runnerIntel);\n',
        "SCREEN_LOAD",
    )
    replace_once(
        TARGETS["screen"],
        ' const enriched = useMemo(() => buildEnrichedRunners({\n  raceRows,\n  formEnrichmentRows,\n',
        ' const enriched = useMemo(() => buildEnrichedRunners({\n  raceRows,\n  sectionalRows,\n  formEnrichmentRows,\n',
        "SCREEN_ENRICH_ARG",
    )
    replace_once(
        TARGETS["screen"],
        ' }), [raceRows, runnerIntelRows, v8Rows, betRows, reliabilityRows,',
        ' }), [raceRows, sectionalRows, runnerIntelRows, v8Rows, betRows, reliabilityRows,',
        "SCREEN_DEPENDENCY",
    )
    replace_once(
        TARGETS["screen"],
        ' { label: "Late Power", value: latePowerMetricValue(selected), max: 100, digits: 0, tone: "#ffffff" },\n',
        ' { label: "Late Power", value: latePowerMetricValue(selected), max: 100, digits: 0, tone: "#ffffff" },\n'
        ' { label: "Gov Sect", value: firstNum(selected.sectionals, ["sectional_weapon_score"]), max: 100, digits: 0, tone: "#a78bfa" },\n'
        ' { label: "Gov Late", value: firstNum(selected.sectionals, ["sectional_late_power_score"]), max: 100, digits: 0, tone: "#ffffff" },\n'
        ' { label: "Gov Early", value: firstNum(selected.sectionals, ["sectional_early_speed_score"]), max: 100, digits: 0, tone: "#60a5fa" },\n',
        "SCREEN_GOVERNED_FACTORS",
    )

    # Final structural verification before declaring success.
    checks = {
        "config": 'sectionalSidecar: edgeiqDataPath("/data/edgeiq_live_runner_board_sectionals_v31.csv")',
        "loader": "sectionalSidecar: CsvRow[];",
        "enrichment": "const sectionals = findSidecar(sectionalRows, row);",
        "screen_state": "const [sectionalRows, setSectionalRows] = useState<Row[]>([]);",
        "screen_factor": 'label: "Gov Sect"',
    }
    source_by_name = {name: path.read_text(encoding="utf-8-sig") for name, path in TARGETS.items()}
    verify_map = {
        "config": ("config", checks["config"]),
        "loader": ("loader", checks["loader"]),
        "enrichment": ("enrichment", checks["enrichment"]),
        "screen_state": ("screen", checks["screen_state"]),
        "screen_factor": ("screen", checks["screen_factor"]),
    }
    failed = []
    for label, (target_name, needle) in verify_map.items():
        ok = needle in source_by_name[target_name]
        print(f"VERIFY_{label.upper()}={'PASS' if ok else 'FAIL'}")
        if not ok:
            failed.append(label)
    if failed:
        raise RuntimeError("V32.2 verification failed: " + ", ".join(failed))

    print()
    print("V32.2 SECTIONAL INTELLIGENCE UI WIRING")
    print("sectional_source=edgeiq_live_runner_board_sectionals_v31.csv")
    print("join=EXISTING_GOVERNED_SIDECAR_LOOKUP")
    print("policy=SUPPLEMENTARY_ONLY")
    print("pricing_mutation=NO")
    print("decision_mutation=NO")
    print("base_runner_board_replaced=NO")
    print("FINAL STATUS: PATCH_APPLIED=YES")


if __name__ == "__main__":
    main()
