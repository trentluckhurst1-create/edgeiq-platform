from pathlib import Path

ROOT = Path.cwd()
SCRIPT = ROOT / "dashboard" / "racing-dashboard" / "scripts" / "patch_active_truth_integration_v1.py"

code = r'''
from pathlib import Path

ROOT = Path.cwd()

TARGETS = [
    ROOT / "build_edgeiq_first_starter_engine_v1.py",
    ROOT / "build_edgeiq_uncertainty_engine_v1.py",
    ROOT / "build_edgeiq_form_depth_ability_v2.py",
]

PATCHES = [
    (
        'official_run_count =',
        '''
active_truth_run_count = pd.to_numeric(
    row.get("active_truth_official_run_count", 0),
    errors="coerce"
)

if pd.notna(active_truth_run_count) and active_truth_run_count > 0:
    official_run_count = active_truth_run_count
'''
    ),
    (
        'last3_rating =',
        '''
active_truth_last3 = pd.to_numeric(
    row.get("active_truth_3lsa", None),
    errors="coerce"
)

if pd.notna(active_truth_last3):
    last3_rating = active_truth_last3
'''
    ),
]

for target in TARGETS:

    if not target.exists():
        print("MISSING:", target)
        continue

    text = target.read_text(encoding="utf-8", errors="ignore")

    applied = 0

    for trigger, patch in PATCHES:

        if trigger in text and patch not in text:
            text = text.replace(trigger, patch + "\n\n" + trigger)
            applied += 1

    target.write_text(text, encoding="utf-8")

    print(f"PATCHED {target.name} | patches={applied}")

print("=" * 100)
print("ACTIVE TRUTH PATCH COMPLETE")
print("=" * 100)
'''

SCRIPT.write_text(code, encoding="utf-8")

print("SAVED:", SCRIPT)
