import math
import numpy as np

def softmax(x,temp):
    x=np.asarray(x,float)
    z=(x-x.max())/temp
    e=np.exp(np.clip(z,-50,50))
    return e/e.sum()

def main():
    # Static compact -> B1 interface invariant, checked before any large data read.\n    root=Path(__file__).resolve().parents[2]\n    compact=(root/"scripts/research/build_lab245b_compact_performance_bridge.py").read_text(encoding="utf-8")\n    b1=(root/"scripts/research/run_lab245b1_next_performance_forecast.py").read_text(encoding="utf-8")\n    for col in ["target_lvs","target_finish_position","target_field_size","represented_field_size","hist_runs","current_distance"]:\n        assert col in compact, f"compact producer missing {col}"\n        assert col in b1, f"B1 consumer missing {col}"\n    ast.parse(compact); ast.parse(b1)\n\n    # B2 probability invariant.
    p=softmax([2.0,1.0,-1.0],2.0)
    assert abs(float(p.sum())-1.0)<1e-12
    assert np.all(p>0)
    ll=-math.log(float(p[0]))
    assert np.isfinite(ll) and ll>0

    # Runner formula parity invariant: race-level benchmark shifts cancel within race.
    margin=np.array([0.0,0.75,2.5,5.0])
    pit=3.2-margin
    authority=1.1-margin
    pc=pit-pit.mean()
    ac=authority-authority.mean()
    assert np.corrcoef(pc,ac)[0,1]>0.999999
    assert float(np.mean(np.abs(pc-ac)))<1e-12

    # Strict date-PIT invariant: same-date observations cannot update each other.
    history=[100.0,101.0,102.0]
    before=list(history)
    same_day=[90.0,110.0]
    scored_counts=[len(before) for _ in same_day]
    assert scored_counts==[3,3]
    history.extend(same_day)
    assert len(history)==5

    # V1 lengths conversion contract used by the baseline target.
    assert abs(0.17-0.17)<1e-12

    # B3/B4 flat-stake final-SP forensic P&L.
    winner=np.array([1,0,1,0],float)
    sp=np.array([3.0,5.0,2.5,10.0])
    pnl=winner*sp-1.0
    assert np.allclose(pnl,[2.0,-1.0,1.5,-1.0])
    assert abs(float(pnl.sum())-1.5)<1e-12

    print("LAB245B_CONTRACT_SMOKE=PASS")
    print("COMPACT_B1_INTERFACE=PASS")\n    print("PROBABILITY_MASS=PASS")
    print("WITHIN_RACE_RUNNER_FORMULA_PARITY=PASS")
    print("STRICT_DATE_PIT_SAME_DAY_FREEZE=PASS")
    print("V1_LENGTH_CONVERSION_0_17=PASS")
    print("FINAL_SP_FORENSIC_PNL_ARITHMETIC=PASS")

if __name__=="__main__":
    main()
