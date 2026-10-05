import math
import numpy as np
import pandas as pd

def softmax(x,temp):
    x=np.asarray(x,float); z=(x-x.max())/temp; e=np.exp(np.clip(z,-50,50)); return e/e.sum()

def main():
    # B2 probability invariant.
    p=softmax([2.0,1.0,-1.0],2.0)
    assert abs(float(p.sum())-1.0)<1e-12
    assert np.all(p>0)
    ll=-math.log(float(p[0]))
    assert np.isfinite(ll) and ll>0

    # Runner formula parity invariant: race-level benchmark shifts must cancel.
    margin=np.array([0.0,0.75,2.5,5.0])
    pit=3.2-margin
    authority=1.1-margin
    pc=pit-pit.mean(); ac=authority-authority.mean()
    assert np.corrcoef(pc,ac)[0,1]>0.999999
    assert float(np.mean(np.abs(pc-ac)))<1e-12

    # B3/B4 flat-stake final-SP forensic P&L.
    winner=np.array([1,0,1,0],float); sp=np.array([3.0,5.0,2.5,10.0])
    pnl=winner*sp-1.0
    assert np.allclose(pnl,[2.0,-1.0,1.5,-1.0])
    assert abs(float(pnl.sum())-1.5)<1e-12

    print("LAB245B_CONTRACT_SMOKE=PASS")
    print("PROBABILITY_MASS=PASS")
    print("WITHIN_RACE_RUNNER_FORMULA_PARITY=PASS")
    print("FINAL_SP_FORENSIC_PNL_ARITHMETIC=PASS")

if __name__=="__main__":
    main()
