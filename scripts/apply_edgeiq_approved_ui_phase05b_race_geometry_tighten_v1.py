from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_APPROVED_UI_PHASE05B_RACE_GEOMETRY_TIGHTEN_{STAMP}"


def main() -> None:
    css = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    target = CHECKPOINT / css.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(css, target)
    text = css.read_text(encoding="utf-8-sig")
    marker = "EDGEIQ APPROVED UI PHASE 05B RACE GEOMETRY TIGHTEN"
    append = f"""
/* {marker} */
.eiq-approved-race__context {{
  min-height: 96px;
}}

.eiq-approved-race__context p {{
  margin-bottom: 12px;
}}

.eiq-approved-race__meta {{
  margin-top: 18px;
}}

.eiq-approved-race__tabs {{
  min-height: 50px;
}}

.eiq-approved-race__grid {{
  gap: 12px;
}}

.eiq-approved-race__panel {{
  padding: 13px 15px;
}}

.eiq-approved-race__panel h2,
.eiq-approved-race__runner-board h2 {{
  margin-bottom: 11px;
}}

.eiq-approved-race__summary,
.eiq-approved-race__conditions {{
  min-height: 178px;
}}

.eiq-approved-race__summary dl,
.eiq-approved-race__conditions dl {{
  column-gap: 28px;
  row-gap: 9px;
}}

.eiq-approved-race__meeting dl,
.eiq-approved-race__actions {{
  gap: 7px;
}}

.eiq-approved-race__panel dt {{
  font-size: 10px;
}}

.eiq-approved-race__panel dd {{
  margin-top: 2px;
  font-size: 12px;
}}

.eiq-approved-race__races {{
  min-height: 332px;
}}

.eiq-approved-race__actions {{
  min-height: 216px;
}}
"""
    if marker not in text:
        text = text.rstrip() + "\n\n" + append.strip() + "\n"
    css.write_text(text, encoding="utf-8", newline="")
    print(f"checkpoint={CHECKPOINT}")
    print("EDGEIQ_APPROVED_UI_PHASE05B_RACE_GEOMETRY_TIGHTEN_PASS")


if __name__ == "__main__":
    main()
