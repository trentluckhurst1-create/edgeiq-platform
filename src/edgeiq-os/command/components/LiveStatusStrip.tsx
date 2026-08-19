type LiveStatusItem = {
  label: string;
  value: string;
  tone: string;
};

type LiveStatusStripProps = {
  items: LiveStatusItem[];
};

export function LiveStatusStrip({ items }: LiveStatusStripProps) {
  return (
    <section className="eiq-command-live__strip">
      <div className="eiq-command-live__live-dot">● LIVE</div>
      {items.map((item) => (
        <div key={item.label}>
          <span>{item.label}</span>
          <strong className={`is-${item.tone}`}>{item.value}</strong>
        </div>
      ))}
    </section>
  );
}
