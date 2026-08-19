type BriefSectionProps = {
  label: string;
  title?: string;
  body: string;
  action?: string;
};

export function BriefSection({ label, title, body, action }: BriefSectionProps) {
  return (
    <section className="eiq-ds-brief">
      <span>{label}</span>
      {title ? <h2>{title}</h2> : null}
      <p>{body}</p>
      {action ? <b>{action}</b> : null}
    </section>
  );
}
