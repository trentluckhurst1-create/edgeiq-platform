from __future__ import annotations

from collections import defaultdict

from edgeiq_beta_intelligence_v1_common import DATA, EARLY_SPEED, clean, load_current_projection, load_current_runners, to_float, write_json


OUT = DATA / "edgeiq_current_map_v1.json"


def zone_from_rank(rank: int | None, field_size: int) -> str:
    if rank is None:
        return "UNRESOLVED"
    pct = rank / max(1, field_size)
    if pct <= 0.18:
        return "LEAD"
    if pct <= 0.38:
        return "ON PACE"
    if pct <= 0.72:
        return "MIDFIELD"
    return "BACK"


def main() -> None:
    current = load_current_runners()
    early = load_current_projection(EARLY_SPEED, "earlySpeed")
    race_shape = load_current_projection(DATA / "edgeiq_current_race_shape_v2.json", "raceShape")
    grouped = defaultdict(list)
    for row in current:
        grouped[row["raceIdentity"]].append(row)
    runners = []
    for race_key, race_rows in grouped.items():
        ranked = sorted([(row, to_float(early.get(row["identity"], {}).get("earlySpeed"))) for row in race_rows], key=lambda item: item[1] if item[1] is not None else -999, reverse=True)
        rank_map = {row["identity"]: index + 1 for index, (row, value) in enumerate(ranked) if value is not None}
        for row in race_rows:
            erow = early.get(row["identity"], {})
            srow = race_shape.get(row["identity"], {})
            runners.append({
                "raceDate": row["raceDate"],
                "meeting": row["meeting"],
                "raceNumber": row["raceNumber"],
                "runnerId": row["runnerId"],
                "runnerNumber": row["runnerNumber"],
                "runnerName": row["runnerName"],
                "barrier": row["barrier"],
                "jockey": row["jockey"],
                "trainer": row["trainer"],
                "weight": row["weight"],
                "market": row["market"],
                "projectedZone": clean(srow.get("projectedZone")) or zone_from_rank(rank_map.get(row["identity"]), len(race_rows)),
                "projectedRank": rank_map.get(row["identity"]),
                "earlySpeed": erow.get("earlySpeed"),
                "runStyle": clean(srow.get("projectedZone")) or "",
                "raceShape": srow.get("raceShape"),
                "evidenceCoverage": srow.get("evidenceCoverage") or erow.get("evidenceCoverage"),
                "sourceVersion": "CURRENT_MAP_V1",
            })
    write_json(OUT, {"schemaVersion": "edgeiq_current_map_v1", "orientation": "Victorian: leaders left, barrier 1 bottom", "runners": runners})
    print(f"CURRENT_MAP_V1 rows={len(runners)}")


if __name__ == "__main__":
    main()
