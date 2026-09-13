from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"


def patch_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"{label}=ALREADY_APPLIED")
        return text
    if old not in text:
        raise RuntimeError(f"V32.3 patch anchor not found: {label} in {SCREEN}")
    print(f"{label}=PATCHED")
    return text.replace(old, new, 1)


def main() -> None:
    if not SCREEN.exists():
        raise FileNotFoundError(SCREEN)

    text = SCREEN.read_text(encoding="utf-8-sig")

    required = [
        "sectionals?: Row;",
        "const [sectionalRows, setSectionalRows] = useState<Row[]>([]);",
        "setSectionalRows(data.sectionalSidecar);",
        'label: "Gov Sect"',
        'label: "Gov Late"',
        'label: "Gov Early"',
    ]
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeError("V32.3 requires successful V32.2 first; missing: " + ", ".join(missing))

    bak = SCREEN.with_suffix(SCREEN.suffix + ".v32_3.bak")
    if not bak.exists():
        shutil.copy2(SCREEN, bak)

    old_vars = ''' const selectedConnectionScore = selected ? connectionScoreValue(selected) : null;\n const selectedRunnerFactors = selected\n'''
    new_vars = ''' const selectedConnectionScore = selected ? connectionScoreValue(selected) : null;\n const selectedGovSectionalHistoryRuns = selected ? firstNum(selected.sectionals, ["sectional_history_runs"]) : null;\n const selectedGovSectionalHistoryStatus = !selected\n ? ""\n : (selectedGovSectionalHistoryRuns ?? 0) <= 0\n ? "NO SECTIONAL HISTORY"\n : selectedGovSectionalHistoryRuns === 1\n ? "LIMITED HISTORY · 1 PRIOR RUN"\n : `${Math.trunc(selectedGovSectionalHistoryRuns ?? 0)} PRIOR RUNS`;\n const selectedGovConsistency = selected ? firstNum(selected.sectionals, ["sectional_consistency_score"]) : null;\n const selectedGovTrajectory = selected ? firstNum(selected.sectionals, ["sectional_trajectory_score"]) : null;\n const selectedRunnerFactors = selected\n'''
    text = patch_once(text, old_vars, new_vars, "SCREEN_GOVERNED_HISTORY_STATE")

    old_factors = ''' { label: "Gov Sect", value: firstNum(selected.sectionals, ["sectional_weapon_score"]), max: 100, digits: 0, tone: "#a78bfa" },\n { label: "Gov Late", value: firstNum(selected.sectionals, ["sectional_late_power_score"]), max: 100, digits: 0, tone: "#ffffff" },\n { label: "Gov Early", value: firstNum(selected.sectionals, ["sectional_early_speed_score"]), max: 100, digits: 0, tone: "#60a5fa" },\n'''
    new_factors = ''' { label: `Gov History · ${selectedGovSectionalHistoryStatus}`, value: (selectedGovSectionalHistoryRuns ?? 0) > 0 ? selectedGovSectionalHistoryRuns : null, max: 3, digits: 0, tone: (selectedGovSectionalHistoryRuns ?? 0) > 0 ? "#fbbf24" : "#64748b" },\n { label: "Gov Sect", value: (selectedGovSectionalHistoryRuns ?? 0) > 0 ? firstNum(selected.sectionals, ["sectional_weapon_score"]) : null, max: 100, digits: 0, tone: "#a78bfa" },\n { label: "Gov Late", value: (selectedGovSectionalHistoryRuns ?? 0) > 0 ? firstNum(selected.sectionals, ["sectional_late_power_score"]) : null, max: 100, digits: 0, tone: "#ffffff" },\n { label: "Gov Early", value: (selectedGovSectionalHistoryRuns ?? 0) > 0 ? firstNum(selected.sectionals, ["sectional_early_speed_score"]) : null, max: 100, digits: 0, tone: "#60a5fa" },\n { label: selectedGovConsistency === null ? "Gov Consistency · LIMITED DATA" : "Gov Consistency", value: selectedGovConsistency, max: 100, digits: 0, tone: selectedGovConsistency === null ? "#64748b" : "#c4b5fd" },\n { label: selectedGovTrajectory === null ? "Gov Trajectory · LIMITED DATA" : "Gov Trajectory", value: selectedGovTrajectory, max: 100, digits: 0, tone: selectedGovTrajectory === null ? "#64748b" : "#93c5fd" },\n'''
    text = patch_once(text, old_factors, new_factors, "SCREEN_GOVERNED_FACTOR_POLISH")

    SCREEN.write_text(text, encoding="utf-8")

    checks = {
        "VERIFY_NO_HISTORY_LABEL": "NO SECTIONAL HISTORY" in text,
        "VERIFY_LIMITED_HISTORY_LABEL": "LIMITED HISTORY · 1 PRIOR RUN" in text,
        "VERIFY_CONSISTENCY_LIMITED": "Gov Consistency · LIMITED DATA" in text,
        "VERIFY_TRAJECTORY_LIMITED": "Gov Trajectory · LIMITED DATA" in text,
        "VERIFY_HISTORY_GATING": '(selectedGovSectionalHistoryRuns ?? 0) > 0 ? firstNum(selected.sectionals, ["sectional_weapon_score"]) : null' in text,
    }
    for label, ok in checks.items():
        print(f"{label}={'PASS' if ok else 'FAIL'}")
    if not all(checks.values()):
        raise RuntimeError("V32.3 verification failed")

    print()
    print("V32.3 GOVERNED SECTIONAL UI POLISH")
    print("no_history_display=NO_SECTIONAL_HISTORY")
    print("one_prior_run_display=LIMITED_HISTORY_1_PRIOR_RUN")
    print("consistency_without_support=LIMITED_DATA")
    print("trajectory_without_support=LIMITED_DATA")
    print("zero_imputation=NO")
    print("pricing_mutation=NO")
    print("decision_mutation=NO")
    print("FINAL STATUS: PATCH_APPLIED=YES")


if __name__ == "__main__":
    main()
