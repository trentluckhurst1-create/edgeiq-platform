from pathlib import Path
from collections import Counter, defaultdict
import csv
import datetime
import hashlib

ROOT = Path(r"C:\EDGEIQ_PLATFORM_FAST")
DATA = ROOT / "public" / "data"

RACE_ENTRIES = DATA / "edgeiq_race_entry_fact_v1.csv"
IDENTITY_BRIDGE = DATA / "edgeiq_rcom_to_eiq_horse_identity_bridge_v1.csv"
IDENTITY_EXCEPTIONS = DATA / "edgeiq_rcom_to_eiq_horse_identity_bridge_v1_exceptions.csv"
HORSE_RATINGS = DATA / "edgeiq_horse_performance_rating_fact_v1.csv"

OUTPUT = DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"
REJECTIONS = DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1_rejections.csv"

CONTRACT_VERSION = "2.1.0"
BUILDER_VERSION = "edgeiq_race_entry_horse_performance_snapshot_fact_v2.1.0"

OUTPUT_FIELDS = ['race_entry_horse_performance_snapshot_id', 'canonical_race_id', 'canonical_runner_id', 'race_date', 'canonical_horse_id', 'canonical_horse_name', 'selected_horse_performance_rating_id', 'selected_horse_performance_aggregate_id', 'selected_rating_as_of_date', 'rating_age_days', 'eligible_historical_rating_count', 'first_eligible_rating_date', 'latest_eligible_rating_date', 'selected_horse_performance_rating_value', 'highest_eligible_historical_rating_value', 'lowest_eligible_historical_rating_value', 'average_eligible_historical_rating_value', 'selected_included_observation_count', 'horse_performance_rating_method', 'race_entry_horse_performance_snapshot_status', 'identity_resolution_method', 'source_race_entry_evidence_sha256', 'source_identity_bridge_evidence_sha256', 'source_selected_rating_evidence_sha256', 'source_eligible_rating_ids_sha256', 'source_eligible_rating_evidence_sha256', 'race_entry_horse_performance_snapshot_evidence_sha256', 'source_rating_builder_version', 'builder_version', 'contract_version', 'built_at_utc']
REJECTION_FIELDS = ['race_entry_horse_performance_snapshot_rejection_id', 'canonical_race_id', 'canonical_runner_id', 'race_date', 'runner_name', 'canonical_horse_id', 'identity_resolution_status', 'rejection_reason', 'available_horse_rating_count', 'earliest_available_rating_date', 'latest_available_rating_date', 'source_race_entry_evidence_sha256', 'source_identity_evidence_sha256', 'rejection_evidence_sha256', 'builder_version', 'contract_version', 'built_at_utc']


def clean(value):
    return "" if value is None else str(value).strip()


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, fields, rows):
    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    temporary.replace(path)


def parse_date(value):
    text = clean(value)

    if not text:
        return None

    try:
        return datetime.date.fromisoformat(text[:10])
    except Exception:
        return None


def number(value):
    try:
        return float(clean(value))
    except Exception:
        return None


def fmt(value):
    return f"{float(value):.6f}"


def sha256_text(value):
    return hashlib.sha256(
        clean(value).encode("utf-8")
    ).hexdigest()


def sha256_payload(values):
    return sha256_text(
        "\x1f".join(clean(value) for value in values)
    )


def evidence(row, preferred):
    value = clean(row.get(preferred))

    if len(value) == 64:
        return value.lower()

    return sha256_payload([
        f"{key}={clean(row.get(key))}"
        for key in sorted(row)
    ])


def main():
    entries = read_csv(RACE_ENTRIES)
    bridge_rows = read_csv(IDENTITY_BRIDGE)
    exception_rows = read_csv(IDENTITY_EXCEPTIONS)
    ratings = read_csv(HORSE_RATINGS)

    bridge_by_runner = {
        clean(row.get("rcom_horse_id")): row
        for row in bridge_rows
        if clean(row.get("rcom_horse_id"))
        and clean(row.get("eiq_canonical_horse_id"))
    }

    exception_by_runner = {
        clean(row.get("rcom_horse_id")): row
        for row in exception_rows
        if clean(row.get("rcom_horse_id"))
    }

    ratings_by_horse = defaultdict(list)

    for rating in ratings:
        horse_id = clean(rating.get("canonical_horse_id"))
        rating_date = parse_date(rating.get("rating_as_of_date"))
        rating_value = number(
            rating.get("horse_performance_rating_value")
        )

        if (
            not horse_id
            or rating_date is None
            or rating_value is None
        ):
            continue

        ratings_by_horse[horse_id].append(
            (rating_date, rating_value, rating)
        )

    for horse_id in ratings_by_horse:
        ratings_by_horse[horse_id].sort(
            key=lambda item: (
                item[0],
                int(
                    clean(
                        item[2].get("included_observation_count")
                    )
                    or 0
                ),
                clean(
                    item[2].get("horse_performance_rating_id")
                ),
            )
        )

    built_at = datetime.datetime.now(
        datetime.timezone.utc
    ).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )

    accepted = []
    rejected = []

    for entry in entries:
        race_id = clean(entry.get("canonical_race_id"))
        runner_id = clean(entry.get("canonical_runner_id"))
        race_date_text = clean(entry.get("race_date"))
        race_date = parse_date(race_date_text)
        runner_name = clean(entry.get("runner_name"))

        entry_evidence = evidence(entry, "source_hash")

        def reject(
            reason,
            horse_id="",
            identity_status="",
            identity_evidence="",
            horse_ratings=None,
        ):
            horse_ratings = horse_ratings or []

            rating_dates = [
                item[0]
                for item in horse_ratings
            ]

            rejection_id = (
                "REHPSR2-"
                + sha256_payload([
                    CONTRACT_VERSION,
                    race_id,
                    runner_id,
                    race_date_text,
                    reason,
                ])[:24].upper()
            )

            rejection_evidence = sha256_payload([
                rejection_id,
                entry_evidence,
                identity_evidence,
                reason,
            ])

            rejected.append({
                "race_entry_horse_performance_snapshot_rejection_id":
                    rejection_id,
                "canonical_race_id": race_id,
                "canonical_runner_id": runner_id,
                "race_date": race_date_text,
                "runner_name": runner_name,
                "canonical_horse_id": horse_id,
                "identity_resolution_status": identity_status,
                "rejection_reason": reason,
                "available_horse_rating_count":
                    len(horse_ratings),
                "earliest_available_rating_date":
                    min(rating_dates).isoformat()
                    if rating_dates else "",
                "latest_available_rating_date":
                    max(rating_dates).isoformat()
                    if rating_dates else "",
                "source_race_entry_evidence_sha256":
                    entry_evidence,
                "source_identity_evidence_sha256":
                    identity_evidence,
                "rejection_evidence_sha256":
                    rejection_evidence,
                "builder_version": BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": built_at,
            })

        if not race_id or not runner_id or race_date is None:
            reject(
                "RACE_ENTRY_REQUIRED_FIELD_INVALID",
                identity_status="INVALID_RACE_ENTRY",
            )
            continue

        if runner_id in exception_by_runner:
            exception = exception_by_runner[runner_id]

            reject(
                "IDENTITY_EXCEPTION",
                identity_status=clean(
                    exception.get("resolution_status")
                ) or "IDENTITY_EXCEPTION",
                identity_evidence=evidence(
                    exception,
                    "evidence_reference",
                ),
            )
            continue

        bridge = bridge_by_runner.get(runner_id)

        if bridge is None:
            reject(
                "IDENTITY_BRIDGE_NOT_FOUND",
                identity_status="UNRESOLVED",
            )
            continue

        horse_id = clean(
            bridge.get("eiq_canonical_horse_id")
        )

        identity_evidence = evidence(
            bridge,
            "evidence_sha256",
        )

        horse_ratings = ratings_by_horse.get(
            horse_id,
            [],
        )

        if not horse_ratings:
            reject(
                "NO_GOVERNED_HORSE_RATING",
                horse_id=horse_id,
                identity_status=clean(
                    bridge.get("resolution_status")
                ) or "RESOLVED",
                identity_evidence=identity_evidence,
            )
            continue

        eligible = [
            item
            for item in horse_ratings
            if item[0] <= race_date
        ]

        if not eligible:
            reject(
                "NO_POINT_IN_TIME_ELIGIBLE_HORSE_RATING",
                horse_id=horse_id,
                identity_status=clean(
                    bridge.get("resolution_status")
                ) or "RESOLVED",
                identity_evidence=identity_evidence,
                horse_ratings=horse_ratings,
            )
            continue

        selected_date, selected_value, selected = eligible[-1]

        eligible_values = [
            item[1]
            for item in eligible
        ]

        eligible_ids = [
            clean(
                item[2].get("horse_performance_rating_id")
            )
            for item in eligible
        ]

        eligible_evidence = [
            evidence(
                item[2],
                "horse_performance_rating_evidence_sha256",
            )
            for item in eligible
        ]

        selected_evidence = evidence(
            selected,
            "horse_performance_rating_evidence_sha256",
        )

        eligible_ids_hash = sha256_payload(
            sorted(eligible_ids)
        )

        eligible_evidence_hash = sha256_payload(
            sorted(eligible_evidence)
        )

        snapshot_id = (
            "REHPS2-"
            + sha256_payload([
                CONTRACT_VERSION,
                race_id,
                runner_id,
                race_date_text,
            ])[:24].upper()
        )

        rating_age_days = (
            race_date - selected_date
        ).days

        snapshot_evidence = sha256_payload([
            snapshot_id,
            entry_evidence,
            identity_evidence,
            selected_evidence,
            eligible_ids_hash,
            eligible_evidence_hash,
            selected_value,
            rating_age_days,
        ])

        accepted.append({
            "race_entry_horse_performance_snapshot_id":
                snapshot_id,
            "canonical_race_id": race_id,
            "canonical_runner_id": runner_id,
            "race_date": race_date_text,
            "canonical_horse_id": horse_id,
            "canonical_horse_name": clean(
                selected.get("canonical_horse_name")
            ),
            "selected_horse_performance_rating_id":
                clean(
                    selected.get(
                        "horse_performance_rating_id"
                    )
                ),
            "selected_horse_performance_aggregate_id":
                clean(
                    selected.get(
                        "horse_performance_aggregate_id"
                    )
                ),
            "selected_rating_as_of_date":
                selected_date.isoformat(),
            "rating_age_days": rating_age_days,
            "eligible_historical_rating_count":
                len(eligible),
            "first_eligible_rating_date":
                eligible[0][0].isoformat(),
            "latest_eligible_rating_date":
                eligible[-1][0].isoformat(),
            "selected_horse_performance_rating_value":
                fmt(selected_value),
            "highest_eligible_historical_rating_value":
                fmt(max(eligible_values)),
            "lowest_eligible_historical_rating_value":
                fmt(min(eligible_values)),
            "average_eligible_historical_rating_value":
                fmt(
                    sum(eligible_values)
                    / len(eligible_values)
                ),
            "selected_included_observation_count":
                clean(
                    selected.get(
                        "included_observation_count"
                    )
                ),
            "horse_performance_rating_method":
                clean(
                    selected.get(
                        "horse_performance_rating_method"
                    )
                ),
            "race_entry_horse_performance_snapshot_status":
                "POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE",
            "identity_resolution_method":
                clean(
                    bridge.get("resolution_method")
                ) or "GOVERNED_RCOM_TO_EIQ_BRIDGE",
            "source_race_entry_evidence_sha256":
                entry_evidence,
            "source_identity_bridge_evidence_sha256":
                identity_evidence,
            "source_selected_rating_evidence_sha256":
                selected_evidence,
            "source_eligible_rating_ids_sha256":
                eligible_ids_hash,
            "source_eligible_rating_evidence_sha256":
                eligible_evidence_hash,
            "race_entry_horse_performance_snapshot_evidence_sha256":
                snapshot_evidence,
            "source_rating_builder_version":
                clean(
                    selected.get("builder_version")
                ),
            "builder_version": BUILDER_VERSION,
            "contract_version": CONTRACT_VERSION,
            "built_at_utc": built_at,
        })

    accepted.sort(
        key=lambda row: (
            row["race_date"],
            row["canonical_race_id"],
            row["canonical_runner_id"],
        )
    )

    rejected.sort(
        key=lambda row: (
            row["race_date"],
            row["canonical_race_id"],
            row["canonical_runner_id"],
        )
    )

    write_csv(OUTPUT, OUTPUT_FIELDS, accepted)
    write_csv(REJECTIONS, REJECTION_FIELDS, rejected)

    print(
        "EDGEIQ_RACE_ENTRY_HORSE_PERFORMANCE_"
        "SNAPSHOT_FACT_V2_1_BUILD_PASS"
    )
    print(f"race_entry_rows={len(entries)}")
    print(f"identity_bridge_rows={len(bridge_rows)}")
    print(f"identity_exception_rows={len(exception_rows)}")
    print(f"horse_rating_rows={len(ratings)}")
    print(f"accepted_snapshot_rows={len(accepted)}")
    print(f"rejection_rows={len(rejected)}")

    reasons = Counter(
        row["rejection_reason"]
        for row in rejected
    )

    for reason, count in sorted(reasons.items()):
        print(f"rejection[{reason}]={count}")

    print(f"output={OUTPUT}")
    print(f"rejections={REJECTIONS}")


if __name__ == "__main__":
    main()
