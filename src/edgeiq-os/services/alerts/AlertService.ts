
import type { OperationalAlert } from "./AlertTypes";

export function buildSystemAlerts(): OperationalAlert[] {
  return [
    {
      id: "os-alert-intelligence-wiring",
      category: "SYSTEM",
      title: "Integration phase active",
      summary: "EDGEiQ OS is ready for production intelligence feed wiring.",
      severity: "IMPORTANT",
    },
  ];
}
