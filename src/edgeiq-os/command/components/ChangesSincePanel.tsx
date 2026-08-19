type ChangeItem = {
  label: string;
  value: string;
  detail: string;
};

type ChangesSincePanelProps = {
  since: string;
  items: ChangeItem[];
};

export function ChangesSincePanel({ since, items }: ChangesSincePanelProps) {
  return (
    <section className="eiq-command-changes">
      <div>
        <span>Changes Since</span>
        <strong>{since}</strong>
      </div>

      {items.map((item) => (
        <article key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          <p>{item.detail}</p>
        </article>
      ))}

      <button type="button">View History</button>
    </section>
  );
}
