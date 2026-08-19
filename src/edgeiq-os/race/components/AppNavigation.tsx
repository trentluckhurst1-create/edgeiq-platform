import {
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
