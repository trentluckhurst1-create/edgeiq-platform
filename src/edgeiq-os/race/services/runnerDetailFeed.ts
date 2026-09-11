import { edgeiqDataPath } from "../../../config/edgeiqDataOrigin";
import type { ThreeDayRunner } from "./threeDayCatalog";

type RunnerDetailFeed = {
  schemaVersion: string;
  generatedAt: string;
  date: string;
  meetingKey: string;
  raceKey: string;
  runnerIndex: number;
  runnerNumber: string;
  runnerName: string;
  runner: ThreeDayRunner;
};

const MAX_RUNNER_DETAIL_BYTES = 2_000_000;
const runnerCache = new Map<string, ThreeDayRunner>();
const runnerPending = new Map<string, Promise<ThreeDayRunner>>();

export async function loadRunnerDetail(path: string, force = false): Promise<ThreeDayRunner> {
  const cleanPath = String(path ?? "").trim();
  if (!cleanPath) throw new Error("Runner detail path is not supplied");
  if (!force && runnerCache.has(cleanPath)) return runnerCache.get(cleanPath)!;
  if (runnerPending.has(cleanPath)) return runnerPending.get(cleanPath)!;

  const url = edgeiqDataPath(cleanPath);
  const pending = fetch(`${url}?updated=${encodeURIComponent(String(Date.now()))}`, {
    cache: force ? "reload" : "no-store",
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Runner detail failed with ${response.status}`);
      const text = await response.text();
      if (text.length > MAX_RUNNER_DETAIL_BYTES) {
        throw new Error(`Runner detail exceeds ${MAX_RUNNER_DETAIL_BYTES} bytes`);
      }
      const payload = JSON.parse(text) as RunnerDetailFeed;
      if (!payload.runner) throw new Error("Runner detail is invalid");
      runnerCache.set(cleanPath, payload.runner);
      return payload.runner;
    })
    .finally(() => {
      runnerPending.delete(cleanPath);
    });

  runnerPending.set(cleanPath, pending);
  return pending;
}
