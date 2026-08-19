import { useEffect } from "react";
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
