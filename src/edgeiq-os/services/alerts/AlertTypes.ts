
export type OperationalAlertSeverity = "INFO" | "WATCH" | "IMPORTANT" | "CRITICAL";

export interface OperationalAlert {
  id: string;
  category:
    | "SYSTEM"
    | "MARKET"
    | "TRACK"
    | "WEATHER"
    | "PACE"
    | "RUNNER"
    | "CONNECTION"
    | "SECTIONAL";
  title: string;
  summary: string;
  severity: OperationalAlertSeverity;
}
