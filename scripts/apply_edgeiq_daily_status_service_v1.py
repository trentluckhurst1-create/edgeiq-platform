from pathlib import Path
root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

def write(rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")

status_service = '''export type EdgeiqDailyPipelineStatus = {
  status?: "READY" | "WARN" | "FAIL";
  generated_at?: string;
  melbourne_date?: string;
  window_dates?: string[];
  stages?: Array<{ name: string; status: string; detail?: string }>;
  counts?: Record<string, number>;
  last_successful_status?: EdgeiqDailyPipelineStatus | null;
};

const STATUS_URL = "/data/edgeiq_daily_pipeline_status_v1.json";
let cachedStatus: EdgeiqDailyPipelineStatus | null = null;

export async function loadEdgeiqDailyPipelineStatus(force = false): Promise<EdgeiqDailyPipelineStatus | null> {
  if (!force && cachedStatus) return cachedStatus;
  try {
    const response = await fetch(`${STATUS_URL}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" });
    if (!response.ok) return null;
    const status = (await response.json()) as EdgeiqDailyPipelineStatus;
    cachedStatus = status;
    return status;
  } catch (error) {
    console.warn("EDGEiQ daily pipeline status unavailable", error);
    return null;
  }
}
'''
write("src/edgeiq-os/services/daily-pipeline/DailyPipelineStatusService.ts", status_service)

shell = '''import { useEffect } from "react";
import { RaceFileV3 } from "../race/RaceFileV3";
import { loadEdgeiqDailyPipelineStatus } from "../services/daily-pipeline/DailyPipelineStatusService";

export function EdgeiqOsShell() {
  useEffect(() => {
    let cancelled = false;
    loadEdgeiqDailyPipelineStatus()
      .then((status) => {
        if (!cancelled && status) {
          console.info("EDGEiQ daily pipeline status", status.status, status.melbourne_date, status.window_dates);
        }
      })
      .catch((error) => console.warn("EDGEiQ daily pipeline status read failed", error));
    return () => {
      cancelled = true;
    };
  }, []);

  return <RaceFileV3 />;
}
'''
write("src/edgeiq-os/shell/EdgeiqOsShell.tsx", shell)
print("daily status service and shell read patched")
