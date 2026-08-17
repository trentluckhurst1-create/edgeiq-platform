import { EiqCard, EiqPanel, EiqSectionHeader, PageFrame, PageHeader } from "../../design-system/v1";

const settingsSections = [
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
    <PageFrame
      className="eiq-settings-v2 eiq-settings-final"
      data-edgeiq-workspace-key="SETTINGS"
      data-edgeiq-mounted-component="SettingsWorkspace"
    >
      <PageHeader
        eyebrow="SETTINGS"
        title="Product settings and data boundaries"
        description="Configuration surface for what is currently connected. Nothing here changes model outputs or production calculations."
      />

      <div className="eiq-settings-final__grid">
        {settingsSections.map((section) => (
          <EiqCard className="eiq-settings-final-card" key={section.title}>
            <EiqSectionHeader title={section.title} />
            <dl className="eiq-v1-side-facts">
              {section.rows.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </EiqCard>
        ))}
      </div>

      <EiqPanel className="eiq-settings-final-card eiq-settings-final__boundary">
        <EiqSectionHeader eyebrow="Boundary" title="Settings are display and governance only." />
        <p className="eiq-v1-analytical-copy">Pricing, EPI, ERI, EPF, weather freshness and performance intelligence calculations remain owned by their existing services and builders.</p>
      </EiqPanel>
    </PageFrame>
  );
}
