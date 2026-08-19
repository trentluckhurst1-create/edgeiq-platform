
export type OperationalEventSeverity = "INFO" | "IMPORTANT" | "WARNING" | "CRITICAL";

export interface OperationalEvent {
  id: string;
  time: string;
  severity: OperationalEventSeverity;
  title: string;
  detail: string;
  source: string;
}
