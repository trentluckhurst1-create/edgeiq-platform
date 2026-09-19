# EDGEiQ All-Runner EPI Restore V1 — Acceptance

Status: PASS

This acceptance records the successful side-by-side reconstruction of the historical all-runner EPI/ERI lineage from the surviving 879,784-row Performance Fact Warehouse.

## Governed source
- Performance Fact Warehouse rows: 879,784
- Historical benchmark standards reconstructed: 586
- Production outputs changed: NO
- HPR chain changed: NO
- Market used as model input: NO

## Exact accepted cardinalities
- Unmatched benchmark rows: 232,783
- Invalid calculation rows: 113,614
- Runner lengths-v-standard rows: 533,387
- EPI rows: 533,387
- Race lengths-v-standard rows: 51,769
- ERI rows: 51,769

Arithmetic:
879,784 - 232,783 - 113,614 = 533,387

## Historical lookup semantics recovered
The July 26 producer built the 586 standard-time rows using the fuller physical grouping:
canonical track + track display name + track layout + distance + condition + jurisdiction + surface.

The downstream historical lookup then indexed standards using the reduced key:
canonical track + distance + condition + jurisdiction + surface.

Where multiple physical standard rows mapped to the same reduced key, the later loaded row overwrote the earlier row. The restoration runner intentionally reproduces this historical lookup behavior to reconstruct the original lineage exactly; it does not claim this overwrite behavior is a preferred future architecture.

## Reconstructed artifact hashes
- runner LVS: b08bb7a334ddba2f6a76942452dd964cd59db05001dc5710ff19aa7fc6e12926
- EPI: ef4fad0f0a1b10d78cc72cfb62e2cf097aa5f70119aed99c563b9afb31980f41
- race LVS: 5881a2d2490ecfb698eef31efe3f68cb257a0e810722877925d3a4e1b4c98fe3
- ERI: c318a9f2302c793575370d0d8fd1595c29a8331989def8a0b7745eaeefccffb0

The reconstructed EPI SHA256 exactly matches the surviving audited 533,387-row historical EPI artifact:
ef4fad0f0a1b10d78cc72cfb62e2cf097aa5f70119aed99c563b9afb31980f41

## Governance decision
- 533,387-row historical EPI artifact: CERTIFIED RECONSTRUCTABLE
- 51,769-row ERI artifact: CERTIFIED RECONSTRUCTABLE
- 533,388-row later mirror: NOT PROMOTED; quarantined pending explicit source-authority justification for its single additional row
- 879,784-row physical authority: UNCHANGED
- restored 52,309-row HPR chain: UNCHANGED

## Restoration runner
scripts/run_edgeiq_all_runner_epi_restore_v1.py

The runner is side-by-side and fail-closed. It writes only under:
work/all-runner-epi-restore-v1/

No production promotion is authorized by this acceptance.
