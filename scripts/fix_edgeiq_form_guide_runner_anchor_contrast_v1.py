from datetime import datetime
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"FORM_GUIDE_RUNNER_ANCHOR_CONTRAST_V1_{STAMP}" / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
BLOCK = r'''

/* EDGEIQ FORM GUIDE RUNNER ANCHOR CONTRAST V1 */
.eiq-race-form-guide--v4 .eiq-form-runner-anchor,
.eiq-race-form-guide--v4 .eiq-form-runner-expand {
  appearance: none;
  display: inline-grid;
  gap: 2px;
  width: 100%;
  min-width: 0;
  border: 0 !important;
  background: transparent !important;
  color: var(--edgeiq-text-primary) !important;
  box-shadow: none !important;
  padding: 0 !important;
  text-align: left;
  line-height: 1.2;
}

.eiq-race-form-guide--v4 .eiq-form-runner-anchor strong,
.eiq-race-form-guide--v4 .eiq-form-runner-expand strong {
  color: var(--edgeiq-text-primary) !important;
  font-weight: 800;
  white-space: normal;
}

.eiq-race-form-guide--v4 .eiq-form-runner-anchor small,
.eiq-race-form-guide--v4 .eiq-form-runner-expand small {
  color: #b42318 !important;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
}
'''

CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(CSS, CHECKPOINT)
text = CSS.read_text(encoding="utf-8")
marker = "/* EDGEIQ FORM GUIDE RUNNER ANCHOR CONTRAST V1 */"
if marker in text:
    text = text[: text.index(marker)].rstrip() + "\n"
CSS.write_text(text.rstrip() + BLOCK, encoding="utf-8", newline="\n")
print(f"CHECKPOINT={CHECKPOINT}")
print("EDGEIQ_FORM_GUIDE_RUNNER_ANCHOR_CONTRAST_FIXED")
