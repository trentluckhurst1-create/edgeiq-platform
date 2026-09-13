from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
PERFORMANCE = ROOT / "src" / "components" / "workspaces" / "RacePerformanceWorkspace.tsx"


def patch_once(text: str, old: str, new: str, label: str, path: Path) -> str:
    if new in text:
        print(f"{label}=ALREADY_APPLIED")
        return text
    if old not in text:
        raise RuntimeError(f"V33 patch anchor not found: {label} in {path}")
    print(f"{label}=PATCHED")
    return text.replace(old, new, 1)


def backup(path: Path, suffix: str) -> None:
    bak = path.with_suffix(path.suffix + suffix)
    if not bak.exists():
        shutil.copy2(path, bak)


def main() -> None:
    for path in (SCREEN, PERFORMANCE):
        if not path.exists():
            raise FileNotFoundError(path)

    screen = SCREEN.read_text(encoding="utf-8-sig")
    perf = PERFORMANCE.read_text(encoding="utf-8-sig")

    # V31/V32 wiring must remain present. V33 only relocates presentation.
    required_screen = [
        "sectionals?: Row;",
        "const [sectionalRows, setSectionalRows] = useState<Row[]>([]);",
        "setSectionalRows(data.sectionalSidecar);",
    ]
    missing = [token for token in required_screen if token not in screen]
    if missing:
        raise RuntimeError("V33 requires V32 sidecar wiring first; missing: " + ", ".join(missing))

    required_perf = [
        "export function RacePerformanceWorkspace",
        "const performanceSpread =",
        '<div className="edgeiq-performance-summary-grid">',
        '<div className="edgeiq-performance-index-panel edgeiq-product-v4-panel">',
    ]
    missing_perf = [token for token in required_perf if token not in perf]
    if missing_perf:
        raise RuntimeError("V33 Performance workspace anchors missing: " + ", ".join(missing_perf))

    backup(SCREEN, ".v33.bak")
    backup(PERFORMANCE, ".v33.bak")

    # Remove the V32.3 generic selected-runner governed presentation. Keep the sidecar itself.
    v32_vars = ''' const selectedConnectionScore = selected ? connectionScoreValue(selected) : null;\n const selectedGovSectionalHistoryRuns = selected ? firstNum(selected.sectionals, ["sectional_history_runs"]) : null;\n const selectedGovSectionalHistoryStatus = !selected\n ? ""\n : (selectedGovSectionalHistoryRuns ?? 0) <= 0\n ? "NO SECTIONAL HISTORY"\n : selectedGovSectionalHistoryRuns === 1\n ? "LIMITED HISTORY · 1 PRIOR RUN"\n : `${Math.trunc(selectedGovSectionalHistoryRuns ?? 0)} PRIOR RUNS`;\n const selectedGovConsistency = selected ? firstNum(selected.sectionals, ["sectional_consistency_score"]) : null;\n const selectedGovTrajectory = selected ? firstNum(selected.sectionals, ["sectional_trajectory_score"]) : null;\n const selectedRunnerFactors = selected\n'''
    base_vars = ''' const selectedConnectionScore = selected ? connectionScoreValue(selected) : null;\n const selectedRunnerFactors = selected\n'''
    if v32_vars in screen:
        screen = screen.replace(v32_vars, base_vars, 1)
        print("SCREEN_REMOVE_GENERIC_GOV_STATE=PATCHED")
    elif "selectedGovSectionalHistoryRuns" not in screen:
        print("SCREEN_REMOVE_GENERIC_GOV_STATE=ALREADY_APPLIED")
    else:
        raise RuntimeError("V33 could not safely remove V32.3 governed state block")

    v32_factors = ''' { label: `Gov History · ${selectedGovSectionalHistoryStatus}`, value: (selectedGovSectionalHistoryRuns ?? 0) > 0 ? selectedGovSectionalHistoryRuns : null, max: 3, digits: 0, tone: (selectedGovSectionalHistoryRuns ?? 0) > 0 ? "#fbbf24" : "#64748b" },\n { label: "Gov Sect", value: (selectedGovSectionalHistoryRuns ?? 0) > 0 ? firstNum(selected.sectionals, ["sectional_weapon_score"]) : null, max: 100, digits: 0, tone: "#a78bfa" },\n { label: "Gov Late", value: (selectedGovSectionalHistoryRuns ?? 0) > 0 ? firstNum(selected.sectionals, ["sectional_late_power_score"]) : null, max: 100, digits: 0, tone: "#ffffff" },\n { label: "Gov Early", value: (selectedGovSectionalHistoryRuns ?? 0) > 0 ? firstNum(selected.sectionals, ["sectional_early_speed_score"]) : null, max: 100, digits: 0, tone: "#60a5fa" },\n { label: selectedGovConsistency === null ? "Gov Consistency · LIMITED DATA" : "Gov Consistency", value: selectedGovConsistency, max: 100, digits: 0, tone: selectedGovConsistency === null ? "#64748b" : "#c4b5fd" },\n { label: selectedGovTrajectory === null ? "Gov Trajectory · LIMITED DATA" : "Gov Trajectory", value: selectedGovTrajectory, max: 100, digits: 0, tone: selectedGovTrajectory === null ? "#64748b" : "#93c5fd" },\n'''
    if v32_factors in screen:
        screen = screen.replace(v32_factors, "", 1)
        print("SCREEN_REMOVE_GENERIC_GOV_FACTORS=PATCHED")
    elif 'label: "Gov Sect"' not in screen and "Gov History ·" not in screen:
        print("SCREEN_REMOVE_GENERIC_GOV_FACTORS=ALREADY_APPLIED")
    else:
        raise RuntimeError("V33 could not safely remove V32.3 generic governed factor block")

    old_calc = '''  const performanceSpread = runnerPerformance.length ? Math.max(...runnerPerformance) - Math.min(...runnerPerformance) : null;\n\n  const topFigureEntry = heatRows.reduce<{ item: EnrichedRunnerLike; value: number } | null>((best, entry) => {\n'''
    new_calc = '''  const performanceSpread = runnerPerformance.length ? Math.max(...runnerPerformance) - Math.min(...runnerPerformance) : null;\n\n  const governedSectionalRows = activeRaceRows.map((item) => {\n    const sectionals = (item.sectionals || {}) as Row;\n    const runs = firstNum(sectionals, ["sectional_history_runs"]) ?? 0;\n    const hasHistory = runs > 0;\n    const historyLabel = !hasHistory\n      ? "NO SECTIONAL HISTORY"\n      : runs === 1\n      ? "LIMITED HISTORY · 1 PRIOR RUN"\n      : `${Math.trunc(runs)} PRIOR RUNS`;\n    return {\n      item,\n      sectionals,\n      runs,\n      hasHistory,\n      historyLabel,\n      weapon: hasHistory ? firstNum(sectionals, ["sectional_weapon_score"]) : null,\n      weaponBand: hasHistory ? firstText(sectionals, ["sectional_weapon_band"], "") : "",\n      late: hasHistory ? firstNum(sectionals, ["sectional_late_power_score"]) : null,\n      lateBand: hasHistory ? firstText(sectionals, ["sectional_late_power_band"], "") : "",\n      early: hasHistory ? firstNum(sectionals, ["sectional_early_speed_score"]) : null,\n      earlyBand: hasHistory ? firstText(sectionals, ["sectional_early_speed_band"], "") : "",\n      consistency: hasHistory ? firstNum(sectionals, ["sectional_consistency_score"]) : null,\n      consistencyBand: hasHistory ? firstText(sectionals, ["sectional_consistency_band"], "") : "",\n      trajectory: hasHistory ? firstNum(sectionals, ["sectional_trajectory_score"]) : null,\n      trajectoryBand: hasHistory ? firstText(sectionals, ["sectional_trajectory_band"], "") : "",\n    };\n  });\n  const governedSectionalMatched = governedSectionalRows.filter((entry) => entry.hasHistory).length;\n  const governedScoreText = (value: number | null, band: string) => {\n    if (value === null || !Number.isFinite(value)) return "LIMITED DATA";\n    return `${renderMetricValue(value, 0)}${band ? ` · ${band}` : ""}`;\n  };\n\n  const topFigureEntry = heatRows.reduce<{ item: EnrichedRunnerLike; value: number } | null>((best, entry) => {\n'''
    perf = patch_once(perf, old_calc, new_calc, "PERFORMANCE_GOVERNED_SECTIONAL_MODEL", PERFORMANCE)

    old_jsx = '''      </div>\n\n      <div className="edgeiq-performance-index-panel edgeiq-product-v4-panel">\n'''
    new_jsx = '''      </div>\n\n      <div className="edgeiq-performance-index-panel edgeiq-product-v4-panel" style={{ display: "grid", gap: 10 }}>\n        <div className="edgeiq-performance-panel-head" style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>\n          <strong>GOVERNED SECTIONAL HISTORY</strong>\n          <span style={{ color: "#7f8ea3", fontSize: 10, fontWeight: 800, letterSpacing: ".06em" }}>\n            SUPPLEMENTARY EVIDENCE · NO PRICING IMPACT · {governedSectionalMatched}/{governedSectionalRows.length} RUNNERS COVERED\n          </span>\n        </div>\n\n        {governedSectionalMatched === 0 ? (\n          <div className="edgeiq-product-empty">NO SECTIONAL HISTORY FOR THIS FIELD</div>\n        ) : (\n          <div style={{ display: "grid", gap: 5, overflowX: "auto" }}>\n            <div style={{ display: "grid", gridTemplateColumns: "42px minmax(170px,1.4fr) minmax(180px,1.5fr) repeat(5,minmax(105px,1fr))", gap: 8, minWidth: 980, color: "#7f8ea3", fontSize: 9.5, fontWeight: 900, letterSpacing: ".07em", textTransform: "uppercase", padding: "0 8px 5px", borderBottom: "1px solid rgba(51,65,85,.65)" }}>\n              {["NO", "HORSE", "HISTORY", "WEAPON", "LATE", "EARLY", "CONSISTENCY", "TRAJECTORY"].map((label) => <span key={`gov-section-head-${label}`}>{label}</span>)}\n            </div>\n            {governedSectionalRows.map((entry) => (\n              <div\n                key={`gov-section-${runnerRowKey(entry.item.row)}`}\n                style={{\n                  display: "grid",\n                  gridTemplateColumns: "42px minmax(170px,1.4fr) minmax(180px,1.5fr) repeat(5,minmax(105px,1fr))",\n                  gap: 8,\n                  minWidth: 980,\n                  alignItems: "center",\n                  padding: "8px",\n                  borderRadius: 8,\n                  border: "1px solid rgba(51,65,85,.45)",\n                  background: entry.hasHistory ? "rgba(10,25,32,.72)" : "rgba(4,10,18,.42)",\n                  opacity: entry.hasHistory ? 1 : 0.62,\n                  fontSize: 10.5,\n                }}\n              >\n                <span>{saddle(entry.item.row) === 999 ? empty : saddle(entry.item.row)}</span>\n                <strong style={{ color: "#f4f8f8" }}>{horse(entry.item.row)}</strong>\n                <span style={{ color: entry.hasHistory ? "#fbbf24" : "#64748b", fontWeight: 850 }}>{entry.historyLabel}</span>\n                <span>{entry.hasHistory ? governedScoreText(entry.weapon, entry.weaponBand) : "-"}</span>\n                <span>{entry.hasHistory ? governedScoreText(entry.late, entry.lateBand) : "-"}</span>\n                <span>{entry.hasHistory ? governedScoreText(entry.early, entry.earlyBand) : "-"}</span>\n                <span>{entry.hasHistory ? governedScoreText(entry.consistency, entry.consistencyBand) : "-"}</span>\n                <span>{entry.hasHistory ? governedScoreText(entry.trajectory, entry.trajectoryBand) : "-"}</span>\n              </div>\n            ))}\n          </div>\n        )}\n      </div>\n\n      <div className="edgeiq-performance-index-panel edgeiq-product-v4-panel">\n'''
    perf = patch_once(perf, old_jsx, new_jsx, "PERFORMANCE_GOVERNED_SECTIONAL_PANEL", PERFORMANCE)

    SCREEN.write_text(screen, encoding="utf-8")
    PERFORMANCE.write_text(perf, encoding="utf-8")

    checks = {
        "VERIFY_SIDECAR_PRESERVED": "sectionals?: Row;" in screen and "sectionalRows" in screen,
        "VERIFY_GENERIC_GOV_REMOVED": 'label: "Gov Sect"' not in screen and "Gov History ·" not in screen,
        "VERIFY_PERFORMANCE_PANEL": "GOVERNED SECTIONAL HISTORY" in perf,
        "VERIFY_NO_HISTORY": "NO SECTIONAL HISTORY FOR THIS FIELD" in perf and "NO SECTIONAL HISTORY" in perf,
        "VERIFY_LIMITED_HISTORY": "LIMITED HISTORY · 1 PRIOR RUN" in perf,
        "VERIFY_LIMITED_DATA": "LIMITED DATA" in perf,
        "VERIFY_NO_ZERO_IMPUTATION": 'return "LIMITED DATA"' in perf,
        "VERIFY_PRICING_POLICY": "NO PRICING IMPACT" in perf,
    }
    for label, ok in checks.items():
        print(f"{label}={'PASS' if ok else 'FAIL'}")
    if not all(checks.values()):
        raise RuntimeError("V33 verification failed")

    print()
    print("V33 GOVERNED SECTIONALS -> PERFORMANCE")
    print("presentation_target=PERFORMANCE")
    print("generic_runner_factor_surface=REMOVED")
    print("sidecar_wiring=PRESERVED")
    print("no_history_display=NO_SECTIONAL_HISTORY")
    print("one_prior_run_display=LIMITED_HISTORY_1_PRIOR_RUN")
    print("missing_metric_display=LIMITED_DATA")
    print("zero_imputation=NO")
    print("pricing_mutation=NO")
    print("decision_mutation=NO")
    print("FINAL STATUS: PATCH_APPLIED=YES")


if __name__ == "__main__":
    main()
