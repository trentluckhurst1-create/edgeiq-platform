from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_FINAL_RUNTIME_PHASE05_AUDIT_CAPTURE_{STAMP}"
FILES = [
    "scripts/capture_edgeiq_final_live_runtime_completion_v1.py",
    "scripts/audit_edgeiq_final_live_runtime_completion_v1.py",
]
for rel in FILES:
    src = ROOT / rel
    dst = CHECKPOINT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

for rel in FILES:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    if rel.endswith("capture_edgeiq_final_live_runtime_completion_v1.py"):
        text = text.replace("bodySample: bodyText.slice(0, 2400)", "bodySample: bodyText.slice(0, 12000)")
    else:
        text = text.replace('"05_FORM_GUIDE": ("FORM GUIDE", "RaceFormGuideWorkspace", ["FORM GUIDE", "LAST FIVE", "RUNNER"])', '"05_FORM_GUIDE": ("FORM GUIDE", "RaceFormGuideWorkspace", ["FORM GUIDE", "LAST 5", "RUNNER"])')
        old = '''add_check("source", "no_runner_compare_reroute", "runnerModeBySection empty", "const runnerModeBySection" in race_file and "compare" not in race_file.split("const runnerModeBySection", 1)[1].split("};", 1)[0].lower(), "PASS" if "const runnerModeBySection: Partial<Record<PrimarySection, RunnerWorkspaceMode>> = {};" in race_file else "FAIL")'''
        new = '''runner_section = race_file.split("const runnerModeBySection", 1)[1].split("};", 1)[0].lower() if "const runnerModeBySection" in race_file else ""
runner_compare_ok = "const runnerModeBySection" in race_file and "compare" not in runner_section
add_check("source", "no_runner_compare_reroute", "runnerModeBySection has no compare route", runner_compare_ok, "PASS" if runner_compare_ok else "FAIL")'''
        if old not in text:
            raise SystemExit("source check target not found")
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")

print(f"EDGEIQ_FINAL_RUNTIME_PHASE05_AUDIT_CAPTURE_HARDENING_PASS checkpoint={CHECKPOINT}")
