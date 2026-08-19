from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HOME = r'''import { buildMissionControlModel } from "../services/mission-control";

const mission = buildMissionControlModel();

const platformStats = [
  { label: "Meetings", value: String(mission.meetingCount), detail: "Current product window" },
  { label: "Races", value: String(mission.raceCount), detail: "Loaded race contexts" },
  { label: "Runners", value: String(mission.runnerCount), detail: "Current race evidence rows" },
  { label: "Weather", value: mission.weatherWatch.label || "Unavailable", detail: mission.weatherWatch.value || "No rail detail supplied" },
];

const workspaceItems = [
  { label: "Meetings", detail: "Open the governed meeting calendar and race list." },
  { label: "Form Guide", detail: "Inspect field, profiles, gear, prices and recent runs." },
  { label: "Map", detail: "Read the expected race shape and settling positions." },
  { label: "Market", detail: "Review live market fields where supplied." },
  { label: "Results", detail: "Open supplied results and post-race records." },
  { label: "Lab", detail: "Run governed research queries from compact product feeds." },
];

export function EdgeiqOsHome() {
  return (
    <section className="eiq-home-final">
      <header className="eiq-home-final__hero">
        <div>
          <span>EDGEIQ OS</span>
          <strong>Race intelligence workspace</strong>
          <p>
            A single governed workspace for meetings, form, map, market, results and research.
            The interface shows available data and leaves unavailable values clearly marked.
          </p>
        </div>
        <aside>
          <span>Theme</span>
          <strong>Light workspace locked</strong>
          <p>White surfaces, dark text and restrained blue accents.</p>
        </aside>
      </header>

      <section className="eiq-home-final__stats">
        {platformStats.map((item) => (
          <article key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <p>{item.detail}</p>
          </article>
        ))}
      </section>

      <section className="eiq-home-final-panel">
        <header>
          <span>Workspaces</span>
          <strong>Current product flow</strong>
        </header>
        <div className="eiq-home-final__workspaces">
          {workspaceItems.map((item) => (
            <article key={item.label}>
              <b>{item.label}</b>
              <p>{item.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="eiq-home-final-panel">
        <header>
          <span>Data Discipline</span>
          <strong>Browser-safe product feeds</strong>
        </header>
        <ul className="eiq-home-final__rules">
          <li>Warehouse-scale data remains behind builders and services.</li>
          <li>Current workspaces render compact governed feeds only.</li>
          <li>Unavailable values remain visible as unavailable rather than being filled by assumption.</li>
        </ul>
      </section>
    </section>
  );
}
'''

SETTINGS = r'''const settingsSections = [
  {
    title: "Display",
    rows: [
      ["Theme", "Light workspace locked"],
      ["Tables", "Compact racing form layout"],
      ["Contrast", "Dark text on white surfaces"],
    ],
  },
  {
    title: "Data",
    rows: [
      ["Browser feeds", "Compact governed feeds only"],
      ["Warehouse data", "Backend builders only"],
      ["Unavailable values", "Shown honestly"],
    ],
  },
  {
    title: "Weather",
    rows: [
      ["Source state", "Builder-owned"],
      ["Freshness", "Service supplied"],
      ["Timestamps", "Preserved from live feed"],
    ],
  },
  {
    title: "Review",
    rows: [
      ["Saved records", "Not connected"],
      ["Result analysis", "Requires supplied result"],
      ["User notes", "Not stored in this build"],
    ],
  },
];

export function SettingsWorkspace() {
  return (
    <section className="eiq-settings-final">
      <header className="eiq-settings-final__header">
        <div>
          <span>SETTINGS</span>
          <strong>Product settings and data boundaries</strong>
          <p>Configuration surface for what is currently connected. Nothing here changes model outputs or production calculations.</p>
        </div>
      </header>

      <div className="eiq-settings-final__grid">
        {settingsSections.map((section) => (
          <article className="eiq-settings-final-card" key={section.title}>
            <span>{section.title}</span>
            <dl>
              {section.rows.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </div>

      <section className="eiq-settings-final-card eiq-settings-final__boundary">
        <span>Boundary</span>
        <strong>Settings are display and governance only.</strong>
        <p>Pricing, EPI, ERI, EPF, weather freshness and performance intelligence calculations remain owned by their existing services and builders.</p>
      </section>
    </section>
  );
}
'''

CSS = r'''

/* EDGEIQ HOME AND SETTINGS FINAL SPEC V1 */
.eiq-home-final,
.eiq-settings-final {
  display: grid;
  gap: 16px;
  color: var(--edgeiq-text-primary, #172033);
}

.eiq-home-final__hero,
.eiq-home-final-panel,
.eiq-home-final__stats article,
.eiq-settings-final__header,
.eiq-settings-final-card {
  background: var(--edgeiq-surface, #ffffff);
  border: 1px solid var(--edgeiq-border, #d9e2ec);
  border-radius: 14px;
  box-shadow: 0 10px 28px rgba(15, 31, 48, 0.06);
}

.eiq-home-final__hero,
.eiq-settings-final__header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  padding: 22px;
}

.eiq-home-final__hero span,
.eiq-home-final-panel > header span,
.eiq-home-final__stats span,
.eiq-settings-final__header span,
.eiq-settings-final-card > span {
  display: block;
  color: var(--edgeiq-primary, #1167b1);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-home-final__hero strong,
.eiq-settings-final__header strong {
  display: block;
  margin-top: 8px;
  color: var(--edgeiq-text-primary, #172033);
  font-size: 28px;
}

.eiq-home-final__hero p,
.eiq-home-final-panel p,
.eiq-home-final__stats p,
.eiq-settings-final__header p,
.eiq-settings-final-card p {
  margin: 8px 0 0;
  color: var(--edgeiq-text-secondary, #5f6f82);
  line-height: 1.45;
}

.eiq-home-final__hero aside {
  border-left: 1px solid var(--edgeiq-border, #d9e2ec);
  padding-left: 18px;
}

.eiq-home-final__hero aside strong {
  font-size: 18px;
}

.eiq-home-final__stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.eiq-home-final__stats article,
.eiq-home-final-panel,
.eiq-settings-final-card {
  padding: 16px;
}

.eiq-home-final__stats strong {
  display: block;
  margin-top: 7px;
  font-size: 22px;
  color: var(--edgeiq-text-primary, #172033);
}

.eiq-home-final-panel > header strong,
.eiq-settings-final-card > strong {
  display: block;
  margin-top: 6px;
  color: var(--edgeiq-text-primary, #172033);
  font-size: 18px;
}

.eiq-home-final__workspaces {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.eiq-home-final__workspaces article {
  border: 1px solid var(--edgeiq-border, #d9e2ec);
  border-radius: 12px;
  padding: 12px;
  background: var(--edgeiq-page-bg, #f5f8fb);
}

.eiq-home-final__workspaces b {
  color: var(--edgeiq-text-primary, #172033);
}

.eiq-home-final__rules {
  display: grid;
  gap: 8px;
  margin: 14px 0 0;
  padding-left: 18px;
  color: var(--edgeiq-text-primary, #172033);
}

.eiq-settings-final__header {
  grid-template-columns: 1fr;
}

.eiq-settings-final__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.eiq-settings-final-card dl {
  display: grid;
  margin: 12px 0 0;
}

.eiq-settings-final-card dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--edgeiq-border, #d9e2ec);
}

.eiq-settings-final-card dl div:last-child {
  border-bottom: 0;
}

.eiq-settings-final-card dt {
  color: var(--edgeiq-text-secondary, #5f6f82);
}

.eiq-settings-final-card dd {
  margin: 0;
  color: var(--edgeiq-text-primary, #172033);
  font-weight: 800;
  text-align: right;
}

.eiq-settings-final__boundary {
  max-width: 760px;
}

@media (max-width: 1100px) {
  .eiq-home-final__hero,
  .eiq-home-final__stats,
  .eiq-home-final__workspaces,
  .eiq-settings-final__grid {
    grid-template-columns: 1fr;
  }

  .eiq-home-final__hero aside {
    border-left: 0;
    border-top: 1px solid var(--edgeiq-border, #d9e2ec);
    padding: 14px 0 0;
  }
}
'''

AUDIT = r'''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
home = ROOT / "src/edgeiq-os/home/EdgeiqOsHome.tsx"
settings = ROOT / "src/edgeiq-os/race/components/SettingsWorkspace.tsx"
race = ROOT / "src/edgeiq-os/race/RaceFileV3.tsx"
css = ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css"

def fail(message: str) -> None:
    raise SystemExit(f"EDGEIQ_HOME_SETTINGS_FINAL_SPEC_AUDIT_FAIL: {message}")

home_text = home.read_text(encoding="utf-8")
settings_text = settings.read_text(encoding="utf-8")
race_text = race.read_text(encoding="utf-8")
css_text = css.read_text(encoding="utf-8")

for token in ["Race intelligence workspace", "Workspaces", "Data Discipline", "Browser-safe product feeds"]:
    if token not in home_text:
        fail(f"missing home token {token}")

for token in ["Product settings and data boundaries", "Settings are display and governance only", "Light workspace locked"]:
    if token not in settings_text:
        fail(f"missing settings token {token}")

if "EdgeiqOsHome" not in race_text or "activeSection === \"home\"" not in race_text:
    fail("HOME is not routed through RaceFileV3")

for token in ["Confidence", "confidence", "tip", "bet", "mock", "demo", "fake", "dark workspace", "not yet connected"]:
    if token in home_text or token in settings_text:
        fail(f"rejected home/settings token remains {token}")

if "EDGEIQ HOME AND SETTINGS FINAL SPEC V1" not in css_text:
    fail("missing home/settings css marker")

report = ROOT / "docs/full-product-implementation/EDGEIQ_HOME_SETTINGS_FINAL_SPEC_V1_AUDIT.md"
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(
    "\n".join(
        [
            "# EDGEiQ Home And Settings Final Spec V1 Audit",
            "",
            "Status: EDGEIQ_HOME_SETTINGS_FINAL_SPEC_AUDIT_PASS",
            "",
            "- HOME renders the product operating hub instead of falling through to meetings.",
            "- Rejected Home confidence copy removed.",
            "- SETTINGS no longer renders a disconnected placeholder.",
            "- Settings surface is display and governance only.",
            "- White theme styling is present.",
            "",
        ]
    ),
    encoding="utf-8",
)
print("EDGEIQ_HOME_SETTINGS_FINAL_SPEC_AUDIT_PASS")
'''

def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")

def append_once(path: str, marker: str, text: str) -> None:
    target = ROOT / path
    current = target.read_text(encoding="utf-8")
    if marker not in current:
        target.write_text(current.rstrip() + "\n" + text.lstrip(), encoding="utf-8")

def patch_race_file() -> None:
    target = ROOT / "src/edgeiq-os/race/RaceFileV3.tsx"
    text = target.read_text(encoding="utf-8")
    if 'import { EdgeiqOsHome } from "../home/EdgeiqOsHome";' not in text:
        text = text.replace('import { SettingsWorkspace } from "./components/SettingsWorkspace";\n', 'import { SettingsWorkspace } from "./components/SettingsWorkspace";\nimport { EdgeiqOsHome } from "../home/EdgeiqOsHome";\n')
    old = '''      {activeSection === "results" ? (
        <GlobalResultsWorkspace meeting={selectedMeeting} />
      ) : activeSection === "lab" ? (
'''
    new = '''      {activeSection === "home" ? (
        <EdgeiqOsHome />
      ) : activeSection === "results" ? (
        <GlobalResultsWorkspace meeting={selectedMeeting} />
      ) : activeSection === "lab" ? (
'''
    if old not in text:
        raise RuntimeError("RaceFileV3 render branch not found.")
    target.write_text(text.replace(old, new), encoding="utf-8")

write("src/edgeiq-os/home/EdgeiqOsHome.tsx", HOME)
write("src/edgeiq-os/race/components/SettingsWorkspace.tsx", SETTINGS)
append_once("src/edgeiq-os/styles/edgeiqOsV2.css", "EDGEIQ HOME AND SETTINGS FINAL SPEC V1", CSS)
write("scripts/audit_edgeiq_home_settings_final_spec_v1.py", AUDIT)
patch_race_file()

print("EDGEIQ_HOME_SETTINGS_FINAL_SPEC_APPLIED")
