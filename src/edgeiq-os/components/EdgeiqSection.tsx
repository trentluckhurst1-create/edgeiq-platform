import type { ReactNode } from "react";

type EdgeiqSectionProps = {
  label: string;
  children: ReactNode;
  emphasis?: boolean;
};

export function EdgeiqSection({ label, children, emphasis = false }: EdgeiqSectionProps) {
  return (
    <section className={emphasis ? "eiq-section is-emphasis" : "eiq-section"}>
      <span>{label}</span>
      {children}
    </section>
  );
}
