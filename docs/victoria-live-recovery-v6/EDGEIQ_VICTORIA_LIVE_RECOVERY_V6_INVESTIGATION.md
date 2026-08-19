# EDGEIQ Victoria Live Recovery V6 Investigation

{
  "epi": {
    "current_runners_missing_epi": 5,
    "distinct_current_runners_with_epi": 51,
    "epi_status": "EPI_POPULATED",
    "input_component_rows": 153,
    "missing_reasons": {
      "MISSING_REQUIRED_EPI_COMPONENT": 5
    },
    "output_epi_rows": 51
  },
  "historical_normalisation": {
    "accepted_rows": 52320,
    "ambiguous_identities": 104,
    "approved_identities": 52320,
    "distinct_historical_horses": 29955,
    "earliest_performance_date": "2000-08-02",
    "eligible_rows": 52320,
    "formula_status": "FORMULA_UNCHANGED",
    "formula_version": "HPR-NORM-A",
    "horse_observation_rows": 52320,
    "identity_rejection_rows": 105,
    "latest_performance_date": "2026-07-30",
    "normalisation_rows": 52320,
    "performance_base_rows": 52425,
    "performance_rating_base_rows": 52320,
    "policy_id": "HPR-NORM-A-v2",
    "rejected_rows": 105,
    "rejection_reasons": {
      "IDENTITY_AMBIGUOUS": 104,
      "IDENTITY_UNRESOLVED": 1
    },
    "unresolved_identities": 1
  },
  "horse_aggregates": {
    "depth_distribution": {
      "1 observation": 17758,
      "10-19 observations": 21,
      "2 observations": 6685,
      "3 observations": 2939,
      "4 observations": 1434,
      "5-9 observations": 1118
    },
    "distinct_horses": 29955,
    "distinct_rated_horses": 734,
    "horses_below_threshold": 28816,
    "horses_meeting_threshold": 1139,
    "input_observations": 52320,
    "latest_rating_date": "2026-06-13",
    "maximum_observation_depth": 13,
    "median_observation_depth": 1,
    "minimum_observations": 5,
    "output_aggregates": 1265,
    "output_ratings": 1265
  },
  "policy": {
    "approved_from_date": "2026-07-30",
    "backfill_execution_timestamp": "2026-07-30T00:00:00Z",
    "centre_value": "-0.193589",
    "formula_status": "FORMULA_UNCHANGED",
    "formula_version": "HPR-NORM-A",
    "historical_backfill_authorised": true,
    "historical_eligibility_from_date": "2001-01-01",
    "minimum_observations_changed": false,
    "normalisation_method": "LINEAR_CENTRE_AND_SCALE",
    "policy_evidence_sha256": "2a145468c8dc6b7130cd08e08e063bd31ab9d434af5f7bdf05e0002d699b2738",
    "policy_id": "HPR-NORM-A-v2",
    "policy_version": "HPR-NORM-A-v2",
    "scale_value": "1.637342",
    "source_hpr_norm_a_v1_parameter_evidence_sha256": "4f78130be693dc4392e15358270863b3fbdb1b8acd9f7b487704ea0b3aae8131",
    "source_hpr_norm_a_v1_parameter_id": "PNP1-857E573537B32FF28FD6F5E6",
    "supersedes_policy_id": "HPR-NORM-A-v1"
  },
  "rollback": {
    "public/data/edgeiq_horse_performance_aggregate_fact_v1.csv": {
      "backup": "docs/victoria-live-recovery-v6/rollback/edgeiq_horse_performance_aggregate_fact_v1.csv.pre_v6",
      "exists": true,
      "sha256": "df474fd7441ba4653479532bfe43e349a115f435f38beb6da7708c8db9c861f1"
    },
    "public/data/edgeiq_horse_performance_observation_fact_v1.csv": {
      "backup": "docs/victoria-live-recovery-v6/rollback/edgeiq_horse_performance_observation_fact_v1.csv.pre_v6",
      "exists": true,
      "sha256": "1553d705377079f2c95f7574dc6cff2350939b013b2a7bc540a94a93bec04a78"
    },
    "public/data/edgeiq_horse_performance_observation_fact_v1_rejections.csv": {
      "backup": "docs/victoria-live-recovery-v6/rollback/edgeiq_horse_performance_observation_fact_v1_rejections.csv.pre_v6",
      "exists": true,
      "sha256": "f881d896052ee8fa6464c581ac5d3ddba8b18fbbc2e57f45f72fe032cf053e30"
    },
    "public/data/edgeiq_horse_performance_rating_fact_v1.csv": {
      "backup": "docs/victoria-live-recovery-v6/rollback/edgeiq_horse_performance_rating_fact_v1.csv.pre_v6",
      "exists": true,
      "sha256": "ef35d238b7e250ba7a88d14c84439cba4ba4498c2e4bd1d201270e9e19c64891"
    },
    "public/data/edgeiq_performance_normalisation_fact_v1.csv": {
      "backup": "docs/victoria-live-recovery-v6/rollback/edgeiq_performance_normalisation_fact_v1.csv.pre_v6",
      "exists": true,
      "sha256": "3b723270e2ade533f5402ee34736705c2aa69685a582afe63e2fca0b8c04f4d8"
    },
    "public/data/edgeiq_performance_normalisation_fact_v1_rejections.csv": {
      "backup": "docs/victoria-live-recovery-v6/rollback/edgeiq_performance_normalisation_fact_v1_rejections.csv.pre_v6",
      "exists": true,
      "sha256": "6bdbe9be14566facba6a922b62a78d1d7c91fb23d1892e4880612053b86c4119"
    },
    "public/data/edgeiq_performance_rating_base_fact_v1.csv": {
      "backup": "docs/victoria-live-recovery-v6/rollback/edgeiq_performance_rating_base_fact_v1.csv.pre_v6",
      "exists": true,
      "sha256": "2026fc7fd6e8a8fcceb37ab02fef2b5213f6b605f9935c6868a6cd448578036f"
    },
    "public/data/edgeiq_race_entry_epi_component_fact_v1.csv": {
      "backup": "docs/victoria-live-recovery-v6/rollback/edgeiq_race_entry_epi_component_fact_v1.csv.pre_v6",
      "exists": true,
      "sha256": "5ce7ec2c542e591c1fe4a0ec3786bfa4cd2c3a1caa5a76d3a24145530ad17069"
    },
    "public/data/edgeiq_race_entry_epi_fact_v1.csv": {
      "backup": "docs/victoria-live-recovery-v6/rollback/edgeiq_race_entry_epi_fact_v1.csv.pre_v6",
      "exists": true,
      "sha256": "0418d4d0fb0517c54633d4bd6b1886f825192267687ae1575047105dc6450bda"
    },
    "public/data/edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv": {
      "backup": "docs/victoria-live-recovery-v6/rollback/edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv.pre_v6",
      "exists": true,
      "sha256": "9b654869e37171764ab7f1ef138305e22dc36bbebaa0976e2833f11287b342f0"
    }
  },
  "sale": {
    "chigurh": {
      "aggregate_available": "NO",
      "blocking_reason": "INSUFFICIENT_OBSERVATIONS",
      "canonical_horse_id": "RA_HORSE_34054013730",
      "current_observations": "0",
      "epi_available": "NO",
      "historical_observations": "0",
      "race_number": "3",
      "rating_available": "NO",
      "runner_name": "CHIGURH",
      "snapshot_available": "NO",
      "total_governed_observations": "0"
    },
    "current_sale_runners": 80,
    "governed_identities": 80,
    "runners_with_5_plus_observations": 0,
    "runners_with_aggregates": 0,
    "runners_with_epi": 0,
    "runners_with_historical_observations": 0,
    "runners_with_ratings": 0,
    "runners_with_snapshots": 0
  },
  "snapshots": {
    "distinct_snapshot_horses": 5,
    "input_ratings": 1265,
    "latest_snapshot_date": "2026-07-25",
    "missing_snapshot_reasons": {
      "NO_PRIOR_HORSE_RATING": 199
    },
    "output_snapshots": 5,
    "race_entry_rows": 204
  }
}
