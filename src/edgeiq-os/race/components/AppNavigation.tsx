import {
  BadgeDollarSign, CalendarDays, CloudSun, Crosshair, Gauge, Home, Lightbulb, LineChart,
  Map, MapPinned, SlidersHorizontal, Trophy, ClipboardList,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type GlobalSection =
  | "home" | "meetings" | "race" | "formGuide" | "performance" | "epi" | "map"
  | "market" | "results" | "track" | "weather" | "overview" | "insights";

type AppNavigationProps = { activeSection: GlobalSection; onSectionChange: (section: GlobalSection) => void; };
type NavItem = { key: GlobalSection; label: string; Icon: LucideIcon };
type NavGroup = { label: string; items: NavItem[] };

const navGroups: NavGroup[] = [
  { label: "RACE DAY", items: [
    { key: "home", label: "Dashboard", Icon: Home },
    { key: "meetings", label: "Meetings", Icon: CalendarDays },
    { key: "race", label: "Race", Icon: Crosshair },
  ]},
  { label: "INTELLIGENCE", items: [
    { key: "performance", label: "Performance", Icon: SlidersHorizontal },
    { key: "formGuide", label: "Form", Icon: ClipboardList },
    { key: "map", label: "Map", Icon: Map },
    { key: "epi", label: "Nexus", Icon: LineChart },
    { key: "market", label: "Market", Icon: BadgeDollarSign },
  ]},
  { label: "RACE CONTEXT", items: [
    { key: "results", label: "Results", Icon: Trophy },
    { key: "track", label: "Track", Icon: MapPinned },
    { key: "weather", label: "Weather", Icon: CloudSun },
    { key: "overview", label: "Overview", Icon: Gauge },
    { key: "insights", label: "Insights", Icon: Lightbulb },
  ]},
];

export function EdgeiqBrand() {
  return <div className="eiq-app-nav__brand eiq-wordmark" data-edgeiq-canonical-brand="true" aria-label="EDGEiQ">EDGE<span>iQ</span></div>;
}

export function AppNavigation({ activeSection, onSectionChange }: AppNavigationProps) {
  return <aside className="eiq-app-nav" aria-label="EDGEiQ Racing navigation">
    <EdgeiqBrand />
    <nav className="eiq-app-nav__groups">{navGroups.map((group, groupIndex) => <section className="eiq-app-nav__group" key={`${group.label}-${groupIndex}`} aria-label={group.label}>
      <p>{group.label}</p><div>{group.items.map(({ key, label, Icon }) => <button key={key} type="button" data-edgeiq-section={key} className={activeSection === key ? "is-active" : ""} onClick={() => onSectionChange(key)}><span className="eiq-app-nav__icon" aria-hidden="true"><Icon size={16} strokeWidth={1.8} /></span><strong>{label}</strong></button>)}</div>
    </section>)}</nav>
    <footer className="eiq-app-nav__footer"><div><span className="eiq-app-nav__live-dot" aria-hidden="true" /><strong>System online</strong></div><small>Production workspace</small></footer>
  </aside>;
}
