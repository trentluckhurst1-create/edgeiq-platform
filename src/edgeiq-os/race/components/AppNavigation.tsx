import { CalendarDays, Home } from "lucide-react";

export type GlobalSection = "home" | "meetings";

type AppNavigationProps = {
  activeSection: GlobalSection;
  onSectionChange: (section: GlobalSection) => void;
};

const items = [
  { key: "home" as const, label: "Dashboard", Icon: Home },
  { key: "meetings" as const, label: "Meetings", Icon: CalendarDays },
];

export function AppNavigation({ activeSection, onSectionChange }: AppNavigationProps) {
  return (
    <aside className="eiq-app-nav" aria-label="EDGEiQ Racing navigation">
      <div className="eiq-app-nav__brand">
        <div className="eiq-app-nav__mark" aria-hidden="true">E</div>
        <div><strong>EDGE<span>iQ</span></strong><em>RACING INTELLIGENCE</em></div>
      </div>
      <nav className="eiq-app-nav__groups">
        <section className="eiq-app-nav__group" aria-label="RACE DAY">
          <p>RACE DAY</p>
          <div>
            {items.map(({ key, label, Icon }) => (
              <button key={key} type="button" data-edgeiq-section={key} className={activeSection === key ? "is-active" : ""} onClick={() => onSectionChange(key)}>
                <span className="eiq-app-nav__icon" aria-hidden="true"><Icon size={16} strokeWidth={1.8} /></span>
                <strong>{label}</strong>
              </button>
            ))}
          </div>
        </section>
      </nav>
      <footer className="eiq-app-nav__footer"><div><span className="eiq-app-nav__live-dot" aria-hidden="true" /><strong>System online</strong></div><small>Production workspace</small></footer>
    </aside>
  );
}
