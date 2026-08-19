type TimelineItem = {
  id: string;
  time: string;
  title: string;
  summary: string;
};

type TimelineSectionProps = {
  title: string;
  items: TimelineItem[];
};

export function TimelineSection({ title, items }: TimelineSectionProps) {
  return (
    <section className="eiq-ds-timeline">
      <h2>{title}</h2>
      {items.map((item) => (
        <article key={item.id}>
          <span>{item.time}</span>
          <strong>{item.title}</strong>
          <p>{item.summary}</p>
        </article>
      ))}
    </section>
  );
}
