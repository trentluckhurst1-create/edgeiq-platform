from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "config": ROOT / "src" / "config" / "edgeiqFiles.ts",
    "loader": ROOT / "src" / "services" / "edgeiqDataLoader.ts",
    "enrichment": ROOT / "src" / "services" / "runnerEnrichmentService.ts",
    "metrics": ROOT / "src" / "services" / "runnerMetricsService.ts",
    "screen": ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx",
}


def patch_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    if new in text:
        print(f"{label}=ALREADY_APPLIED")
        return
    if old not in text:
        raise RuntimeError(f"V32 patch anchor not found: {label} in {path}")
    bak = path.with_suffix(path.suffix + ".v32.bak")
    if not bak.exists():
        shutil.copy2(path, bak)
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"{label}=PATCHED")


def main() -> None:
    missing = [str(p) for p in FILES.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing V32 target files: " + ", ".join(missing))

    patch_once(
        FILES["config"],
        '  runnerBoard: "/data/edgeiq_live_runner_board_governed_v1.csv",\n',
        '  runnerBoard: "/data/edgeiq_live_runner_board_governed_v1.csv",\n  sectionalSidecar: "/data/edgeiq_live_runner_board_sectionals_v31.csv",\n',
        "CONFIG_SECTIONAL_SIDECAR",
    )

    patch_once(
        FILES["loader"],
        '  runner: CsvRow[];\n  runnerIntel: CsvRow[];\n',
        '  runner: CsvRow[];\n  sectionalSidecar: CsvRow[];\n  runnerIntel: CsvRow[];\n',
        "LOADER_TYPE",
    )
    patch_once(
        FILES["loader"],
        '    runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel,\n',
        '    runner, sectionalSidecar, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel,\n',
        "LOADER_DESTRUCTURE",
    )
    patch_once(
        FILES["loader"],
        '    loadCsv(FILES.runnerBoard),\n    loadCsv(FILES.runnerIntel),\n',
        '    loadCsv(FILES.runnerBoard),\n    loadCsv(FILES.sectionalSidecar),\n    loadCsv(FILES.runnerIntel),\n',
        "LOADER_PROMISE",
    )
    patch_once(
        FILES["loader"],
        '    runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel,\n',
        '    runner, sectionalSidecar, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel,\n',
        "LOADER_RETURN",
    )

    patch_once(
        FILES["enrichment"],
        '  raceRows: Row[];\n  formEnrichmentRows: Row[];\n',
        '  raceRows: Row[];\n  sectionalRows: Row[];\n  formEnrichmentRows: Row[];\n',
        "ENRICH_PARAM",
    )
    patch_once(
        FILES["enrichment"],
        '    raceRows,\n    formEnrichmentRows,\n',
        '    raceRows,\n    sectionalRows,\n    formEnrichmentRows,\n',
        "ENRICH_DESTRUCTURE",
    )
    patch_once(
        FILES["enrichment"],
        '    const runnerIntel = findSidecar(runnerIntelRows, row);\n',
        '    const sectionals = findSidecar(sectionalRows, row);\n    const runnerIntel = findSidecar(runnerIntelRows, row);\n',
        "ENRICH_LOOKUP",
    )
    patch_once(
        FILES["enrichment"],
        '      row,\n      runnerIntel,\n',
        '      row,\n      sectionals,\n      runnerIntel,\n',
        "ENRICH_RETURN",
    )

    patch_once(
        FILES["metrics"],
        'type EnrichedRunnerLike = {\n  row: Row;\n',
        'type EnrichedRunnerLike = {\n  row: Row;\n  sectionals?: Row;\n',
        "METRICS_TYPE",
    )

    patch_once(
        FILES["screen"],
        'type EnrichedRunner = {\n row: Row;\n',
        'type EnrichedRunner = {\n row: Row;\n sectionals?: Row;\n',
        "SCREEN_TYPE",
    )
    patch_once(
        FILES["screen"],
        ' const [runnerRows, setRunnerRows] = useState<Row[]>([]);\n const [runnerIntelRows, setRunnerIntelRows] = useState<Row[]>([]);\n',
        ' const [runnerRows, setRunnerRows] = useState<Row[]>([]);\n const [sectionalRows, setSectionalRows] = useState<Row[]>([]);\n const [runnerIntelRows, setRunnerIntelRows] = useState<Row[]>([]);\n',
        "SCREEN_STATE",
    )
    patch_once(
        FILES["screen"],
        ' setRunnerRows(data.runner);\n setRunnerIntelRows(data.runnerIntel);\n',
        ' setRunnerRows(data.runner);\n setSectionalRows(data.sectionalSidecar);\n setRunnerIntelRows(data.runnerIntel);\n',
        "SCREEN_LOAD",
    )
    patch_once(
        FILES["screen"],
        ' const enriched = useMemo(() => buildEnrichedRunners({\n  raceRows,\n  formEnrichmentRows,\n',
        ' const enriched = useMemo(() => buildEnrichedRunners({\n  raceRows,\n  sectionalRows,\n  formEnrichmentRows,\n',
        "SCREEN_ENRICH_ARG",
    )
    patch_once(
        FILES["screen"],
        ' }), [raceRows, runnerIntelRows, v8Rows, betRows, reliabilityRows,',
        ' }), [raceRows, sectionalRows, runnerIntelRows, v8Rows, betRows, reliabilityRows,',
        "SCREEN_DEPENDENCY",
    )

    # Add governed V31 evidence as separate supplementary factors in the selected-runner panel.
    patch_once(
        FILES["screen"],
        ' { label: "Late Power", value: latePowerMetricValue(selected), max: 100, digits: 0, tone: "#ffffff" },\n',
        ' { label: "Late Power", value: latePowerMetricValue(selected), max: 100, digits: 0, tone: "#ffffff" },\n { label: "Gov Sect", value: firstNum(selected.sectionals, ["sectional_weapon_score"]), max: 100, digits: 0, tone: "#a78bfa" },\n { label: "Gov Late", value: firstNum(selected.sectionals, ["sectional_late_power_score"]), max: 100, digits: 0, tone: "#ffffff" },\n { label: "Gov Early", value: firstNum(selected.sectionals, ["sectional_early_speed_score"]), max: 100, digits: 0, tone: "#60a5fa" },\n',
        "SCREEN_GOVERNED_FACTORS",
    )

    print("V32 SECTIONAL UI WIRING")
    print("sectional_source=edgeiq_live_runner_board_sectionals_v31.csv")
    print("policy=SUPPLEMENTARY_ONLY")
    print("pricing_mutation=NO")
    print("decision_mutation=NO")
    print("FINAL STATUS: PATCH_APPLIED=YES")


if __name__ == "__main__":
    main()
