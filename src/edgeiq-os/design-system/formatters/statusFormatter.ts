export function formatIntelligenceStatus(status: string): string {
  if (status === "READY") return "Assessment Complete";
  if (status === "PARTIAL") return "Building Assessment";
  if (status === "PLACEHOLDER") return "Awaiting Intelligence";
  if (status === "ERROR") return "Intelligence Unavailable";
  return status;
}
