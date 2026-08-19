
import { buildOperationalRaceState } from "../operational-state";
import type { OperationalRaceState } from "../operational-state";

export function getOperationalRaceState(): OperationalRaceState {
  return buildOperationalRaceState();
}
