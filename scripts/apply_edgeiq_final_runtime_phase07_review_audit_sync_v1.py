from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_FINAL_RUNTIME_PHASE07_REVIEW_AUDIT_SYNC_{STAMP}"
rel = "scripts/audit_edgeiq_review_final_spec_v1.py"
src = ROOT / rel
dst = CHECKPOINT / rel
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src, dst)
text = src.read_text(encoding="utf-8")
old = 'for token in ["Race review workspace", "Reviewable Work", "Saved Review", "Review Boundary"]:'
new = 'for token in ["Sectional and performance review", "Review Structure", "Saved Review", "Review Boundary", "Stewards / Notes"]:'
if old not in text:
    raise SystemExit("Expected stale review audit token list not found")
src.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
print(f"EDGEIQ_FINAL_RUNTIME_PHASE07_REVIEW_AUDIT_SYNC_PASS checkpoint={CHECKPOINT}")
