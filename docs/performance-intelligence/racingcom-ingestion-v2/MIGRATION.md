# Migration

Current migration decision: `DO_NOT_MIGRATE_YET`.

V2 is safe for governed historical warehouse production of the eight proven CSV files, but migration is held because no fresh CSV links were observed during page discovery.

Next migration gate:

1. Identify timestamp/current Racing.com speed-data CSV discovery mechanism without URL fabrication.
2. Add replay-safe discovery evidence.
3. Re-run the E2E regression gate.
4. Only then patch orchestration in a separate governed unit.
