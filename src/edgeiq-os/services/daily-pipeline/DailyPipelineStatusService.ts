export type EdgeiqDailyPipelineStatus = {
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
