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

type NavItem = { key: GlobalSection; label: string; Icon: LucideIcon };
type NavGroup = { label: string; items: NavItem[] };

const navGroups: NavGroup[] = [
  {
    label: "RACE DAY",
    items: [
      { key: "home", label: "Dashboard", Icon: Home },
      { key: "meetings", label: "Meetings", Icon: CalendarDays },
      { key: "race", label: "Race", Icon: Crosshair },
      { key: "field", label: "Field", Icon: Users },
      { key: "formGuide", label: "Form", Icon: ClipboardList },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { key: "performance", label: "Performance", Icon: SlidersHorizontal },
      { key: "epi", label: "EPI Ratings", Icon: LineChart },
      { key: "map", label: "Speed Map", Icon: Map },
      { key: "market", label: "Market", Icon: BadgeDollarSign },
      { key: "overview", label: "Overview", Icon: ClipboardCheck },
      { key: "insights", label: "Insights", Icon: Lightbulb },
    ],
  },
  {
    label: "POST RACE",
    items: [
      { key: "results", label: "Results", Icon: Trophy },
      { key: "review", label: "Review", Icon: FileText },
    ],
  },
  {
    label: "TOOLS",
    items: [
      { key: "lab", label: "Research Lab", Icon: FlaskConical },
      { key: "compare", label: "Compare", Icon: ArrowUpDown },
      { key: "settings", label: "Settings", Icon: Settings },
    ],
  },
];

export function AppNavigation({ activeSection, onSectionChange }: AppNavigationProps) {
  return (
    <aside className="eiq-app-nav" aria-label="EDGEiQ Racing navigation">
      <div className="eiq-app-nav__brand">
        <div className="eiq-app-nav__mark" aria-hidden="true">E</div>
        <div>
          <strong>EDGE<span>iQ</span></strong>
          <em>RACING INTELLIGENCE</em>
        </div>
      </div>

      <nav className="eiq-app-nav__groups">
        {navGroups.map((group) => (
          <section className="eiq-app-nav__group" key={group.label} aria-label={group.label}>
            <p>{group.label}</p>
            <div>
              {group.items.map(({ Icon, ...item }) => (
                <button
                  key={item.key}
                  type="button"
                  data-section={item.key}
                  className={activeSection === item.key ? "is-active" : ""}
                  onClick={() => onSectionChange(item.key)}
                >
                  <span className="eiq-app-nav__icon" aria-hidden="true"><Icon size={16} strokeWidth={1.8} /></span>
                  <strong>{item.label}</strong>
                </button>
              ))}
            </div>
          </section>
        ))}
      </nav>

      <footer className="eiq-app-nav__footer">
        <div><span className="eiq-app-nav__live-dot" aria-hidden="true" /><strong>System online</strong></div>
        <small>Production workspace</small>
      </footer>
    </aside>
  );
}
