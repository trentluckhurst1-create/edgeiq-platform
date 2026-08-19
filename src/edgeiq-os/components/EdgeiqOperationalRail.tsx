type OperationalItem = {
  label: string;
  value: string;
  detail?: string;
  tone?: "good" | "info" | "monitor" | "risk" | "neutral";
};

type EdgeiqOperationalRailProps = {
  title: string;
  items: OperationalItem[];
};

export function EdgeiqOperationalRail({ title, items }: EdgeiqOperationalRailProps) {
  return (
    <div className="eiq-ops">
      <span>Race State</span>
      <h2>{title}</h2>

      <div className="eiq-ops__items">
        {items.map((item) => (
          <div className="eiq-ops__item" key={item.label}>
            <span>{item.label}</span>
            <strong className={item.tone ? `is-${item.tone}` : undefined}>{item.value}</strong>
            {item.detail ? <p>{item.detail}</p> : null}
          </div>
        ))}
      </div>
    </div>
  );
}
