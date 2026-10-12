"""Issue23: deterministic live feature scaffold, explicitly NOT scoreable.

Build one row per runner for fully identified fields. Missing feature families remain
NA, never fabricated. No 2025-26 outcomes or historical result columns are read.
"""
from pathlib import Path
import pandas as pd
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
SRC=ROOT/"outputs/research/model_v2/issue23_live_identity/ISSUE23_LIVE_HISTORY_COVERAGE.csv"
OUT=ROOT/"outputs/research/model_v2/issue23_live_features"
FEATURES="current_distance hist_runs lvs_last1 lvs_mean3 lvs_mean5 lvs_median5 lvs_std5 lvs_peak lvs_worst5 margin_mean5 margin_std5 margin_worst5 margin_last1 margin_last2 last_distance margin_change_l1_l2 margin_per_runner_last1 margin_per_runner_last2 days_since_last dist200_runs dist200_lvs_mean dist200_lvs_best represented_field_size barrier_position_pct jockey_prior_starts jockey_prior_win_rate jockey_prior_top3_rate trainer_prior_starts trainer_prior_win_rate trainer_prior_top3_rate clean_finish_mean5 clean_last_finish clean_last_won clean_last_top3 clean_finish_hist_n".split()
def main():
 d=pd.read_csv(SRC,dtype={"race_id":"string","race_entry_id":"string","canonical_horse_id":"string"})
 if d.empty or d.duplicated(["race_date","race_id","race_entry_id"]).any():raise RuntimeError("STOP invalid source runner identities")
 race=d.groupby(["race_date","race_id"],dropna=False).match_status.agg(lambda x:x.eq("UNIQUE_NORMALIZED_CODE").all())
 selected=d.set_index(["race_date","race_id"]).loc[race[race].index].reset_index()
 if selected.empty:raise RuntimeError("STOP no fully identified races")
 if not selected.match_status.eq("UNIQUE_NORMALIZED_CODE").all():raise RuntimeError("STOP incomplete identity")
 if selected.canonical_horse_id.isna().any():raise RuntimeError("STOP missing certified identity")
 out=pd.DataFrame({"race_date":selected.race_date,"race_id":selected.race_id,"runner_id":selected.race_entry_id,"canonical_horse_id":selected.canonical_horse_id,"horse_name":selected.horse_name,"venue":selected.venue,"race_no":selected.race_no,"scratch_status":selected.scratched.map(lambda x:"SCRATCHED" if str(x).lower() in ("true","1") else "UNKNOWN")})
 for f in FEATURES:out[f]=float("nan")
 # Barrier percent requires a governed denominator and scratch rules; don't assume it.
 # The coverage file contains pre-2025 history counts, but those are not Stage011
 # hist_runs and must never be substituted for that feature.
 if "barrier" in selected.columns:out["declared_barrier_unvalidated"]=pd.to_numeric(selected.barrier,errors="coerce")
 if "jockey_code" in selected.columns:out["jockey_code_unvalidated"]=selected.jockey_code
 if "trainer_code" in selected.columns:out["trainer_code_unvalidated"]=selected.trainer_code
 out["feature_status"]="INCOMPLETE_DO_NOT_SCORE"
 OUT.mkdir(parents=True,exist_ok=True)
 path=OUT/"ISSUE23_FIVE_RACE_FEATURE_SCAFFOLD.csv"
 if path.exists():raise RuntimeError("STOP immutable output already exists")
 out.to_csv(path,index=False)
 print("FEATURE_SCAFFOLD_CREATED RUNNERS",len(out),"RACES",out.race_id.nunique())
 print("FEATURES",len(FEATURES),"POPULATED_CERTIFIED_FEATURES",0)
 print("OUTPUT",path)
 print("NOT_SCOREABLE: upstream PIT feature reconstruction and declarations required")
 print("NO_2025_2026_OUTCOMES_READ; NO_MARKET; NO_SCORING")
if __name__=="__main__":main()
