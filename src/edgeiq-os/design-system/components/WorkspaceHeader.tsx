type WorkspaceHeaderProps = {
  eyebrow: string;
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
};

export function WorkspaceHeader({ eyebrow, title, subtitle, children }: WorkspaceHeaderProps) {
  return (
    <header className="eiq-ds-workspace-header">
      <div>
        <span>{eyebrow}</span>
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {children ? <div className="eiq-ds-workspace-header__aside">{children}</div> : null}
    </header>
  );
}
