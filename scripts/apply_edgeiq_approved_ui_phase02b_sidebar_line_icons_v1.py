from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_APPROVED_UI_PHASE02B_SIDEBAR_LINE_ICONS_{STAMP}"


TSX = """import {
  ArrowUpDown,
  BadgeDollarSign,
  CalendarDays,
  ClipboardCheck,
  ClipboardList,
  Crosshair,
  FileText,
  FlaskConical,
  Home,
  Lightbulb,
  LineChart,
  Map,
  Settings,
  SlidersHorizontal,
  Trophy,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type GlobalSection =
  | "home"
  | "meetings"
  | "race"
  | "field"
  | "formGuide"
  | "performance"
  | "epi"
  | "map"
  | "market"
  | "overview"
  | "insights"
  | "results"
  | "lab"
  | "compare"
  | "review"
  | "settings";

type AppNavigationProps = {
  activeSection: GlobalSection;
  onSectionChange: (section: GlobalSection) => void;
};

const navItems: Array<{ key: GlobalSection; label: string; Icon: LucideIcon }> = [
  { key: "home", label: "HOME", Icon: Home },
  { key: "meetings", label: "MEETINGS", Icon: CalendarDays },
  { key: "race", label: "RACE", Icon: Crosshair },
  { key: "field", label: "FIELD", Icon: Users },
  { key: "formGuide", label: "FORM GUIDE", Icon: ClipboardList },
  { key: "performance", label: "PERFORMANCE", Icon: SlidersHorizontal },
  { key: "epi", label: "EPI", Icon: LineChart },
  { key: "map", label: "MAP", Icon: Map },
  { key: "market", label: "MARKET", Icon: BadgeDollarSign },
  { key: "overview", label: "OVERVIEW", Icon: ClipboardCheck },
  { key: "insights", label: "INSIGHTS", Icon: Lightbulb },
  { key: "results", label: "RESULTS", Icon: Trophy },
  { key: "lab", label: "LAB", Icon: FlaskConical },
  { key: "compare", label: "COMPARE", Icon: ArrowUpDown },
  { key: "review", label: "REVIEW", Icon: FileText },
  { key: "settings", label: "SETTINGS", Icon: Settings },
];

export function AppNavigation({ activeSection, onSectionChange }: AppNavigationProps) {
  return (
    <aside className="eiq-app-nav" aria-label="EDGEIQ global navigation">
      <div className="eiq-app-nav__brand">
        <strong>EDGE<span>iQ</span></strong>
        <em>Race Intelligence</em>
      </div>

      <nav>
        {navItems.map(({ Icon, ...item }) => (
          <button
            key={item.key}
            type="button"
            className={activeSection === item.key ? "is-active" : ""}
            onClick={() => onSectionChange(item.key)}
          >
            <span aria-hidden="true"><Icon size={19} strokeWidth={1.9} /></span>
            <strong>{item.label}</strong>
          </button>
        ))}
      </nav>
    </aside>
  );
}
"""


CSS = r"""
/* EDGEIQ APPROVED UI PHASE 02B SIDEBAR LINE ICONS */
.eiq-app-nav button span {
  border: 0;
  border-radius: 0;
  color: var(--eiq-approved-navy);
}

.eiq-app-nav button span svg {
  display: block;
}

.eiq-app-nav button.is-active span,
.eiq-app-nav button:hover span {
  color: var(--eiq-approved-blue);
}
"""


def main() -> None:
    tsx = ROOT / "src" / "edgeiq-os" / "race" / "components" / "AppNavigation.tsx"
    css = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    for path in [tsx, css]:
        target = CHECKPOINT / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    tsx.write_text(TSX, encoding="utf-8", newline="")
    css_text = css.read_text(encoding="utf-8-sig")
    if "EDGEIQ APPROVED UI PHASE 02B SIDEBAR LINE ICONS" not in css_text:
        css.write_text(css_text.rstrip() + "\n\n" + CSS.strip() + "\n", encoding="utf-8", newline="")
    print(f"checkpoint={CHECKPOINT}")
    print("EDGEIQ_APPROVED_UI_PHASE02B_SIDEBAR_LINE_ICONS_PASS")


if __name__ == "__main__":
    main()
