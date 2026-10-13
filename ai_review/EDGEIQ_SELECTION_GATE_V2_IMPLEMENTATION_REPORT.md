# EDGEiQ Selection Gate V2 Implementation Report

Status: implemented for research review.

## Scope

This change fixes and hardens the research-only BACK/LAY qualification engine. It does not modify production, place bets, access sealed outcomes, or claim historical ROI.

## Implemented

- Fail-closed input contract validation.
- Independent BACK WIN and LAY WIN qualification.
- Explicit Betfair exchange versus bookmaker fixed-win quote semantics.
- Quote timestamp, quote age, source/provider, certification and duplicate snapshot checks.
- Crossed exchange quote rejection.
- Lay liquidity and liability cap checks.
- Expected value per BACK stake and per LAY liability.
- Immutable paper-trading event IDs and optional append-only paper log output.
- Consolidated parameterized synthetic regression tests.

## Commands

```powershell
python -m py_compile scripts\research\run_edgeiq_selection_gate_v2.py scripts\research\test_edgeiq_selection_gate_v2_corrected.py scripts\research\test_edgeiq_selection_gate_v2.py
python scripts\research\test_edgeiq_selection_gate_v2_corrected.py
python scripts\research\test_edgeiq_selection_gate_v2.py
python scripts\research\run_edgeiq_selection_gate_v2.py --input outputs\research\selection_gate_v2\EDGEIQ_SELECTION_GATE_V2_SYNTHETIC_INPUT.csv --output outputs\research\selection_gate_v2\EDGEIQ_SELECTION_GATE_V2_SYNTHETIC_CLASSIFIED.csv --audit outputs\research\selection_gate_v2\EDGEIQ_SELECTION_GATE_V2_SYNTHETIC_AUDIT.json --paper-log outputs\research\selection_gate_v2\EDGEIQ_SELECTION_GATE_V2_SYNTHETIC_PAPER_LOG.csv --min-depth 30 --max-lay-liability 100 --max-quote-age-seconds 60
```

## Results

- Compile: PASS
- Consolidated corrected test: PASS
- Compatibility test wrapper: PASS
- Synthetic gate run: PASS
- Synthetic rows: 3
- BACK status counts: `RESEARCH_CANDIDATE=1`, `NO_VALUE=1`, `FAIL_CLOSED=1`
- LAY status counts: `RESEARCH_CANDIDATE=1`, `NO_VALUE=1`, `FAIL_CLOSED=1`
- Paper log rows: 3
- Execution authorized: FALSE
- Profitability claim: FALSE

Synthetic outputs:

- `outputs/research/selection_gate_v2/EDGEIQ_SELECTION_GATE_V2_SYNTHETIC_INPUT.csv`
- `outputs/research/selection_gate_v2/EDGEIQ_SELECTION_GATE_V2_SYNTHETIC_CLASSIFIED.csv`
- `outputs/research/selection_gate_v2/EDGEIQ_SELECTION_GATE_V2_SYNTHETIC_AUDIT.json`
- `outputs/research/selection_gate_v2/EDGEIQ_SELECTION_GATE_V2_SYNTHETIC_PAPER_LOG.csv`

## Governance

- `execution_authorized` is always `False`.
- `research_only` is always `True`.
- Outcome, SP, BSP, result, closing price and return columns fail closed.
- Historical profitability is not tested or claimed.
- Market odds are accepted only as prospective qualification evidence, not as model-training features.
