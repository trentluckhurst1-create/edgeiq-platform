from pathlib import Path
import json
import math

import numpy as np
import pandas as pd


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
BASE = ROOT / "outputs" / "research" / "model_price_diagnostics"
OUT = BASE / "lab230"
OUT.mkdir(parents=True, exist_ok=True)

LAB229_OOF = BASE / "lab229" / "LAB229_OOF_PREDICTIONS_CORRECTED.csv"
LAB229_BC = BASE / "lab229" / "LAB229_BC_RANKING_RESPONSE_CORRECTED.csv"
LAB179_OOF = BASE / "lab179" / "LAB179_OOF_PREDICTIONS.csv"
LAB219_PAIR = BASE / "lab219" / "LAB219_PAIR_LEARNER_RESPONSE.csv"
LAB227_DETAIL = BASE / "lab227" / "LAB227_INTERACTION_DETAIL.csv"
LAB205_CATA = BASE / "lab205" / "LAB205_CATASTROPHIC_WINNER_CASES.csv"
LAB202_FAIL = BASE / "lab202" / "LAB202_FAILURE_SIGNATURES.csv"
LAB217_FAMILY = BASE / "lab217" / "LAB217_FEATURE_FAMILY_REGRET.csv"

STRICT = "STRICT281_BASELINE"
DROP = "DROP_TRAINER_WIN_PAIR"
EXPECTED = {
    STRICT: 2.0328310797721265,
    DROP: 2.0321077047495013,
}
EPS = 1e-12


def read_csv(path, **kwargs):
    if not path.exists():
        raise RuntimeError(f"Missing required file: {path}")
    return pd.read_csv(path, low_memory=False, **kwargs)


def norm_ids(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df


def race_winner_ll(df):
    winners = df.loc[pd.to_numeric(df["_y"], errors="raise").eq(1)].copy()
    counts = winners.groupby("_race", sort=False).size()
    if not counts.eq(1).all():
        raise RuntimeError("Winner count gate failed.")
    return float(-np.log(pd.to_numeric(winners["p_model"], errors="raise").clip(1e-15, 1.0)).mean())


def summarize_values(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return {
            "mean": np.nan,
            "median": np.nan,
            "p10": np.nan,
            "p25": np.nan,
            "p75": np.nan,
            "p90": np.nan,
            "p95": np.nan,
            "p99": np.nan,
        }
    qs = s.quantile([0.10, 0.25, 0.75, 0.90, 0.95, 0.99])
    return {
        "mean": float(s.mean()),
        "median": float(s.median()),
        "p10": float(qs.loc[0.10]),
        "p25": float(qs.loc[0.25]),
        "p75": float(qs.loc[0.75]),
        "p90": float(qs.loc[0.90]),
        "p95": float(qs.loc[0.95]),
        "p99": float(qs.loc[0.99]),
    }


def profit_units(frame, p_col):
    return float(np.where(frame["_y"].eq(1), frame["final_sp"] - 1.0, -1.0).sum())


def economics(frame, p_col, mask, label):
    z = frame.loc[mask & frame["final_sp"].notna()].copy()
    bets = int(len(z))
    wins = int(z["_y"].sum()) if bets else 0
    expected = float(z[p_col].sum()) if bets else 0.0
    profit = profit_units(z, p_col) if bets else 0.0
    return {
        "bet_definition": label,
        "bets": bets,
        "wins": wins,
        "expected_wins": expected,
        "phantom_wins": expected - wins,
        "profit_units": profit,
        "POT": profit / bets if bets else np.nan,
    }


def boolify(s):
    if pd.api.types.is_bool_dtype(s):
        return s.fillna(False)
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes"])


print("=" * 100)
print("LAB230 - RESIDUAL RANKING + PHANTOM-OVERLAY DECOMPOSITION")
print("=" * 100)
print("NEW_MODEL_FITTING=NO")
print("MARKET_AS_FEATURE=NO")
print("FINAL_SP_EVALUATION_ONLY=YES")

oof = read_csv(LAB229_OOF, usecols=["_race", "_horse", "_year", "_y", "p_model", "architecture", "algorithm"])
oof = norm_ids(oof, ["_race", "_horse", "architecture", "algorithm"])
oof["_year"] = pd.to_numeric(oof["_year"], errors="raise").astype(int)
oof["_y"] = pd.to_numeric(oof["_y"], errors="raise").astype(int)
oof["p_model"] = pd.to_numeric(oof["p_model"], errors="raise")
ens = oof.loc[oof["algorithm"].eq("ENSEMBLE") & oof["architecture"].isin([STRICT, DROP])].copy()

input_rows = []
for arch in [STRICT, DROP]:
    z = ens.loc[ens["architecture"].eq(arch)].copy()
    rows = int(len(z))
    races = int(z["_race"].nunique())
    sum_err = float((z.groupby("_race", sort=False)["p_model"].sum() - 1.0).abs().max())
    ll = race_winner_ll(z)
    ll_error = abs(ll - EXPECTED[arch])
    gate = rows == 53804 and sum_err <= 1e-10 and ll_error <= 1e-10
    input_rows.append({
        "architecture": arch,
        "rows": rows,
        "races": races,
        "max_race_sum_error": sum_err,
        "race_winner_log_loss": ll,
        "expected_log_loss": EXPECTED[arch],
        "ll_abs_error": ll_error,
        "gate": "PASS" if gate else "FAIL",
    })
    if not gate:
        raise RuntimeError(f"Input gate failed for {arch}: rows={rows}, sum_err={sum_err}, ll={ll}")

input_audit = pd.DataFrame(input_rows)
input_audit.to_csv(OUT / "LAB230_INPUT_AUDIT.csv", index=False)

wide = ens.pivot_table(
    index=["_race", "_horse", "_year", "_y"],
    columns="architecture",
    values="p_model",
    aggfunc="first",
).reset_index()
wide.columns.name = None
wide = wide.rename(columns={STRICT: "p_strict281", DROP: "p_drop_pair"})

for arch, p_col, r_col in [(STRICT, "p_strict281", "rank_strict281"), (DROP, "p_drop_pair", "rank_drop_pair")]:
    ranks = wide.sort_values(["_race", p_col, "_horse"], ascending=[True, False, True]).copy()
    ranks[r_col] = ranks.groupby("_race", sort=False).cumcount() + 1
    wide = wide.merge(ranks[["_race", "_horse", r_col]], on=["_race", "_horse"], how="left", validate="one_to_one")

winners = wide.loc[wide["_y"].eq(1)].copy()
winners["winner_logloss_strict281"] = -np.log(winners["p_strict281"].clip(1e-15, 1.0))
winners["winner_logloss_drop_pair"] = -np.log(winners["p_drop_pair"].clip(1e-15, 1.0))
winners["ll_gain"] = winners["winner_logloss_strict281"] - winners["winner_logloss_drop_pair"]
winners["winner_probability_change"] = winners["p_drop_pair"] - winners["p_strict281"]
winners["winner_rank_change"] = winners["rank_strict281"] - winners["rank_drop_pair"]
winners["rank_movement"] = np.select(
    [winners["winner_rank_change"].gt(0), winners["winner_rank_change"].lt(0)],
    ["WINNER_RANK_IMPROVED", "WINNER_RANK_WORSENED"],
    default="WINNER_RANK_UNCHANGED",
)
winners["period"] = np.where(winners["_year"].lt(2024), "PRE2024", "2024_2026")
winners.to_csv(OUT / "LAB230_RACE_LL_DECOMPOSITION.csv", index=False)

pos = winners.loc[winners["ll_gain"].gt(EPS), "ll_gain"].sort_values(ascending=False)
neg = winners.loc[winners["ll_gain"].lt(-EPS), "ll_gain"]
total_pos = float(pos.sum())
concentration_rows = []
for share in [0.01, 0.05, 0.10, 0.20]:
    n = max(1, int(math.ceil(len(pos) * share))) if len(pos) else 0
    concentration_rows.append({
        "metric": f"positive_gain_top_{int(share * 100)}pct_share",
        "races": n,
        "value": float(pos.head(n).sum() / total_pos) if total_pos else np.nan,
    })

ll_summary = {
    "races_improved": int(winners["ll_gain"].gt(EPS).sum()),
    "races_worsened": int(winners["ll_gain"].lt(-EPS).sum()),
    "races_unchanged": int(winners["ll_gain"].abs().le(EPS).sum()),
    "gross_ll_improvement": total_pos,
    "gross_ll_deterioration": float(neg.sum()),
    "net_ll_improvement_sum": float(winners["ll_gain"].sum()),
    "net_ll_improvement_mean": float(winners["ll_gain"].mean()),
}
ll_summary.update(summarize_values(winners["ll_gain"]))
pd.DataFrame([ll_summary] + concentration_rows).to_csv(OUT / "LAB230_SUMMARY_LL_DISTRIBUTION.csv", index=False)

rank_rows = []
for label, z in winners.groupby("rank_movement", sort=False):
    rank_rows.append({
        "rank_movement": label,
        "races": int(len(z)),
        "share": float(len(z) / len(winners)),
        "mean_rank_change": float(z["winner_rank_change"].mean()),
        "median_rank_change": float(z["winner_rank_change"].median()),
        "mean_ll_gain": float(z["ll_gain"].mean()),
        "mean_winner_probability_change": float(z["winner_probability_change"].mean()),
    })

def transition_label(a, b):
    if a == 2 and b == 1:
        return "rank_2_to_1"
    if a == 3 and b == 1:
        return "rank_3_to_1"
    if a >= 4 and b == 1:
        return "rank_4plus_to_1"
    if a >= 6 and b <= 3:
        return "rank_6plus_to_top3"
    if a <= 1 and b >= 4:
        return "rank_1_to_4plus"
    if a <= 3 and b >= 6:
        return "top3_to_rank_6plus"
    return "other"

winners["rank_transition"] = [transition_label(int(a), int(b)) for a, b in zip(winners["rank_strict281"], winners["rank_drop_pair"])]
rank_trans = winners.groupby("rank_transition", sort=False).agg(
    races=("_race", "count"),
    mean_ll_gain=("ll_gain", "mean"),
    mean_rank_change=("winner_rank_change", "mean"),
).reset_index()
winner_rank_movement = pd.concat([pd.DataFrame(rank_rows), rank_trans], ignore_index=True, sort=False)
winner_rank_movement.to_csv(OUT / "LAB230_WINNER_RANK_MOVEMENT.csv", index=False)

fav_strict = wide.sort_values(["_race", "p_strict281", "_horse"], ascending=[True, False, True]).drop_duplicates("_race", keep="first")
fav_drop = wide.sort_values(["_race", "p_drop_pair", "_horse"], ascending=[True, False, True]).drop_duplicates("_race", keep="first")
fav = winners[["_race", "_horse", "_year", "ll_gain"]].rename(columns={"_horse": "winner_horse"})
fav = fav.merge(fav_strict[["_race", "_horse"]].rename(columns={"_horse": "strict_favourite"}), on="_race", how="left", validate="one_to_one")
fav = fav.merge(fav_drop[["_race", "_horse"]].rename(columns={"_horse": "drop_favourite"}), on="_race", how="left", validate="one_to_one")
fav["favourite_transition"] = np.where(fav["strict_favourite"].eq(fav["drop_favourite"]), "SAME_FAVOURITE", "CHALLENGER_CHANGED_FAVOURITE")
fav["strict_correct"] = fav["strict_favourite"].eq(fav["winner_horse"])
fav["drop_correct"] = fav["drop_favourite"].eq(fav["winner_horse"])
fav["changed_favourite_class"] = np.select(
    [
        fav["favourite_transition"].eq("SAME_FAVOURITE"),
        ~fav["strict_correct"] & fav["drop_correct"],
        fav["strict_correct"] & ~fav["drop_correct"],
        ~fav["strict_correct"] & ~fav["drop_correct"],
    ],
    ["SAME_FAVOURITE", "STRICT_WRONG_DROP_CORRECT", "STRICT_CORRECT_DROP_WRONG", "BOTH_WRONG"],
    default="OTHER_TIE",
)
fav_summary = fav.groupby(["favourite_transition", "changed_favourite_class"], sort=False).agg(
    races=("_race", "count"),
    mean_ll_gain=("ll_gain", "mean"),
).reset_index()
fav.to_csv(OUT / "LAB230_FAVOURITE_TRANSITIONS_DETAIL.csv", index=False)
fav_summary.to_csv(OUT / "LAB230_FAVOURITE_TRANSITIONS.csv", index=False)

pair219 = read_csv(LAB219_PAIR)
pair219 = norm_ids(pair219, ["_race", "focal_horse", "rival_horse", "population"])
pair219["HGB_favours_focal"] = boolify(pair219["HGB_favours_focal"])
pair219["LOGISTIC_favours_focal"] = boolify(pair219["LOGISTIC_favours_focal"])
b324 = pair219.loc[pair219["population"].eq("B_INTERNAL_SUPPORT") & ~pair219["HGB_favours_focal"] & ~pair219["LOGISTIC_favours_focal"]].copy()
c525 = pair219.loc[pair219["population"].eq("C_CONTROL")].copy()
if len(b324) != 324 or len(c525) != 525:
    raise RuntimeError(f"B/C membership gate failed: B={len(b324)}, C={len(c525)}")

pred_lookup = wide.set_index(["_race", "_horse"])[["p_strict281", "p_drop_pair"]]

def pair_response(pop_name, pp):
    rows = []
    for r in pp.to_dict("records"):
        fk = (str(r["_race"]), str(r["focal_horse"]))
        rk = (str(r["_race"]), str(r["rival_horse"]))
        f = pred_lookup.loc[fk]
        rv = pred_lookup.loc[rk]
        strict_gap = float(f["p_strict281"] - rv["p_strict281"])
        drop_gap = float(f["p_drop_pair"] - rv["p_drop_pair"])
        rows.append({
            "population": pop_name,
            "_race": fk[0],
            "focal_horse": fk[1],
            "rival_horse": rk[1],
            "strict_pair_gap": strict_gap,
            "drop_pair_gap": drop_gap,
            "pair_gap_change": drop_gap - strict_gap,
            "strict_focal_above": strict_gap > 0,
            "drop_focal_above": drop_gap > 0,
        })
    return pd.DataFrame(rows)

bc_detail = pd.concat([pair_response("B_SHARED_OVERRIDE", b324), pair_response("C_CONTROL", c525)], ignore_index=True)
bc_rows = []
for pop, z in bc_detail.groupby("population", sort=False):
    bc_rows.append({
        "population": pop,
        "races": int(len(z)),
        "strict_focal_above": int(z["strict_focal_above"].sum()),
        "drop_focal_above": int(z["drop_focal_above"].sum()),
        "rescued_or_preserved": int((~z["strict_focal_above"] & z["drop_focal_above"]).sum()) if pop == "B_SHARED_OVERRIDE" else int((z["strict_focal_above"] & z["drop_focal_above"]).sum()),
        "damaged_or_reversed": int((z["strict_focal_above"] & ~z["drop_focal_above"]).sum()) if pop == "C_CONTROL" else int((z["strict_focal_above"] & ~z["drop_focal_above"]).sum()),
        "mean_strict_pair_gap": float(z["strict_pair_gap"].mean()),
        "mean_drop_pair_gap": float(z["drop_pair_gap"].mean()),
        "mean_pair_gap_change": float(z["pair_gap_change"].mean()),
    })

d227 = read_csv(LAB227_DETAIL)
d227 = norm_ids(d227, ["_race", "focal_horse", "rival_horse"])
p05 = d227.loc[d227["audit_population"].astype(str).eq("B_SHARED_OVERRIDE") & d227["group"].astype(str).eq("PAIR::05")].copy()
p05_wide = p05.pivot_table(index=["_race", "focal_horse", "rival_horse"], columns="algorithm", values="reversal_to_focal", aggfunc="first").reset_index()
p05_wide["HGB"] = boolify(p05_wide["HGB"])
p05_wide["LOGISTIC"] = boolify(p05_wide["LOGISTIC"])
p05_17 = p05_wide.loc[p05_wide["HGB"] & p05_wide["LOGISTIC"]].copy()
if len(p05_17) != 17:
    raise RuntimeError(f"Pair05 membership gate failed: {len(p05_17)}")
p05_detail = pair_response("PAIR05_17", p05_17)
p05_rescued = int((~p05_detail["strict_focal_above"] & p05_detail["drop_focal_above"]).sum())
bc_rows.append({
    "population": "PAIR05_17",
    "races": 17,
    "strict_focal_above": int(p05_detail["strict_focal_above"].sum()),
    "drop_focal_above": int(p05_detail["drop_focal_above"].sum()),
    "rescued_or_preserved": p05_rescued,
    "damaged_or_reversed": int((p05_detail["strict_focal_above"] & ~p05_detail["drop_focal_above"]).sum()),
    "mean_strict_pair_gap": float(p05_detail["strict_pair_gap"].mean()),
    "mean_drop_pair_gap": float(p05_detail["drop_pair_gap"].mean()),
    "mean_pair_gap_change": float(p05_detail["pair_gap_change"].mean()),
})
B_RESCUES = int((~bc_detail.loc[bc_detail["population"].eq("B_SHARED_OVERRIDE"), "strict_focal_above"] & bc_detail.loc[bc_detail["population"].eq("B_SHARED_OVERRIDE"), "drop_focal_above"]).sum())
C_DAMAGE = int((bc_detail.loc[bc_detail["population"].eq("C_CONTROL"), "strict_focal_above"] & ~bc_detail.loc[bc_detail["population"].eq("C_CONTROL"), "drop_focal_above"]).sum())
bc_rows.append({
    "population": "NET_BC_RANKING_EFFECT",
    "races": np.nan,
    "strict_focal_above": np.nan,
    "drop_focal_above": np.nan,
    "rescued_or_preserved": B_RESCUES,
    "damaged_or_reversed": C_DAMAGE,
    "mean_strict_pair_gap": np.nan,
    "mean_drop_pair_gap": np.nan,
    "mean_pair_gap_change": B_RESCUES - C_DAMAGE,
})
pd.DataFrame(bc_rows).to_csv(OUT / "LAB230_BC_RESPONSE.csv", index=False)

cata = read_csv(LAB205_CATA)
cata = norm_ids(cata, ["race", "winner_horse"])
cata_eval = cata[["race", "winner_horse", "year", "model_rank", "p_model"]].rename(columns={"race": "_race", "winner_horse": "_horse", "model_rank": "prior_model_rank", "p_model": "prior_p_model"})
cata_eval = cata_eval.merge(winners[["_race", "_horse", "p_strict281", "p_drop_pair", "rank_strict281", "rank_drop_pair", "ll_gain"]], on=["_race", "_horse"], how="left", validate="one_to_one")
cata_eval["catastrophic_status"] = np.select(
    [
        cata_eval["rank_drop_pair"].lt(cata_eval["rank_strict281"]),
        cata_eval["rank_drop_pair"].gt(cata_eval["rank_strict281"]),
    ],
    ["IMPROVED_NOT_FIXED", "WORSENED"],
    default="UNCHANGED",
)
cata_eval.loc[cata_eval["rank_drop_pair"].eq(1), "catastrophic_status"] = "FIXED_TO_RANK1"
cata_eval.to_csv(OUT / "LAB230_CATASTROPHIC_RESPONSE.csv", index=False)

sp = read_csv(LAB179_OOF, usecols=["_race", "_horse", "_sp"])
sp = norm_ids(sp, ["_race", "_horse"])
sp["_sp"] = pd.to_numeric(sp["_sp"], errors="coerce")
sp = sp.dropna(subset=["_sp"]).drop_duplicates(["_race", "_horse", "_sp"])
sp_counts = sp.groupby(["_race", "_horse"], sort=False)["_sp"].nunique()
if int(sp_counts.max()) > 1:
    raise RuntimeError("Final SP source has conflicting prices for at least one runner.")
sp = sp.drop_duplicates(["_race", "_horse"], keep="first").rename(columns={"_sp": "final_sp"})
wide = wide.merge(sp, on=["_race", "_horse"], how="left", validate="one_to_one")
wide["strict_edge"] = wide["p_strict281"] * wide["final_sp"]
wide["drop_edge"] = wide["p_drop_pair"] * wide["final_sp"]
wide["strict_positive_edge"] = wide["strict_edge"].gt(1.0)
wide["drop_positive_edge"] = wide["drop_edge"].gt(1.0)
wide["strict_extreme"] = wide["strict_edge"].ge(2.0)
wide["drop_extreme"] = wide["drop_edge"].ge(2.0)
wide["overlay_transition"] = np.select(
    [
        wide["strict_extreme"] & wide["drop_extreme"],
        wide["strict_extreme"] & ~wide["drop_extreme"],
        ~wide["strict_extreme"] & wide["drop_extreme"],
    ],
    ["STRICT_EXTREME_TO_DROP_EXTREME", "STRICT_EXTREME_TO_DROP_NON_EXTREME", "STRICT_NON_EXTREME_TO_DROP_EXTREME"],
    default="NEITHER_EXTREME",
)

econ_rows = []
for model, p_col, pe_col, ex_col in [
    ("STRICT281", "p_strict281", "strict_positive_edge", "strict_extreme"),
    ("DROP_PAIR", "p_drop_pair", "drop_positive_edge", "drop_extreme"),
]:
    a = economics(wide, p_col, wide[pe_col], "POSITIVE_EDGE")
    b = economics(wide, p_col, wide[ex_col], "OVERLAY_100PCT_PLUS")
    a["model"] = model
    b["model"] = model
    econ_rows.extend([a, b])
overlay_econ = pd.DataFrame(econ_rows)

transition_rows = []
for trans, z in wide.groupby("overlay_transition", sort=False):
    transition_rows.append({
        "transition": trans,
        "runners": int(len(z)),
        "wins": int(z["_y"].sum()),
        "strict_expected_wins": float(z["p_strict281"].sum()),
        "drop_expected_wins": float(z["p_drop_pair"].sum()),
        "strict_phantom_wins": float(z["p_strict281"].sum() - z["_y"].sum()),
        "drop_phantom_wins": float(z["p_drop_pair"].sum() - z["_y"].sum()),
    })
pd.concat([overlay_econ, pd.DataFrame(transition_rows)], ignore_index=True, sort=False).to_csv(OUT / "LAB230_OVERLAY_TRANSITIONS.csv", index=False)

persistent = wide.loc[wide["strict_extreme"] & wide["drop_extreme"]].copy()
persistent_rows = [
    economics(persistent, "p_strict281", pd.Series(True, index=persistent.index), "PERSISTENT_EXTREME_STRICT_EXPECTATION"),
    economics(persistent, "p_drop_pair", pd.Series(True, index=persistent.index), "PERSISTENT_EXTREME_DROP_EXPECTATION"),
]
pd.DataFrame(persistent_rows).to_csv(OUT / "LAB230_PERSISTENT_EXTREME_OVERLAYS.csv", index=False)

race_overlay = wide.groupby("_race", sort=False).agg(
    strict_extreme_race=("strict_extreme", "any"),
    drop_extreme_race=("drop_extreme", "any"),
).reset_index()
race_overlay = race_overlay.merge(winners[["_race", "_year", "ll_gain"]], on="_race", how="left", validate="one_to_one")
race_overlay["ll_state"] = np.where(race_overlay["ll_gain"].gt(EPS), "LL_IMPROVED", "LL_WORSENED_OR_UNCHANGED")
race_overlay["overlay_state"] = np.select(
    [
        race_overlay["strict_extreme_race"] & ~race_overlay["drop_extreme_race"],
        race_overlay["strict_extreme_race"] & race_overlay["drop_extreme_race"],
    ],
    ["OVERLAY_REMOVED", "OVERLAY_PERSISTS"],
    default="NO_STRICT_EXTREME_BASE",
)
race_overlay["crosswalk_state"] = race_overlay["ll_state"] + "_" + race_overlay["overlay_state"]
wide = wide.merge(race_overlay[["_race", "ll_state"]], on="_race", how="left", validate="many_to_one")
wide["runner_crosswalk_state"] = np.select(
    [
        wide["ll_state"].eq("LL_IMPROVED") & wide["strict_extreme"] & ~wide["drop_extreme"],
        wide["ll_state"].eq("LL_IMPROVED") & wide["strict_extreme"] & wide["drop_extreme"],
        wide["ll_state"].ne("LL_IMPROVED") & wide["strict_extreme"] & ~wide["drop_extreme"],
        wide["ll_state"].ne("LL_IMPROVED") & wide["strict_extreme"] & wide["drop_extreme"],
        wide["ll_state"].eq("LL_IMPROVED") & ~wide["strict_extreme"] & wide["drop_extreme"],
        wide["ll_state"].ne("LL_IMPROVED") & ~wide["strict_extreme"] & wide["drop_extreme"],
    ],
    [
        "LL_IMPROVED_AND_OVERLAY_REMOVED",
        "LL_IMPROVED_OVERLAY_PERSISTS",
        "LL_WORSENED_OVERLAY_REMOVED",
        "LL_WORSENED_OVERLAY_PERSISTS",
        "LL_IMPROVED_NEW_DROP_OVERLAY",
        "LL_WORSENED_NEW_DROP_OVERLAY",
    ],
    default="NO_EXTREME_OVERLAY_INVOLVEMENT",
)
cross_rows = []
for state, z in wide.loc[wide["runner_crosswalk_state"].ne("NO_EXTREME_OVERLAY_INVOLVEMENT")].groupby("runner_crosswalk_state", sort=False):
    cross_rows.append({
        "state": state,
        "races": int(z["_race"].nunique()),
        "bets": int(len(z)),
        "wins": int(z["_y"].sum()),
        "strict_expected_wins": float(z["p_strict281"].sum()),
        "drop_expected_wins": float(z["p_drop_pair"].sum()),
        "strict_phantom_wins": float(z["p_strict281"].sum() - z["_y"].sum()),
        "drop_phantom_wins": float(z["p_drop_pair"].sum() - z["_y"].sum()),
        "strict_profit_units": profit_units(z, "p_strict281"),
        "drop_profit_units": profit_units(z, "p_drop_pair"),
        "strict_POT": profit_units(z, "p_strict281") / len(z) if len(z) else np.nan,
        "drop_POT": profit_units(z, "p_drop_pair") / len(z) if len(z) else np.nan,
    })
pd.DataFrame(cross_rows).to_csv(OUT / "LAB230_LL_ECONOMIC_CROSSWALK.csv", index=False)

residual_rows = []
if LAB202_FAIL.exists():
    fail = pd.read_csv(LAB202_FAIL, low_memory=False)
    population_col = "comparison" if "comparison" in fail.columns else "signature_table"
    family_col = "family" if "family" in fail.columns else "provenance"
    effect_col = (
        "abs_effect_size"
        if "abs_effect_size" in fail.columns
        else "abs_standardized_difference"
        if "abs_standardized_difference" in fail.columns
        else "effect_size"
    )
    target = fail.loc[fail[population_col].astype(str).eq("catastrophic_underpriced_winners_vs_other_winners")].copy()
    family_map = {
        "STRICT_ELO": "HISTORICAL_ABILITY",
        "STRONG70_RAW": "HISTORICAL_ABILITY",
        "STRONG70_RACE_RELATIVE": "PERFORMANCE",
        "LAB120_RACE_RELATIVE": "FORM_LINE_NETWORK",
        "FORM_LINE_RAW": "FORM_LINE_NETWORK",
        "FORM_LINE_RECENCY": "PREP_RECENCY",
        "LAB179_RECENCY_DYNAMIC": "PREP_RECENCY",
        "LAB174_RELIABILITY": "PREP_RECENCY",
    }
    for r in target.head(50).to_dict("records"):
        src_family = str(r.get(family_col, ""))
        mapped = "RACE_CONTEXT" if "barrier" in str(r.get("feature", "")).lower() else None
        if mapped is None:
            mapped = next((v for k, v in family_map.items() if k in src_family), "CONNECTION" if "trainer" in str(r.get("feature", "")).lower() or "jockey" in str(r.get("feature", "")).lower() else "UNMAPPED_PRIOR_FORENSIC")
        if "weight" in str(r.get("feature", "")).lower():
            mapped = "WEIGHT_QUARANTINED"
        residual_rows.append({
            "source": "LAB202_FAILURE_SIGNATURES",
            "population": "catastrophic_underpriced_winners_vs_other_winners",
            "feature": r.get("feature"),
            "source_family": src_family,
            "mapped_lab230_family": mapped,
            "effect_size": r.get(effect_col, np.nan),
            "coverage": r.get("A_coverage", r.get("coverage", np.nan)),
            "note": "Prior certified descriptive signature; final SP not used for feature selection in LAB230.",
        })
if LAB217_FAMILY.exists():
    fam = pd.read_csv(LAB217_FAMILY, low_memory=False)
    for r in fam.head(30).to_dict("records"):
        residual_rows.append({
            "source": "LAB217_FEATURE_FAMILY_REGRET",
            "population": "market_gap_regime",
            "feature": r.get("feature"),
            "source_family": r.get("family"),
            "mapped_lab230_family": r.get("family"),
            "effect_size": r.get("abs_high_minus_edgeiq", r.get("high_minus_edgeiq_diff", np.nan)),
            "coverage": r.get("coverage", r.get("races", np.nan)),
            "note": "Prior governed family contrast used descriptively for residual mechanism diagnosis.",
        })
residual = pd.DataFrame(residual_rows)
if residual.empty:
    residual = pd.DataFrame([{"source": "NONE", "note": "No residual feature forensic source recovered."}])
residual.to_csv(OUT / "LAB230_RESIDUAL_FEATURE_FORENSICS.csv", index=False)

year_rows = []
for label, filt in [("ALL", winners.index == winners.index), ("PRE2024", winners["_year"].lt(2024)), ("2024_2026", winners["_year"].ge(2024))]:
    z = winners.loc[filt]
    if len(z):
        year_rows.append({
            "period": label,
            "races": int(len(z)),
            "ll_gain_mean": float(z["ll_gain"].mean()),
            "rank_improved": int(z["rank_movement"].eq("WINNER_RANK_IMPROVED").sum()),
            "rank_worsened": int(z["rank_movement"].eq("WINNER_RANK_WORSENED").sum()),
            "rank_net": int(z["rank_movement"].eq("WINNER_RANK_IMPROVED").sum() - z["rank_movement"].eq("WINNER_RANK_WORSENED").sum()),
        })
for year, z in winners.groupby("_year", sort=True):
    year_rows.append({
        "period": str(year),
        "races": int(len(z)),
        "ll_gain_mean": float(z["ll_gain"].mean()),
        "rank_improved": int(z["rank_movement"].eq("WINNER_RANK_IMPROVED").sum()),
        "rank_worsened": int(z["rank_movement"].eq("WINNER_RANK_WORSENED").sum()),
        "rank_net": int(z["rank_movement"].eq("WINNER_RANK_IMPROVED").sum() - z["rank_movement"].eq("WINNER_RANK_WORSENED").sum()),
    })
year_stability = pd.DataFrame(year_rows)
year_stability.to_csv(OUT / "LAB230_YEAR_STABILITY.csv", index=False)

dominant_family = "UNDETERMINED"
if not residual.empty and "mapped_lab230_family" in residual.columns:
    rr = residual.loc[~residual["mapped_lab230_family"].astype(str).eq("WEIGHT_QUARANTINED")].copy()
    rr["abs_effect"] = pd.to_numeric(rr["effect_size"], errors="coerce").abs()
    fam_score = rr.groupby("mapped_lab230_family", sort=False)["abs_effect"].mean().sort_values(ascending=False)
    if len(fam_score):
        dominant_family = str(fam_score.index[0])

strict_ll = EXPECTED[STRICT]
drop_ll = EXPECTED[DROP]
fav_corrected = int(fav["changed_favourite_class"].eq("STRICT_WRONG_DROP_CORRECT").sum())
fav_damaged = int(fav["changed_favourite_class"].eq("STRICT_CORRECT_DROP_WRONG").sum())
cat_fixed = int(cata_eval["catastrophic_status"].eq("FIXED_TO_RANK1").sum())
cat_remaining = int(cata_eval["catastrophic_status"].ne("FIXED_TO_RANK1").sum())
strict_extreme = int(wide["strict_extreme"].sum())
drop_extreme = int(wide["drop_extreme"].sum())
persistent_extreme = int((wide["strict_extreme"] & wide["drop_extreme"]).sum())
deescalated = int((wide["strict_extreme"] & ~wide["drop_extreme"]).sum())
new_extreme = int((~wide["strict_extreme"] & wide["drop_extreme"]).sum())
strict_ext_phantom = float(wide.loc[wide["strict_extreme"], "p_strict281"].sum() - wide.loc[wide["strict_extreme"], "_y"].sum())
drop_ext_phantom = float(wide.loc[wide["drop_extreme"], "p_drop_pair"].sum() - wide.loc[wide["drop_extreme"], "_y"].sum())
pre_net = int(year_stability.loc[year_stability["period"].eq("PRE2024"), "rank_net"].iloc[0])
recent_net = int(year_stability.loc[year_stability["period"].eq("2024_2026"), "rank_net"].iloc[0])

if B_RESCUES > C_DAMAGE and drop_ll < strict_ll:
    verdict = "SMALL_TRUE_RANKING_IMPROVEMENT_WITH_PHANTOM_OVERLAY_PERSISTENCE"
else:
    verdict = "PROBABILITY_REALLOCATION_WITH_UNRESOLVED_RANKING_AND_OVERLAY_FAILURE"

summary = pd.DataFrame([
    {"metric": "STRICT281_LL", "value": strict_ll},
    {"metric": "DROP_TRAINER_WIN_PAIR_LL", "value": drop_ll},
    {"metric": "LL_GAIN", "value": strict_ll - drop_ll},
    {"metric": "RACES_IMPROVED", "value": ll_summary["races_improved"]},
    {"metric": "RACES_WORSENED", "value": ll_summary["races_worsened"]},
    {"metric": "WINNER_RANK_IMPROVED", "value": int(winners["rank_movement"].eq("WINNER_RANK_IMPROVED").sum())},
    {"metric": "WINNER_RANK_WORSENED", "value": int(winners["rank_movement"].eq("WINNER_RANK_WORSENED").sum())},
    {"metric": "FAVOURITES_CORRECTED", "value": fav_corrected},
    {"metric": "FAVOURITES_DAMAGED", "value": fav_damaged},
    {"metric": "B324_RESCUED", "value": B_RESCUES},
    {"metric": "C525_DAMAGED", "value": C_DAMAGE},
    {"metric": "PAIR05_RESCUED", "value": p05_rescued},
    {"metric": "CATASTROPHIC_FIXED", "value": cat_fixed},
    {"metric": "CATASTROPHIC_REMAINING", "value": cat_remaining},
    {"metric": "STRICT_EXTREME_BETS", "value": strict_extreme},
    {"metric": "DROP_EXTREME_BETS", "value": drop_extreme},
    {"metric": "PERSISTENT_EXTREME_BETS", "value": persistent_extreme},
    {"metric": "EXTREME_DEESCALATED", "value": deescalated},
    {"metric": "EXTREME_NEW", "value": new_extreme},
    {"metric": "STRICT_EXTREME_PHANTOM_WINS", "value": strict_ext_phantom},
    {"metric": "DROP_EXTREME_PHANTOM_WINS", "value": drop_ext_phantom},
    {"metric": "PRE2024_RANKING_EFFECT", "value": pre_net},
    {"metric": "RECENT_2024_2026_RANKING_EFFECT", "value": recent_net},
    {"metric": "DOMINANT_RESIDUAL_FAILURE_FAMILY", "value": dominant_family},
    {"metric": "LAB230_VERDICT", "value": verdict},
    {"metric": "NEW_MODEL_FITTING", "value": "NO"},
    {"metric": "FEATURE_SELECTION", "value": "NO"},
    {"metric": "HYPERPARAMETER_SELECTION", "value": "NO"},
    {"metric": "THRESHOLD_TUNING", "value": "NO"},
    {"metric": "MARKET_AS_FEATURE", "value": "NO"},
    {"metric": "FINAL_SP_EVALUATION_ONLY", "value": "YES"},
    {"metric": "WEIGHT_FEATURES_ATTRIBUTED_OR_INTERPRETED", "value": "NO"},
    {"metric": "PRODUCTION_MODIFIED", "value": "NO"},
    {"metric": "LAB230", "value": "PASS"},
])
summary.to_csv(OUT / "LAB230_SUMMARY.csv", index=False)

print(f"STRICT281_LL={strict_ll}")
print(f"DROP_TRAINER_WIN_PAIR_LL={drop_ll}")
print(f"LL_GAIN={strict_ll - drop_ll}")
print(f"RACES_IMPROVED={ll_summary['races_improved']}")
print(f"RACES_WORSENED={ll_summary['races_worsened']}")
print(f"WINNER_RANK_IMPROVED={int(winners['rank_movement'].eq('WINNER_RANK_IMPROVED').sum())}")
print(f"WINNER_RANK_WORSENED={int(winners['rank_movement'].eq('WINNER_RANK_WORSENED').sum())}")
print(f"FAVOURITES_CORRECTED={fav_corrected}")
print(f"FAVOURITES_DAMAGED={fav_damaged}")
print(f"B324_RESCUED={B_RESCUES}")
print(f"C525_DAMAGED={C_DAMAGE}")
print(f"PAIR05_RESCUED={p05_rescued}")
print(f"CATASTROPHIC_FIXED={cat_fixed}")
print(f"CATASTROPHIC_REMAINING={cat_remaining}")
print(f"STRICT_EXTREME_BETS={strict_extreme}")
print(f"DROP_EXTREME_BETS={drop_extreme}")
print(f"PERSISTENT_EXTREME_BETS={persistent_extreme}")
print(f"EXTREME_DEESCALATED={deescalated}")
print(f"EXTREME_NEW={new_extreme}")
print(f"STRICT_EXTREME_PHANTOM_WINS={strict_ext_phantom}")
print(f"DROP_EXTREME_PHANTOM_WINS={drop_ext_phantom}")
print(f"PRE2024_RANKING_EFFECT={pre_net}")
print(f"RECENT_2024_2026_RANKING_EFFECT={recent_net}")
print(f"DOMINANT_RESIDUAL_FAILURE_FAMILY={dominant_family}")
print(f"LAB230_VERDICT={verdict}")
print("NEW_MODEL_FITTING=NO")
print("FEATURE_SELECTION=NO")
print("HYPERPARAMETER_SELECTION=NO")
print("THRESHOLD_TUNING=NO")
print("MARKET_AS_FEATURE=NO")
print("FINAL_SP_EVALUATION_ONLY=YES")
print("WEIGHT_FEATURES_ATTRIBUTED_OR_INTERPRETED=NO")
print("PRODUCTION_MODIFIED=NO")
print("LAB230=PASS")
