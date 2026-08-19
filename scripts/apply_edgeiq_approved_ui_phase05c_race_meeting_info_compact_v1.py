from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_APPROVED_UI_PHASE05C_RACE_MEETING_INFO_COMPACT_{STAMP}"


CSS = r"""
/* EDGEIQ APPROVED UI PHASE 05C RACE MEETING INFO COMPACT */
.eiq-approved-race__meeting {
  padding-bottom: 12px;
}

.eiq-approved-race__meeting dl {
  gap: 0;
}

.eiq-approved-race__meeting dl > div {
  min-height: 21px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-items: baseline;
  gap: 12px;
}

.eiq-approved-race__meeting dt,
.eiq-approved-race__meeting dd {
  margin: 0;
  font-size: 11px;
  line-height: 1.25;
}

.eiq-approved-race__meeting dd {
  font-weight: 800;
  text-align: right;
}
"""


def main() -> None:
    css = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    target = CHECKPOINT / css.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(css, target)
    text = css.read_text(encoding="utf-8-sig")
    marker = "EDGEIQ APPROVED UI PHASE 05C RACE MEETING INFO COMPACT"
    if marker not in text:
        css.write_text(text.rstrip() + "\n\n" + CSS.strip() + "\n", encoding="utf-8", newline="")
    print(f"checkpoint={CHECKPOINT}")
    print("EDGEIQ_APPROVED_UI_PHASE05C_RACE_MEETING_INFO_COMPACT_PASS")


if __name__ == "__main__":
    main()
