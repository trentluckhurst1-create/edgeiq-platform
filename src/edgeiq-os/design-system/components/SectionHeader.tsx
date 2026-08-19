type SectionHeaderProps = {
  eyebrow?: string;
  title: string;
  meta?: string;
};

export function SectionHeader({ eyebrow, title, meta }: SectionHeaderProps) {
  return (
    <header className="eiq-ds-section-header">
      <div>
        {eyebrow ? <span>{eyebrow}</span> : null}
        <h2>{title}</h2>
      </div>
      {meta ? <strong>{meta}</strong> : null}
    </header>
  );
}
