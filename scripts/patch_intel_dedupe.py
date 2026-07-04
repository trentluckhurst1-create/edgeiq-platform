from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

anchor = 'intel["horse_canon"] = intel["horse"].apply(canon)'

inject = '''
intel["horse_canon"] = intel["horse"].apply(canon)

# ====================================================================================
# HARD DEDUPE INTELLIGENCE LAYER
# ====================================================================================

intel_before = len(intel)

sort_cols = []

for c in [
    "confidence_score",
    "model_confidence_score",
    "race_date",
    "timestamp",
    "edge_pct"
]:
    if c in intel.columns:
        sort_cols.append(c)

if sort_cols:

    intel = (
        intel
        .sort_values(
            sort_cols,
            ascending=False,
            na_position="last"
        )
        .drop_duplicates(
            ["horse_canon"],
            keep="first"
        )
    )

intel_after = len(intel)

print("=" * 100)
print("INTEL DEDUPE")
print("=" * 100)
print("BEFORE:", intel_before)
print("AFTER :", intel_after)
print("REMOVED:", intel_before - intel_after)
'''

if anchor not in text:
    raise SystemExit("INTEL ANCHOR NOT FOUND")

text = text.replace(anchor, inject)

path.write_text(text, encoding="utf-8")

print("INTEL DEDUPE PATCHED")
