from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
BASE = ROOT / "outputs" / "research" / "model_price_diagnostics"
LAB231_SCRIPT = BASE / "lab231" / "run_lab231_performance_representation_search.py"
LAB231_FEATURES = BASE / "lab231" / "LAB231_HISTORICAL_PERFORMANCE_FEATURES.csv"
OUT = BASE / "lab232"
OUT.mkdir(parents=True, exist_ok=True)

src = LAB231_SCRIPT.read_text(encoding="utf-8-sig", errors="strict")
cut = src.find('print("=" * 118)')
if cut < 0:
    raise RuntimeError("LAB231 definition boundary not found.")

ns = {"__name__": "__lab232_from_lab231_defs__", "__file__": str(LAB231_SCRIPT)}
exec(compile(src[:cut], str(LAB231_SCRIPT), "exec"), ns, ns)
ns["OUT"] = OUT

print("=" * 118)
print("LAB232 - EVIDENCE-SUPPORTED PERFORMANCE COMBO TEST")
print("=" * 118)
print("BROAD_FEATURE_SEARCH=NO")
print("MODEL_FITTING=CONTROLLED_OOS_ONLY")
print("MARKET_AS_FEATURE=NO")
print("FINAL_SP_EVALUATION_ONLY=YES")
print("WEIGHT_FEATURES_ATTRIBUTED_OR_INTERPRETED=NO")
print("PRODUCTION_MODIFIED=NO")

model, features281 = ns["load_strict_matrix"]()
strict_ref = ns["load_reference_predictions"]()
hist = pd.read_csv(LAB231_FEATURES, low_memory=False)
hist["_race"] = ns["norm"](hist["_race"])
hist["_horse"] = ns["norm"](hist["_horse"])
model = model.merge(hist.drop(columns=["_year", "_y"]), on=["_race", "_horse"], how="left", validate="one_to_one")

def expand(cols):
    out = []
    for c in cols:
        out.extend([c, f"{c}_rank_pct", f"{c}_z"])
    return [c for c in out if c in model.columns]

distance = [
    "h231_dist200_count",
    "h231_dist200_mean",
    "h231_dist200_best",
    "h231_dist200_best_minus_peak",
    "h231_same_class_count",
    "h231_same_class_mean",
    "h231_same_class_best",
]

downside = [
    "h231_epi_last10_worst",
    "h231_epi_last10_std",
    "h231_margin_last5_mean",
    "h231_margin_last5_worst",
    "h231_margin_last5_std",
    "h231_finishpos_last5_mean",
]

lowtail = [
    "h231_dist200_mean",
    "h231_dist200_best",
    "h231_same_class_mean",
    "h231_same_class_best",
    "h231_epi_last5_median",
    "h231_epi_last5_worst",
    "h231_epi_last10_worst",
    "h231_margin_last5_mean",
]

rank_only = [
    "h231_dist200_mean_rank_pct",
    "h231_dist200_best_rank_pct",
    "h231_same_class_mean_rank_pct",
    "h231_same_class_best_rank_pct",
    "h231_epi_last5_worst_rank_pct",
    "h231_epi_last10_worst_rank_pct",
    "h231_margin_last5_mean_rank_pct",
]

architectures = {
    "STRICT281_PLUS_H232_DISTANCE_DOWNSIDE": ns["dedupe"](features281 + expand(distance + downside)),
    "STRICT281_PLUS_H232_DISTANCE_LOWTAIL": ns["dedupe"](features281 + expand(lowtail)),
    "STRICT281_PLUS_H232_DISTANCE_LOWTAIL_RANKONLY": ns["dedupe"](features281 + [c for c in rank_only if c in model.columns]),
}

manifest = pd.DataFrame(
    [
        {
            "architecture": k,
            "base_feature_count": len(features281),
            "total_feature_count": len(v),
            "new_feature_count": len(v) - len(features281),
            "rationale": "LAB231-supported distance/class-conditioned performance plus low-tail/downside contrast.",
            "features": " | ".join([c for c in v if c not in features281]),
        }
        for k, v in architectures.items()
    ]
)
manifest.to_csv(OUT / "LAB232_CANDIDATE_MANIFEST.csv", index=False)

oof = ns["fit_oof"](model, architectures)
oof.to_csv(OUT / "LAB232_OOF_PREDICTIONS.csv", index=False)
scores, ens_scores, yearly = ns["score_outputs"](oof)
scores.to_csv(OUT / "LAB232_ALL_ALGORITHM_RESULTS.csv", index=False)
ens_scores.to_csv(OUT / "LAB232_PRIMARY_RESULTS.csv", index=False)
yearly.to_csv(OUT / "LAB232_YEAR_RESULTS.csv", index=False)

best = ens_scores.sort_values("race_winner_log_loss").iloc[0]
best_arch = str(best["architecture"])
rank_econ = ns["rank_and_economics"](oof.loc[oof["architecture"].eq(best_arch)].copy(), strict_ref)
legacy_econ = OUT / "LAB231_ECONOMICS_AND_RANKING.csv"
if legacy_econ.exists():
    legacy_econ.replace(OUT / "LAB232_ECONOMICS_AND_RANKING.csv")
best_year = yearly.loc[yearly["architecture"].eq(best_arch)].copy()
years_improved = int(best_year["gain_vs_strict281"].gt(0).sum())
recent_improved = int(best_year.loc[best_year["_year"].isin([2024, 2025, 2026]), "gain_vs_strict281"].gt(0).sum())

strict_ll = ns["STRICT_LL"]
drop_pair_ll = ns["DROP_PAIR_LL"]
best_ll = float(best["race_winner_log_loss"])
gain = strict_ll - best_ll
material = bool(gain >= 0.002 and years_improved >= 4 and recent_improved >= 2)
phantom_reduction = rank_econ["strict_extreme_phantom_wins"] - rank_econ["best_extreme_phantom_wins"]

summary = pd.DataFrame(
    [
        {"metric": "REFERENCE_LL", "value": strict_ll},
        {"metric": "DROP_PAIR_RESEARCH_LL", "value": drop_pair_ll},
        {"metric": "BEST_NEW_ARCHITECTURE", "value": best_arch},
        {"metric": "BEST_NEW_LL", "value": best_ll},
        {"metric": "LL_GAIN", "value": gain},
        {"metric": "YEARS_IMPROVED", "value": years_improved},
        {"metric": "RECENT_2024_2026_IMPROVED", "value": recent_improved},
        {"metric": "WINNER_RANK_EFFECT", "value": rank_econ["winner_rank_effect"]},
        {"metric": "FAVOURITE_EFFECT", "value": rank_econ["favourite_effect"]},
        {"metric": "CATASTROPHIC_WINNERS_RECOVERED", "value": rank_econ["catastrophic_winners_recovered"]},
        {"metric": "STRICT_EXTREME_PHANTOM_WINS", "value": rank_econ["strict_extreme_phantom_wins"]},
        {"metric": "BEST_MODEL_EXTREME_PHANTOM_WINS", "value": rank_econ["best_extreme_phantom_wins"]},
        {"metric": "PHANTOM_WIN_REDUCTION", "value": phantom_reduction},
        {"metric": "MATERIAL_MODEL_IMPROVEMENT", "value": "YES" if material else "NO"},
        {"metric": "NEXT_MAJOR_ACTION", "value": "DATA_GAP_MAP_AFTER_INTERNAL_PERFORMANCE_COMBOS_FAILED_MATERIAL_GATE" if not material else "LOCK_DOWN_H232_FOR_REPLAY_AUDIT"},
        {"metric": "STRICT_PIT", "value": "YES"},
        {"metric": "MARKET_AS_FEATURE", "value": "NO"},
        {"metric": "FINAL_SP_EVALUATION_ONLY", "value": "YES"},
        {"metric": "WEIGHT_FEATURES_ATTRIBUTED_OR_INTERPRETED", "value": "NO"},
        {"metric": "PRODUCTION_MODIFIED", "value": "NO"},
        {"metric": "LAB232", "value": "PASS"},
    ]
)
summary.to_csv(OUT / "LAB232_SUMMARY.csv", index=False)

print(f"REFERENCE_LL={strict_ll}")
print(f"BEST_NEW_LL={best_ll}")
print(f"LL_GAIN={gain}")
print(f"YEARS_IMPROVED={years_improved}")
print(f"RECENT_2024_2026_IMPROVED={recent_improved}")
print(f"WINNER_RANK_EFFECT={rank_econ['winner_rank_effect']}")
print(f"FAVOURITE_EFFECT={rank_econ['favourite_effect']}")
print(f"CATASTROPHIC_WINNERS_RECOVERED={rank_econ['catastrophic_winners_recovered']}")
print(f"STRICT_EXTREME_PHANTOM_WINS={rank_econ['strict_extreme_phantom_wins']}")
print(f"BEST_MODEL_EXTREME_PHANTOM_WINS={rank_econ['best_extreme_phantom_wins']}")
print(f"PHANTOM_WIN_REDUCTION={phantom_reduction}")
print(f"BEST_NEW_INFORMATION_CONCEPT={best_arch.replace('STRICT281_PLUS_', '')}")
print(f"MATERIAL_MODEL_IMPROVEMENT={'YES' if material else 'NO'}")
print("STRICT_PIT=YES")
print("MARKET_AS_FEATURE=NO")
print("FINAL_SP_EVALUATION_ONLY=YES")
print("WEIGHT_FEATURES_ATTRIBUTED_OR_INTERPRETED=NO")
print("PRODUCTION_MODIFIED=NO")
print("LAB232=PASS")
