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
