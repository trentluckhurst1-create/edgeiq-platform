import {
  BadgeDollarSign,
  CalendarDays,
  CloudSun,
  Crosshair,
  Gauge,
  Home,
  Lightbulb,
  LineChart,
  Map,
  MapPinned,
  Settings,
  SlidersHorizontal,
  Trophy,
  ClipboardList,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * GlobalSection deliberately retains retired legacy keys in the type while the
 * application is migrated. They are NOT exposed in principal navigation.
 * This prevents the navigation cleanup from breaking old deep-link handlers.
 */
export type GlobalSection =
  | "home" | "meetings" | "race" | "field" | "formGuide" | "performance" | "epi" | "map"
  | "market" | "results" | "track" | "weather" | "overview" | "insights"
  | "lab" | "compare" | "review" | "settings";

type AppNavigationProps = {
  activeSection: GlobalSection;
  onSectionChange: (section: GlobalSection) => void;
};

type NavItem = { key: GlobalSection; label: string; Icon: LucideIcon };
type NavGroup = { label: string; items: NavItem[] };

/*
 * LOCKED 2026-09-15 product navigation.
 * Field is intentionally absent: it is the default internal Race view.
 * Review / Research Lab / Compare are intentionally absent from principal nav.
 */
const navGroups: NavGroup[] = [
  { label: "RACE DAY", items: [
    { key: "home", label: "Home", Icon: Home },
    { key: "meetings", label: "Meetings", Icon: CalendarDays },
    { key: "race", label: "Race", Icon: Crosshair },
    { key: "formGuide", label: "Form", Icon: ClipboardList },
  ]},
  { label: "INTELLIGENCE", items: [
    { key: "performance", label: "Performance", Icon: SlidersHorizontal },
    { key: "epi", label: "EPI Ratings", Icon: LineChart },
    { key: "map", label: "Speed Map", Icon: Map },
    { key: "market", label: "Market", Icon: BadgeDollarSign },
  ]},
  { label: "RACE CONTEXT", items: [
    { key: "results", label: "Results", Icon: Trophy },
    { key: "track", label: "Track", Icon: MapPinned },
    { key: "weather", label: "Weather", Icon: CloudSun },
    { key: "overview", label: "Overview", Icon: Gauge },
    { key: "insights", label: "Insights", Icon: Lightbulb },
  ]},
  { label: "", items: [
    { key: "settings", label: "Settings", Icon: Settings },
  ]},
];

/**
 * Canonical application brand component.
 * IMPORTANT: this is the ONE render source for the EDGEiQ sidebar identity.
 * Do not recreate the wordmark inside individual workspaces.
 *
 * The markup below preserves the original approved light-shell EDGEiQ identity
 * already present in the product. A dedicated immutable artwork asset can replace
 * this component's internals only after the exact approved source artwork is
 * recovered; consumers must continue to use this component unchanged.
 */
export function EdgeiqBrand() {
  return (
    <div className="eiq-app-nav__brand" data-edgeiq-canonical-brand="true">
      <div className="eiq-app-nav__mark" aria-hidden="true">E</div>
      <div>
        <strong>EDGE<span>iQ</span></strong>
        <em>RACING INTELLIGENCE</em>
      </div>
    </div>
  );
}

export function AppNavigation({ activeSection, onSectionChange }: AppNavigationProps) {
  return (
    <aside className="eiq-app-nav" aria-label="EDGEiQ Racing navigation">
      <EdgeiqBrand />
      <nav className="eiq-app-nav__groups">
        {navGroups.map((group, groupIndex) => (
          <section className="eiq-app-nav__group" key={`${group.label || "settings"}-${groupIndex}`} aria-label={group.label || "Settings"}>
            {group.label ? <p>{group.label}</p> : null}
            <div>
              {group.items.map(({ key, label, Icon }) => (
                <button key={key} type="button" data-edgeiq-section={key} className={activeSection === key ? "is-active" : ""} onClick={() => onSectionChange(key)}>
                  <span className="eiq-app-nav__icon" aria-hidden="true"><Icon size={16} strokeWidth={1.8} /></span>
                  <strong>{label}</strong>
                </button>
              ))}
            </div>
          </section>
        ))}
      </nav>
      <footer className="eiq-app-nav__footer"><div><span className="eiq-app-nav__live-dot" aria-hidden="true" /><strong>System online</strong></div><small>Production workspace</small></footer>
    </aside>
  );
}
