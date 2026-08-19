type ReportSectionProps = {
  label: string;
  title: string;
  body: string;
  footer?: React.ReactNode;
};

export function ReportSection({ label, title, body, footer }: ReportSectionProps) {
  return (
    <section className="eiq-ds-report">
      <span>{label}</span>
      <h3>{title}</h3>
      <p>{body}</p>
      {footer ? <div className="eiq-ds-report__footer">{footer}</div> : null}
    </section>
  );
}
