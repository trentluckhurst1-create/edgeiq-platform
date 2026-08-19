# EDGEIQ Performance Intelligence

## Phase 1A.4.1 Exact Schema and Field Mapping V1

- Program ID: `EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1A_4_1_EXACT_SCHEMA_FIELD_MAPPING_V1`
- Generated UTC: `2026-07-27T03:34:39+00:00`
- Overall status: **PASS**

## Dataset Schemas

### PERFORMANCE_WAREHOUSE_V1

- Fields: 32

| Position | Field | Type | Nonblank Rate | Samples |
|---:|---|---|---:|---|
| 1 | `canonical_performance_id` | CODE_OR_ID | 1.0 | EIQ_PERFORMANCE_5C5588BA701CFE5C // EIQ_PERFORMANCE_CA13D8100047D9D8 // EIQ_PERFORMANCE_19061354CDD77154 // EIQ_PERFORMANCE_2F0040BD282A0933 // EIQ_PERFORMANCE_ |
| 2 | `canonical_race_id` | CODE_OR_ID | 1.0 | EIQ_RACE_162CAACA9FFCD4E2 // EIQ_RACE_638BD84989E0FD2B // EIQ_RACE_9F5E835472B1308D // EIQ_RACE_A3EF7EC2B622E0CB // EIQ_RACE_593E705699ABCF4C // EIQ_RACE_EE44FD |
| 3 | `canonical_meeting_id` | CODE_OR_ID | 1.0 | EIQ_MEETING_D87DADD60A944C7D // EIQ_MEETING_18FE59B894543C7E // EIQ_MEETING_24C8DCE7D9DE13B5 // EIQ_MEETING_F2922240AC16DE78 // EIQ_MEETING_6673312A31620C34 //  |
| 4 | `canonical_horse_id` | CODE_OR_ID | 1.0 | EIQ_HORSE_C3C7CF14BD12CFCF // EIQ_HORSE_0FDF1361186C3EA0 // EIQ_HORSE_9B9263EC0ACF63FC // EIQ_HORSE_B8941A9A11E478C7 // EIQ_HORSE_A7BCA372AD2CE378 // EIQ_HORSE_ |
| 5 | `canonical_track_id` | CODE_OR_ID | 1.0 | EIQ_TRACK_D12B1A9218E933A9 // EIQ_TRACK_97BB7B956FD8CF6F // EIQ_TRACK_E6827ECDD35C15E9 // EIQ_TRACK_0352DC718DDC7A78 // EIQ_TRACK_C1704BD15A3B2ADA // EIQ_TRACK_ |
| 6 | `canonical_jockey_id` | CODE_OR_ID | 1.0 | EIQ_JOCKEY_27DD698F12BC11E6 // EIQ_JOCKEY_E97D73236A017204 // EIQ_JOCKEY_48D6C108E133F504 // EIQ_JOCKEY_769DA183E2461C88 // EIQ_JOCKEY_77D15D943A5F89A6 // EIQ_J |
| 7 | `canonical_trainer_id` | CODE_OR_ID | 0.9486 | EIQ_TRAINER_0DDB0A8DCB98C42B // EIQ_TRAINER_8EF92E0CE71FF717 // EIQ_TRAINER_3595161B9E8DAD71 // EIQ_TRAINER_107257C7A4BBAD89 // EIQ_TRAINER_5A2C3A676ACDB9F7 //  |
| 8 | `race_date` | ISO_DATE | 1.0 | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| 9 | `jurisdiction` | TEXT | 1.0 | VIC |
| 10 | `track` | CODE_OR_ID | 1.0 | ARARAT // WANGARATTA // SWAN HILL // MOE // SANDOWN // CRANBOURNE // HAMILTON // BENDIGO |
| 11 | `track_layout` | CODE_OR_ID | 1.0 | ararat // sportsbet-wangaratta // swan-hill // moe // sandown // cranbourne // bet365-hamilton // apiam-bendigo |
| 12 | `race_number` | NUMERIC | 1.0 | 3.0 // 4.0 // 5.0 // 9.0 // 8.0 // 6.0 // 7.0 // 1.0 |
| 13 | `distance_metres` | INTEGER | 1.0 | 2000 // 1100 // 1310 // 1400 // 1600 // 1000 // 1300 // 1200 |
| 14 | `distance_band` | TEXT | 1.0 | MIDDLE // SPRINT // MILE // STAYING |
| 15 | `race_class` | TEXT | 1.0 | 3Y MDN-SW // 4UP MDN-SW // CL1 // CL2 // CL3 // HCP // MDN-SW // 2Y HCP |
| 16 | `race_class_group` | TEXT | 1.0 | MAIDEN // CL1 // CL2 // CL3 // HANDICAP // 4UP CL3 // CL4 // WANG CUP |
| 17 | `track_condition` | TEXT | 1.0 | Good // Soft // Heavy |
| 18 | `track_condition_group` | TEXT | 1.0 | GOOD // SOFT // HEAVY |
| 19 | `field_size` | BLANK | 0.0 |  |
| 20 | `barrier` | NUMERIC | 0.9496 | 8.0 // 10.0 // 9.0 // 13.0 // 4.0 // 5.0 // 2.0 // 1.0 |
| 21 | `weight_carried` | TEXT | 1.0 | 56.5kg // 54kg // 57kg // 54.5kg // 58kg // 55.5kg // 52.5kg // 56kg |
| 22 | `finish_position` | NUMERIC | 1.0 | 12.0 // 1.0 // 11.0 // 4.0 // 10.0 // 3.0 // 13.0 // 7.0 |
| 23 | `finish_margin` | NUMERIC | 1.0 | 21.8 // 0.0 // 16.8 // 5.3 // 16.4 // 4.5 // 24.8 // 9.6 |
| 24 | `official_race_time` | NUMERIC | 0.9544 | 12383.0 // 12523.0 // 6376.0 // 7747.0 // 12192.0 // 6395.0 // 12103.0 // 7852.0 |
| 25 | `official_race_time_seconds` | NUMERIC | 0.9544 | 123.8300 // 125.2300 // 63.7600 // 77.4700 // 121.9200 // 63.9500 // 121.0300 // 78.5200 |
| 26 | `time_unit` | CODE_OR_ID | 1.0 | CENTISECONDS_TO_SECONDS_V1 // UNSUPPORTED_TIME_UNIT |
| 27 | `runner_time` | BLANK | 0.0 |  |
| 28 | `sectional_times` | BLANK | 0.0 |  |
| 29 | `position_in_running` | BLANK | 0.0 |  |
| 30 | `source_dataset` | TEXT | 1.0 | public/data/edgeiq_historical_results_warehouse_v2_graphql.csv |
| 31 | `source_record_key` | ISO_DATE | 1.0 | 2001-04-01/ARARAT/390280.0/3.0/2507317/BE MY PATRIARCH // 2001-04-01/ARARAT/390280.0/3.0/2508662/COCORICO // 2001-04-01/ARARAT/390280.0/3.0/2506759/GOLDEN CORN  |
| 32 | `duplicate_status` | CODE_OR_ID | 1.0 | RETAINED |

### CANONICAL_PERFORMANCE_FACTS_SNAPSHOT

- Fields: 51

| Position | Field | Type | Nonblank Rate | Samples |
|---:|---|---|---:|---|
| 1 | `performance_id` | CODE_OR_ID | 1.0 | eiq_performance_a07c40795f9c555ebe35ed16f5b13f16 // eiq_performance_cfde1cfa46c05367b0c51a607e9822f6 // eiq_performance_4091cba705245a3ba1005fdf00579803 // eiq_ |
| 2 | `race_id` | CODE_OR_ID | 1.0 | eiq_race_b383ac3f651e5c92965d583136266c89 // eiq_race_f3bb65dc975c5a93883f9cf2cc282f85 // eiq_race_d320116d6ca15deaac5c72c39ec8a90e // eiq_race_8dfa62b2a8e15a9d |
| 3 | `meeting_id` | CODE_OR_ID | 1.0 | eiq_meeting_95b96968e1b256ac81b4282ecfdb99d9 // eiq_meeting_2664767c629950fe9a2cdd5ac25d5157 // eiq_meeting_ba6d02f417ae5a738ee5601652d4549f // eiq_meeting_1754 |
| 4 | `horse_identity_evidence_id` | CODE_OR_ID | 1.0 | eiq_horse_f54a42a9aae055b4b3f8cc559a3e654d // eiq_horse_a9db133e85be569d9618d8618a7f7863 // eiq_horse_f379a2639ea85cf6bb820160a6fc9027 // eiq_horse_e117a785362b |
| 5 | `race_date` | ISO_DATE | 1.0 | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| 6 | `state` | TEXT | 1.0 | VIC |
| 7 | `track` | CODE_OR_ID | 1.0 | ARARAT // WANGARATTA // SWAN HILL // MOE // SANDOWN // CRANBOURNE // HAMILTON // BENDIGO |
| 8 | `venue_name` | CODE_OR_ID | 1.0 | ararat // sportsbet-wangaratta // swan-hill // moe // sandown // cranbourne // bet365-hamilton // apiam-bendigo |
| 9 | `race_number` | INTEGER | 1.0 | 3 // 4 // 5 // 9 // 8 // 6 // 7 // 1 |
| 10 | `race_name` | MULTIWORD_TEXT | 1.0 | SUPER VOBIS THREE-YEARS-OLD MAIDEN PLATE // TOOHEYS NEW MAIDEN PLATE (4YO & UP) // NISSAN CLASS 1 HANDICAP // STAWELL FOR EASTER CLASS 2 HANDICAP // HORSHAM HIR |
| 11 | `race_class` | TEXT | 1.0 | 3Y MDN-SW // 4UP MDN-SW // CL1 // CL2 // CL3 // HCP // MDN-SW // 2Y HCP |
| 12 | `distance_metres` | INTEGER | 1.0 | 2000 // 1100 // 1310 // 1400 // 1600 // 1000 // 1300 // 1200 |
| 13 | `race_status` | TEXT | 1.0 | Paying |
| 14 | `track_condition` | TEXT | 1.0 | Good // Soft // Heavy |
| 15 | `track_rating` | INTEGER | 1.0 | 3 // 7 // 5 // 10 |
| 16 | `rail_position` | MULTIWORD_TEXT | 0.9692 | Rail out 4m from 1400m to 1000m. // Rail in True Position // Rail out 2m entire circuit // Rail out 15 metres Entire Circuit // Rail in true position. // True / |
| 17 | `previous_rail_position` | MULTIWORD_TEXT | 0.931 | True Position // Rail out 4m from 1000m to turn into straight. // True position. // Rail in true position // Rail out 10.5 metres entire circuit. // Rail Out 3m |
| 18 | `weather` | TEXT | 1.0 | Fine // Overcast // Showers |
| 19 | `rainfall` | BLANK | 0.0 |  |
| 20 | `penetrometer` | NUMERIC | 1.0 | 0.0 // 4.88 // 4.96 // 4.48 // 4.29 // 4.09 // 4.17 // 6.04 |
| 21 | `official_winning_time_seconds` | INTEGER | 0.9544 | 12383 // 12523 // 6376 // 7747 // 12192 // 6395 // 12103 // 7852 |
| 22 | `finish_position` | INTEGER | 1.0 | 12 // 1 // 11 // 4 // 3 // 13 // 7 // 9 |
| 23 | `finish_abbreviation` | TEXT | 1.0 | 12th // 1st // 11th // 4th // 10th // 3rd // 13th // 7th |
| 24 | `official_margin` | NUMERIC | 0.9022 | 21.8 // 16.8 // 5.3 // 16.4 // 4.5 // 24.8 // 9.6 // 14.4 |
| 25 | `margin_lengths` | NUMERIC | 0.9022 | 21.8 // 16.8 // 5.3 // 16.4 // 4.5 // 24.8 // 9.6 // 14.4 |
| 26 | `barrier` | INTEGER | 0.9496 | 8 // 1 // 9 // 13 // 4 // 5 // 2 // 7 |
| 27 | `live_barrier` | BLANK | 0.0 |  |
| 28 | `weight_carried` | INTEGER | 1.0 | 56.5 // 54 // 57 // 54.5 // 58 // 55.5 // 52.5 // 56 |
| 29 | `jockey` | TEXT | 1.0 | N.CALLOW // J.J.OLIVER // M.PAYNE // M.EVANS // L.T.COFFEY // N.WILSON // G.MURPHY // T.R.BARRAS |
| 30 | `jockey_code` | NUMERIC | 1.0 | 22637.0 // 22867.0 // 464906.0 // 21271.0 // 22655.0 // 22989.0 // 21940.0 // 756573.0 |
| 31 | `trainer` | TEXT | 0.9314 | C.P.RYAN // B.J.BARNES // T.O'SULLIVAN // F.J.O'ROURKE // E.V.MUSGROVE // M.W.BAIRSTOW // D.K.WEIR // B.J.JAMES |
| 32 | `trainer_code` | NUMERIC | 0.9486 | 12656.0 // 12226.0 // 11588.0 // 11584.0 // 12582.0 // 10077.0 // 12106.0 // 12463.0 |
| 33 | `starting_price_raw` | TEXT | 1.0 | $8 // $3.5 // $26 // $13 // $15 // $21 // $7 // $9 |
| 34 | `starting_price_decimal` | INTEGER | 1.0 | 8 // 3.5 // 26 // 13 // 15 // 21 // 7 // 9 |
| 35 | `scratched` | TEXT | 1.0 | FALSE |
| 36 | `has_results` | BLANK | 0.0 |  |
| 37 | `has_sectionals` | BLANK | 0.0 |  |
| 38 | `has_speed_map` | BLANK | 0.0 |  |
| 39 | `comment_short` | BLANK | 0.0 |  |
| 40 | `comment` | BLANK | 0.0 |  |
| 41 | `stewards_comment` | BLANK | 0.0 |  |
| 42 | `gear_changes` | MULTIWORD_TEXT | 0.123 | Tongue Tie On // Gelded // Blinkers Off // Blinkers On // Blinkers On,Gelded // Pacifiers On // Tongue Tie On,Blinkers Off // Tongue Tie On,Tongue Control Bit O |
| 43 | `performance_quality_state` | CODE_OR_ID | 1.0 | COMPLETE |
| 44 | `official_time_quality_state` | CODE_OR_ID | 1.0 | OFFICIAL_TIME_AVAILABLE // OFFICIAL_TIME_UNAVAILABLE |
| 45 | `margin_quality_state` | CODE_OR_ID | 1.0 | OFFICIAL_MARGIN_AVAILABLE |
| 46 | `source_file` | TEXT | 1.0 | public/data/edgeiq_historical_results_warehouse_v2_graphql.csv |
| 47 | `source_row_number` | INTEGER | 1.0 | 2 // 3 // 4 // 5 // 6 // 7 // 8 // 9 |
| 48 | `source_sha256` | HASH_OR_ID | 1.0 | 13f17e2ae21802aef5017a9a09cbb9ec572c9fda4c8fa8f85da27231e8828974 |
| 49 | `raw_warehouse_snapshot_id` | CODE_OR_ID | 1.0 | eiq_warehouse_snapshot_b24578e0eb795ab6bd076452bfff3f5e |
| 50 | `materialisation_version` | CODE_OR_ID | 1.0 | PHASE1_5B_PERFORMANCE_FACTS_V0_1 |
| 51 | `materialised_at` | ISO_DATE | 1.0 | 2026-07-15T23:08:17.258565+00:00 |

### CANONICAL_PERFORMANCE_FACTS_V0_2

- Fields: 52

| Position | Field | Type | Nonblank Rate | Samples |
|---:|---|---|---:|---|
| 1 | `performance_fact_id` | CODE_OR_ID | 1.0 | pf2_b5eb39ea7abe6a0fbab2ee81ce451ab9 // pf2_14dc7063d9797a29a78fbb61a4b6f243 // pf2_90079991b04678970c03d78d1c342753 // pf2_8cffe94eed759db8e4b994ba235eead7 //  |
| 2 | `source_version` | CODE_OR_ID | 1.0 | EDGEIQ_RESULTS_WAREHOUSE_V2 |
| 3 | `generated_timestamp` | ISO_DATE | 1.0 | 2026-07-16T00:09:19.813788+00:00 // 2026-07-16T00:09:19.813908+00:00 // 2026-07-16T00:09:19.813957+00:00 // 2026-07-16T00:09:19.813990+00:00 // 2026-07-16T00:09 |
| 4 | `race_id` | NUMERIC | 1.0 | 390280.0 // 390282.0 // 390283.0 // 390284.0 // 390285.0 // 390286.0 // 390287.0 // 434649.0 |
| 5 | `runner_id` | INTEGER | 1.0 | 2507317 // 2508662 // 2506759 // 2507131 // 2508935 // 2509031 // 2506758 // 2507312 |
| 6 | `race_date` | ISO_DATE | 1.0 | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| 7 | `track` | CODE_OR_ID | 1.0 | ARARAT // WANGARATTA // SWAN HILL // MOE // SANDOWN // CRANBOURNE // HAMILTON // BENDIGO |
| 8 | `state` | TEXT | 1.0 | VIC |
| 9 | `race_number` | NUMERIC | 1.0 | 3.0 // 4.0 // 5.0 // 9.0 // 8.0 // 6.0 // 7.0 // 1.0 |
| 10 | `race_name` | MULTIWORD_TEXT | 1.0 | SUPER VOBIS THREE-YEARS-OLD MAIDEN PLATE // TOOHEYS NEW MAIDEN PLATE (4YO & UP) // NISSAN CLASS 1 HANDICAP // STAWELL FOR EASTER CLASS 2 HANDICAP // HORSHAM HIR |
| 11 | `race_class` | TEXT | 1.0 | 3Y MDN-SW // 4UP MDN-SW // CL1 // CL2 // CL3 // HCP // MDN-SW // 2Y HCP |
| 12 | `distance_raw` | TEXT | 1.0 | 2000m // 1100m // 1310m // 1400m // 1600m // 1000m // 1300m // 1200m |
| 13 | `distance_metres` | INTEGER | 1.0 | 2000 // 1100 // 1310 // 1400 // 1600 // 1000 // 1300 // 1200 |
| 14 | `track_condition` | TEXT | 1.0 | Good // Soft // Heavy |
| 15 | `track_rating` | INTEGER | 1.0 | 3 // 7 // 5 // 10 |
| 16 | `rail_position` | MULTIWORD_TEXT | 0.9692 | Rail out 4m from 1400m to 1000m. // Rail in True Position // Rail out 2m entire circuit // Rail out 15 metres Entire Circuit // Rail in true position. // True / |
| 17 | `weather` | TEXT | 1.0 | Fine // Overcast // Showers |
| 18 | `horse` | MULTIWORD_TEXT | 1.0 | BE MY PATRIARCH // COCORICO // GOLDEN CORN // MOONLIGHT COWBOY // READY BLETCH // STARDOM ROAD // TUYET DIEU // CANALETTA |
| 19 | `horse_code` | NUMERIC | 1.0 | 557016.0 // 418335.0 // 424845.0 // 556646.0 // 417501.0 // 410226.0 // 556083.0 // 424706.0 |
| 20 | `trainer` | TEXT | 0.9314 | C.P.RYAN // B.J.BARNES // T.O'SULLIVAN // F.J.O'ROURKE // E.V.MUSGROVE // M.W.BAIRSTOW // D.K.WEIR // B.J.JAMES |
| 21 | `trainer_code` | NUMERIC | 0.9486 | 12656.0 // 12226.0 // 11588.0 // 11584.0 // 12582.0 // 10077.0 // 12106.0 // 12463.0 |
| 22 | `jockey` | TEXT | 1.0 | N.CALLOW // J.J.OLIVER // M.PAYNE // M.EVANS // L.T.COFFEY // N.WILSON // G.MURPHY // T.R.BARRAS |
| 23 | `jockey_code` | NUMERIC | 1.0 | 22637.0 // 22867.0 // 464906.0 // 21271.0 // 22655.0 // 22989.0 // 21940.0 // 756573.0 |
| 24 | `barrier` | NUMERIC | 0.9496 | 8.0 // 10.0 // 9.0 // 13.0 // 4.0 // 5.0 // 2.0 // 1.0 |
| 25 | `weight` | NUMERIC | 1.0 | 56.5 // 54.0 // 57.0 // 54.5 // 58.0 // 55.5 // 52.5 // 56.0 |
| 26 | `finish_position` | NUMERIC | 1.0 | 12.0 // 1.0 // 11.0 // 4.0 // 10.0 // 3.0 // 13.0 // 7.0 |
| 27 | `margin_raw` | TEXT | 0.9022 | 21.8L // 16.8L // 5.3L // 16.4L // 4.5L // 24.8L // 9.6L // 14.4L |
| 28 | `margin_lengths` | NUMERIC | 0.9022 | 21.8 // 16.8 // 5.3 // 16.4 // 4.5 // 24.8 // 9.6 // 14.4 |
| 29 | `starting_price` | TEXT | 1.0 | $8 // $3.5 // $26 // $13 // $15 // $21 // $7 // $9 |
| 30 | `starting_price_decimal` | NUMERIC | 1.0 | 8.0 // 3.5 // 26.0 // 13.0 // 15.0 // 21.0 // 7.0 // 9.0 |
| 31 | `raw_winning_time` | NUMERIC | 0.9544 | 12383.0 // 12523.0 // 6376.0 // 7747.0 // 12192.0 // 6395.0 // 12103.0 // 7852.0 |
| 32 | `governed_time_seconds` | NUMERIC | 0.9544 | 123.83 // 125.23 // 63.76 // 77.47 // 121.92 // 63.95 // 121.03 // 78.52 |
| 33 | `time_unit` | CODE_OR_ID | 0.9544 | CENTISECONDS |
| 34 | `benchmark_eligible` | TEXT | 1.0 | True // False |
| 35 | `quality_state` | CODE_OR_ID | 1.0 | COMPLETE // SOURCE_INCOMPLETE |
| 36 | `legacy_performance_fact_id` | CODE_OR_ID | 1.0 | pf_0943ec460ba6e24a2de559e8 // pf_6ad081d7e35984bc3c50d029 // pf_3c29666d7833577e74d340c7 // pf_132f8314b26407af174ecaef // pf_6be19633d81701a4fb719aa3 // pf_75 |
| 37 | `source_row_number` | INTEGER | 1.0 | 1 // 2 // 3 // 4 // 5 // 6 // 7 // 8 |
| 38 | `identity_version` | CODE_OR_ID | 1.0 | PERFORMANCE_FACT_ID_V0_2_RACE_CONTEXT_RUNNER_HORSE |
| 39 | `identity_natural_key` | ISO_DATE | 1.0 | 2001-04-01/VIC/ARARAT/3/390280.0/2507317/557016.0 // 2001-04-01/VIC/ARARAT/3/390280.0/2508662/418335.0 // 2001-04-01/VIC/ARARAT/3/390280.0/2506759/424845.0 // 2 |
| 40 | `collision_resolution_state` | CODE_OR_ID | 1.0 | NATURAL_KEY_UNIQUE |
| 41 | `identity_collision_discriminator` | BLANK | 0.0 |  |
| 42 | `recomputed_performance_fact_id` | CODE_OR_ID | 1.0 | pf2_b5eb39ea7abe6a0fbab2ee81ce451ab9 // pf2_14dc7063d9797a29a78fbb61a4b6f243 // pf2_90079991b04678970c03d78d1c342753 // pf2_8cffe94eed759db8e4b994ba235eead7 //  |
| 43 | `race_context_key` | ISO_DATE | 1.0 | 2001-04-01/VIC/ARARAT/3/390280.0 // 2001-04-01/VIC/ARARAT/4/390282.0 // 2001-04-01/VIC/ARARAT/5/390283.0 // 2001-04-01/VIC/ARARAT/9/390284.0 // 2001-04-01/VIC/A |
| 44 | `race_time_consistency_state` | CODE_OR_ID | 1.0 | CONSISTENT_COMPLETE // CONSISTENT_WITH_MISSING |
| 45 | `race_time_unit_state` | CODE_OR_ID | 1.0 | CENTISECONDS_CONFIRMED // DISTANCE_UNAVAILABLE_OR_CONFLICTED |
| 46 | `race_time_source_unit` | CODE_OR_ID | 0.9544 | CENTISECONDS |
| 47 | `race_time_governed_seconds` | NUMERIC | 0.9544 | 123.83 // 125.23 // 63.76 // 77.47 // 121.92 // 63.95 // 121.03 // 78.52 |
| 48 | `race_benchmark_eligible` | TEXT | 1.0 | True // False |
| 49 | `performance_benchmark_eligible` | TEXT | 1.0 | True // False |
| 50 | `benchmark_exclusion_reason` | MULTIWORD_TEXT | 0.0456 | SOURCE_INCOMPLETE / TIME_UNIT_NOT_CONFIRMED |
| 51 | `governance_version` | CODE_OR_ID | 1.0 | PHASE1_6_1_CORRECTED_IDENTITY_AND_GOVERNANCE_V0_2 |
| 52 | `governance_generated_at` | ISO_DATE | 1.0 | 2026-07-16T07:52:45Z |

### HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL

- Fields: 53

| Position | Field | Type | Nonblank Rate | Samples |
|---:|---|---|---:|---|
| 1 | `race_date` | ISO_DATE | 1.0 | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| 2 | `track` | CODE_OR_ID | 1.0 | ARARAT // WANGARATTA // SWAN HILL // MOE // SANDOWN // CRANBOURNE // HAMILTON // BENDIGO |
| 3 | `venue_name` | CODE_OR_ID | 1.0 | ararat // sportsbet-wangaratta // swan-hill // moe // sandown // cranbourne // bet365-hamilton // apiam-bendigo |
| 4 | `state` | TEXT | 1.0 | VIC |
| 5 | `meet_code` | NUMERIC | 1.0 | 350686.0 // 350685.0 // 350688.0 // 350687.0 // 350320.0 // 350665.0 // 350700.0 // 350321.0 |
| 6 | `meet_url` | TEXT | 1.0 | https://www.racing.com/form/2001-04-01/ararat // https://www.racing.com/form/2001-04-01/wangaratta // https://www.racing.com/form/2001-04-02/swan-hill // https: |
| 7 | `race_id` | NUMERIC | 1.0 | 390280.0 // 390282.0 // 390283.0 // 390284.0 // 390285.0 // 390286.0 // 390287.0 // 434649.0 |
| 8 | `race_no` | NUMERIC | 1.0 | 3.0 // 4.0 // 5.0 // 9.0 // 8.0 // 6.0 // 7.0 // 1.0 |
| 9 | `race_status` | TEXT | 1.0 | Paying |
| 10 | `race_name` | MULTIWORD_TEXT | 1.0 | SUPER VOBIS THREE-YEARS-OLD MAIDEN PLATE // TOOHEYS NEW MAIDEN PLATE (4YO & UP) // NISSAN CLASS 1 HANDICAP // STAWELL FOR EASTER CLASS 2 HANDICAP // HORSHAM HIR |
| 11 | `race_class` | TEXT | 1.0 | 3Y MDN-SW // 4UP MDN-SW // CL1 // CL2 // CL3 // HCP // MDN-SW // 2Y HCP |
| 12 | `distance` | TEXT | 1.0 | 2000m // 1100m // 1310m // 1400m // 1600m // 1000m // 1300m // 1200m |
| 13 | `race_time_utc` | ISO_DATE | 1.0 | 2001-04-01T03:34:00.000Z // 2001-04-01T04:10:00.000Z // 2001-04-01T04:46:00.000Z // 2001-04-01T07:15:00.000Z // 2001-04-01T06:40:00.000Z // 2001-04-01T05:22:00. |
| 14 | `track_condition` | TEXT | 1.0 | Good // Soft // Heavy |
| 15 | `track_rating` | INTEGER | 1.0 | 3 // 7 // 5 // 10 |
| 16 | `rail_position` | MULTIWORD_TEXT | 0.9692 | Rail out 4m from 1400m to 1000m. // Rail in True Position // Rail out 2m entire circuit // Rail out 15 metres Entire Circuit // Rail in true position. // True / |
| 17 | `previous_rail_position` | MULTIWORD_TEXT | 0.931 | True Position // Rail out 4m from 1000m to turn into straight. // True position. // Rail in true position // Rail out 10.5 metres entire circuit. // Rail Out 3m |
| 18 | `weather` | TEXT | 1.0 | Fine // Overcast // Showers |
| 19 | `rainfall` | BLANK | 0.0 |  |
| 20 | `penetrometer` | NUMERIC | 1.0 | 0.0 // 4.88 // 4.96 // 4.48 // 4.29 // 4.09 // 4.17 // 6.04 |
| 21 | `has_sectionals` | BLANK | 0.0 |  |
| 22 | `has_results` | BLANK | 0.0 |  |
| 23 | `has_speed_map` | BLANK | 0.0 |  |
| 24 | `runner_id` | INTEGER | 1.0 | 2507317 // 2508662 // 2506759 // 2507131 // 2508935 // 2509031 // 2506758 // 2507312 |
| 25 | `race_entry_number` | NUMERIC | 1.0 | 1.0 // 2.0 // 3.0 // 4.0 // 5.0 // 6.0 // 7.0 // 8.0 |
| 26 | `horse` | MULTIWORD_TEXT | 1.0 | BE MY PATRIARCH // COCORICO // GOLDEN CORN // MOONLIGHT COWBOY // READY BLETCH // STARDOM ROAD // TUYET DIEU // CANALETTA |
| 27 | `horse_code` | NUMERIC | 1.0 | 557016.0 // 418335.0 // 424845.0 // 556646.0 // 417501.0 // 410226.0 // 556083.0 // 424706.0 |
| 28 | `trainer` | TEXT | 0.9314 | C.P.RYAN // B.J.BARNES // T.O'SULLIVAN // F.J.O'ROURKE // E.V.MUSGROVE // M.W.BAIRSTOW // D.K.WEIR // B.J.JAMES |
| 29 | `trainer_code` | NUMERIC | 0.9486 | 12656.0 // 12226.0 // 11588.0 // 11584.0 // 12582.0 // 10077.0 // 12106.0 // 12463.0 |
| 30 | `jockey` | TEXT | 1.0 | N.CALLOW // J.J.OLIVER // M.PAYNE // M.EVANS // L.T.COFFEY // N.WILSON // G.MURPHY // T.R.BARRAS |
| 31 | `jockey_code` | NUMERIC | 1.0 | 22637.0 // 22867.0 // 464906.0 // 21271.0 // 22655.0 // 22989.0 // 21940.0 // 756573.0 |
| 32 | `barrier` | NUMERIC | 0.9496 | 8.0 // 10.0 // 9.0 // 13.0 // 4.0 // 5.0 // 2.0 // 1.0 |
| 33 | `live_barrier` | BLANK | 0.0 |  |
| 34 | `weight` | TEXT | 1.0 | 56.5kg // 54kg // 57kg // 54.5kg // 58kg // 55.5kg // 52.5kg // 56kg |
| 35 | `scratched` | TEXT | 1.0 | False |
| 36 | `finish` | NUMERIC | 1.0 | 12.0 // 1.0 // 11.0 // 4.0 // 10.0 // 3.0 // 13.0 // 7.0 |
| 37 | `finish_abv` | TEXT | 1.0 | 12th // 1st // 11th // 4th // 10th // 3rd // 13th // 7th |
| 38 | `margin` | TEXT | 0.9022 | 21.8L // 16.8L // 5.3L // 16.4L // 4.5L // 24.8L // 9.6L // 14.4L |
| 39 | `margin_l` | NUMERIC | 1.0 | 21.8 // 0.0 // 16.8 // 5.3 // 16.4 // 4.5 // 24.8 // 9.6 |
| 40 | `starting_price` | TEXT | 1.0 | $8 // $3.5 // $26 // $13 // $15 // $21 // $7 // $9 |
| 41 | `starting_price_decimal` | NUMERIC | 1.0 | 8.0 // 3.5 // 26.0 // 13.0 // 15.0 // 21.0 // 7.0 // 9.0 |
| 42 | `winning_time` | NUMERIC | 0.9544 | 12383.0 // 12523.0 // 6376.0 // 7747.0 // 12192.0 // 6395.0 // 12103.0 // 7852.0 |
| 43 | `comment_short` | BLANK | 0.0 |  |
| 44 | `comment` | BLANK | 0.0 |  |
| 45 | `comment_stewards` | BLANK | 0.0 |  |
| 46 | `gear_changes` | MULTIWORD_TEXT | 0.123 | Tongue Tie On // Gelded // Blinkers Off // Blinkers On // Blinkers On,Gelded // Pacifiers On // Tongue Tie On,Blinkers Off // Tongue Tie On,Tongue Control Bit O |
| 47 | `source` | CODE_OR_ID | 1.0 | RACING_COM_GRAPHQL_GET_RACES_FOR_MEET_APR2001 // RACING_COM_GRAPHQL_GET_RACES_FOR_MEET_APR2002 |
| 48 | `built_at` | ISO_DATE | 1.0 | 2026-06-22T03:08:58.119Z // 2026-06-22T03:08:58.120Z // 2026-06-22T03:08:58.121Z // 2026-06-22T03:08:58.122Z // 2026-06-22T03:08:58.123Z // 2026-06-22T03:09:18. |
| 49 | `source_file` | TEXT | 1.0 | edgeiq_graphql_april_2001_results_v1.csv // edgeiq_graphql_april_2002_results_v1.csv |
| 50 | `finish_num` | NUMERIC | 1.0 | 12.0 // 1.0 // 11.0 // 4.0 // 10.0 // 3.0 // 13.0 // 7.0 |
| 51 | `won` | INTEGER | 1.0 | 0 // 1 |
| 52 | `placed` | INTEGER | 1.0 | 0 // 1 |
| 53 | `built_at_warehouse_v2` | ISO_DATE | 1.0 | 2026-06-23T04:48:25.259461+00:00 |

### HISTORICAL_RUN_OBSERVATION_FACT_V2

- Fields: 37

| Position | Field | Type | Nonblank Rate | Samples |
|---:|---|---|---:|---|
| 1 | `historical_run_observation_id` | HASH_OR_ID | 1.0 | b83252145a2a39beec4e609f08bf39c2d9e786d1b535c4e072b120d053a4541b // 9566299e423cfabf81dfd9b1ebd40c4c67f89f17a328bd70abbfaf51cce69821 // 8a35dae07262da6ff66b3017 |
| 2 | `canonical_horse_id` | TEXT | 1.0 | HORSE/RACINGCOM/2026221 // HORSE/RACINGCOM/2029649 // HORSE/RACINGCOM/2029654 // HORSE/RACINGCOM/2029659 // HORSE/RACINGCOM/2029881 // HORSE/RACINGCOM/2031157 / |
| 3 | `canonical_horse_name` | BLANK | 0.0 |  |
| 4 | `source_horse_id` | INTEGER | 1.0 | 2026221 // 2029649 // 2029654 // 2029659 // 2029881 // 2031157 // 2031158 // 2031727 |
| 5 | `source_horse_name` | BLANK | 0.0 |  |
| 6 | `horse_identity_resolution_status` | CODE_OR_ID | 1.0 | IDENTITY_RESOLVED |
| 7 | `horse_identity_resolution_method` | CODE_OR_ID | 1.0 | EXACT_SOURCE_ID |
| 8 | `canonical_race_id` | INTEGER | 1.0 | 351360 // 351360.0 // 351361 // 351361.0 // 351362 // 351362.0 // 351363 // 351363.0 |
| 9 | `race_date` | ISO_DATE | 1.0 | 2000-08-02 // 2000-08-03 // 2000-08-05 // 2000-08-06 // 2000-08-07 // 2000-08-08 // 2000-08-09 // 2000-08-10 |
| 10 | `canonical_track` | CODE_OR_ID | 1.0 | FLEMINGTON // CRANBOURNE // CAULFIELD // SALE // THE VALLEY // HAMILTON // MORNINGTON // SANDOWN |
| 11 | `race_number` | INTEGER | 1.0 | 3 // 1 // 5 // 4 // 8 // 7 // 2 // 6 |
| 12 | `race_distance_metres` | INTEGER | 1.0 | 1400 // 1000 // 1600 // 2000 // 1800 // 1200 // 2025 // 1100 |
| 13 | `race_class` | TEXT | 1.0 | 3YC&G 1MW // 3YF 1MW // 4UP CL6 // 1MW LY // 1MW-LY // MARES1MWLY // MARES CL6 // 3Y MDN-SW |
| 14 | `surface_group` | BLANK | 0.0 |  |
| 15 | `track_condition` | TEXT | 1.0 | Soft // Good // Heavy // 5 |
| 16 | `barrier` | INTEGER | 0.9798 | 1 // 7 // 6 // 4 // 8 // 5 // 2 // 3 |
| 17 | `weight_kg` | INTEGER | 1.0 | 57.5 // 55 // 58 // 54 // 55.5 // 54.5 // 56.5 // 53.5 |
| 18 | `jockey_name` | TEXT | 1.0 | D.Gauci // N.Rawiller // B.Park // S.J.Hyland // B.MacDonald // N.Wilson // P.Mertens // B.Prebble |
| 19 | `trainer_name` | TEXT | 0.9798 | R.G.Hore-Lacy // A.J.Macpherson // R.G.Symons // P.T.Hyland // C.C.Parry // D.L.Freedman // J.F.Moloney // M.J.Ellerton |
| 20 | `finish_position` | BLANK | 0.0 |  |
| 21 | `field_size` | BLANK | 0.0 |  |
| 22 | `beaten_margin_lengths` | NUMERIC | 0.8998 | 0.8 // 5.4 // 10.2 // 1.8 // 3.6 // 6.7 // 0.5 // 6.4 |
| 23 | `starting_price` | TEXT | 0.9988 | $6 // $7 // $8 // $21 // $3 // $15 // $41 // $4.5 |
| 24 | `official_race_time_seconds` | BLANK | 0.0 |  |
| 25 | `position_in_running` | BLANK | 0.0 |  |
| 26 | `sectional_800_to_600_lengths_v_standard` | BLANK | 0.0 |  |
| 27 | `sectional_600_to_400_lengths_v_standard` | BLANK | 0.0 |  |
| 28 | `sectional_400_to_200_lengths_v_standard` | BLANK | 0.0 |  |
| 29 | `sectional_200_to_finish_lengths_v_standard` | BLANK | 0.0 |  |
| 30 | `source_system` | CODE_OR_ID | 1.0 | RACINGCOM |
| 31 | `source_path` | TEXT | 1.0 | public\data\edgeiq_graphql_august_2000_results_v1.csv // public\data\edgeiq_historical_results_warehouse_v2_graphql.csv |
| 32 | `source_file_sha256` | HASH_OR_ID | 1.0 | b8ca32d050d0c834a69da3fba5ec507c6ee099d86ee74a39d1903305c9e375c2 // 13f17e2ae21802aef5017a9a09cbb9ec572c9fda4c8fa8f85da27231e8828974 |
| 33 | `source_row_number` | INTEGER | 1.0 | 4 // 5 // 6 // 9 // 2 // 7 // 8 // 3 |
| 34 | `source_row_evidence_sha256` | HASH_OR_ID | 1.0 | 27cb23cf24e353c140e8198023ad64ae47c2224798adec34f274c76713442b88 // 3c4f93838ba8dc55d437d4de8e97aee95bea684675578b01b3fdfbcf5cfc0445 // 70f1e288739f12a3e832c3b0 |
| 35 | `historical_run_builder_version` | CODE_OR_ID | 1.0 | EDGEIQ_HISTORICAL_RUN_OBSERVATION_V2 |
| 36 | `historical_run_method_version` | CODE_OR_ID | 1.0 | FACTUAL_MULTI_SOURCE_EXTRACTION_AND_DEDUPLICATION_V1 |
| 37 | `historical_run_observation_evidence_sha256` | HASH_OR_ID | 1.0 | 9b346bc6653987f75b884e5a165f89d294228c2ae0d39890399aed15ce1fe8c8 // a8738aeeeaeb97c89a1f09a4f3fd527cf85d10c8f7ea14c24f17124f0895f092 // 4c9747601e1292f4bd23bf52 |

### EPI_PERFORMANCE_FACT_V1

- Fields: 26

| Position | Field | Type | Nonblank Rate | Samples |
|---:|---|---|---:|---|
| 1 | `canonical_performance_id` | CODE_OR_ID | 1.0 | EIQ_PERFORMANCE_5C5588BA701CFE5C // EIQ_PERFORMANCE_CA13D8100047D9D8 // EIQ_PERFORMANCE_19061354CDD77154 // EIQ_PERFORMANCE_2F0040BD282A0933 // EIQ_PERFORMANCE_ |
| 2 | `canonical_race_id` | CODE_OR_ID | 1.0 | EIQ_RACE_162CAACA9FFCD4E2 // EIQ_RACE_638BD84989E0FD2B // EIQ_RACE_9F5E835472B1308D // EIQ_RACE_A3EF7EC2B622E0CB // EIQ_RACE_593E705699ABCF4C // EIQ_RACE_EE44FD |
| 3 | `canonical_horse_id` | CODE_OR_ID | 1.0 | EIQ_HORSE_C3C7CF14BD12CFCF // EIQ_HORSE_0FDF1361186C3EA0 // EIQ_HORSE_9B9263EC0ACF63FC // EIQ_HORSE_B8941A9A11E478C7 // EIQ_HORSE_A7BCA372AD2CE378 // EIQ_HORSE_ |
| 4 | `finish_position` | NUMERIC | 1.0 | 12.0 // 1.0 // 11.0 // 4.0 // 10.0 // 3.0 // 13.0 // 7.0 |
| 5 | `finish_margin_lengths` | NUMERIC | 1.0 | 21.8000 // 0.0000 // 16.8000 // 5.3000 // 16.4000 // 4.5000 // 24.8000 // 9.6000 |
| 6 | `runner_time_equivalent_seconds` | NUMERIC | 1.0 | 127.4633 // 123.8300 // 126.6300 // 124.7133 // 126.5633 // 124.5800 // 127.9633 // 125.4300 |
| 7 | `runner_lengths_v_standard` | NUMERIC | 1.0 | -20.6900 // 1.1100 // -15.6900 // -4.1900 // -15.2900 // -3.3900 // -23.6900 // -8.4900 |
| 8 | `early_section_lengths_v_standard` | BLANK | 0.0 |  |
| 9 | `mid_section_lengths_v_standard` | BLANK | 0.0 |  |
| 10 | `late_section_lengths_v_standard` | BLANK | 0.0 |  |
| 11 | `calculation_status` | CODE_OR_ID | 1.0 | CALCULATED_NO_OFFICIAL_SECTIONAL |
| 12 | `epi_value` | NUMERIC | 1.0 | 0.0000 // 52.7750 // 10.7750 // 39.5250 // 11.7750 // 41.5250 // 28.7750 // 16.7750 |
| 13 | `epi_band` | TEXT | 1.0 | RISK // NEUTRAL // POSITIVE // ELITE |
| 14 | `epi_methodology` | CODE_OR_ID | 1.0 | LENGTHS_V_STANDARD_SCALED_V1_CENTISECONDS_REPAIRED |
| 15 | `raw_lengths_v_standard` | NUMERIC | 1.0 | -20.6900 // 1.1100 // -15.6900 // -4.1900 // -15.2900 // -3.3900 // -23.6900 // -8.4900 |
| 16 | `weight_carried_kg` | NUMERIC | 1.0 | 56.500 // 54.000 // 57.000 // 54.500 // 58.000 // 55.500 // 52.500 // 56.000 |
| 17 | `reference_weight_kg` | BLANK | 0.0 |  |
| 18 | `weight_delta_kg` | BLANK | 0.0 |  |
| 19 | `weight_adjustment_lengths` | BLANK | 0.0 |  |
| 20 | `weight_adjusted_lengths_v_standard` | BLANK | 0.0 |  |
| 21 | `race_strength_adjustment` | BLANK | 0.0 |  |
| 22 | `circumstance_adjustment` | BLANK | 0.0 |  |
| 23 | `epi_performance_rating` | NUMERIC | 1.0 | 0.0000 // 52.7750 // 10.7750 // 39.5250 // 11.7750 // 41.5250 // 28.7750 // 16.7750 |
| 24 | `weight_adjustment_status` | CODE_OR_ID | 1.0 | INSUFFICIENT_EMPIRICAL_EVIDENCE |
| 25 | `weight_adjustment_methodology` | CODE_OR_ID | 1.0 | FAIL_CLOSED_NO_EMPIRICALLY_DERIVED_COEFFICIENT |
| 26 | `weight_adjustment_coefficient_provenance` | TEXT | 1.0 | NONE |

## Highest Identity Candidates

| Target | Role | Field | Score | Type | Samples |
|---|---|---|---:|---|---|
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | HORSE_ID | `horse_identity_evidence_id` | 45 | CODE_OR_ID | eiq_horse_f54a42a9aae055b4b3f8cc559a3e654d // eiq_horse_a9db133e85be569d9618d8618a7f7863 // eiq_horse_f379a2639ea85cf6bb820160a6fc9027 // eiq_horse_e117a785362b |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | HORSE_NAME | `race_name` | 40 | MULTIWORD_TEXT | SUPER VOBIS THREE-YEARS-OLD MAIDEN PLATE // TOOHEYS NEW MAIDEN PLATE (4YO & UP) // NISSAN CLASS 1 HANDICAP // STAWELL FOR EASTER CLASS 2 HANDICAP // HORSHAM HIR |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | HORSE_NAME | `horse_identity_evidence_id` | 30 | CODE_OR_ID | eiq_horse_f54a42a9aae055b4b3f8cc559a3e654d // eiq_horse_a9db133e85be569d9618d8618a7f7863 // eiq_horse_f379a2639ea85cf6bb820160a6fc9027 // eiq_horse_e117a785362b |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | HORSE_NAME | `venue_name` | 30 | CODE_OR_ID | ararat // sportsbet-wangaratta // swan-hill // moe // sandown // cranbourne // bet365-hamilton // apiam-bendigo |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | RACE_DATE | `race_date` | 70 | ISO_DATE | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | RACE_DATE | `materialised_at` | 40 | ISO_DATE | 2026-07-15T23:08:17.258565+00:00 |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | RACE_ID | `race_id` | 115 | CODE_OR_ID | eiq_race_b383ac3f651e5c92965d583136266c89 // eiq_race_f3bb65dc975c5a93883f9cf2cc282f85 // eiq_race_d320116d6ca15deaac5c72c39ec8a90e // eiq_race_8dfa62b2a8e15a9d |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | RACE_NUMBER | `race_number` | 175 | INTEGER | 3 // 4 // 5 // 9 // 8 // 6 // 7 // 1 |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | RACE_NUMBER | `race_class` | 30 | TEXT | 3Y MDN-SW // 4UP MDN-SW // CL1 // CL2 // CL3 // HCP // MDN-SW // 2Y HCP |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | RACE_NUMBER | `race_date` | 30 | ISO_DATE | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | RACE_NUMBER | `race_id` | 30 | CODE_OR_ID | eiq_race_b383ac3f651e5c92965d583136266c89 // eiq_race_f3bb65dc975c5a93883f9cf2cc282f85 // eiq_race_d320116d6ca15deaac5c72c39ec8a90e // eiq_race_8dfa62b2a8e15a9d |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | RACE_NUMBER | `race_name` | 30 | MULTIWORD_TEXT | SUPER VOBIS THREE-YEARS-OLD MAIDEN PLATE // TOOHEYS NEW MAIDEN PLATE (4YO & UP) // NISSAN CLASS 1 HANDICAP // STAWELL FOR EASTER CLASS 2 HANDICAP // HORSHAM HIR |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | RACE_NUMBER | `race_status` | 30 | TEXT | Paying |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | SOURCE | `source_file` | 30 | TEXT | public/data/edgeiq_historical_results_warehouse_v2_graphql.csv |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | SOURCE | `source_row_number` | 30 | INTEGER | 2 // 3 // 4 // 5 // 6 // 7 // 8 // 9 |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | SOURCE | `source_sha256` | 30 | HASH_OR_ID | 13f17e2ae21802aef5017a9a09cbb9ec572c9fda4c8fa8f85da27231e8828974 |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | TRACK | `track` | 100 | CODE_OR_ID | ARARAT // WANGARATTA // SWAN HILL // MOE // SANDOWN // CRANBOURNE // HAMILTON // BENDIGO |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | TRACK | `track_condition` | 40 | TEXT | Good // Soft // Heavy |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | TRACK | `track_rating` | 30 | INTEGER | 3 // 7 // 5 // 10 |
| `CANONICAL_PERFORMANCE_FACTS_SNAPSHOT` | TRACK | `venue_name` | 30 | CODE_OR_ID | ararat // sportsbet-wangaratta // swan-hill // moe // sandown // cranbourne // bet365-hamilton // apiam-bendigo |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | HORSE_ID | `runner_id` | 115 | INTEGER | 2507317 // 2508662 // 2506759 // 2507131 // 2508935 // 2509031 // 2506758 // 2507312 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | HORSE_ID | `horse_code` | 100 | NUMERIC | 557016.0 // 418335.0 // 424845.0 // 556646.0 // 417501.0 // 410226.0 // 556083.0 // 424706.0 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | HORSE_NAME | `horse` | 110 | MULTIWORD_TEXT | BE MY PATRIARCH // COCORICO // GOLDEN CORN // MOONLIGHT COWBOY // READY BLETCH // STARDOM ROAD // TUYET DIEU // CANALETTA |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | HORSE_NAME | `race_name` | 40 | MULTIWORD_TEXT | SUPER VOBIS THREE-YEARS-OLD MAIDEN PLATE // TOOHEYS NEW MAIDEN PLATE (4YO & UP) // NISSAN CLASS 1 HANDICAP // STAWELL FOR EASTER CLASS 2 HANDICAP // HORSHAM HIR |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | HORSE_NAME | `horse_code` | 30 | NUMERIC | 557016.0 // 418335.0 // 424845.0 // 556646.0 // 417501.0 // 410226.0 // 556083.0 // 424706.0 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | HORSE_NAME | `runner_id` | 30 | INTEGER | 2507317 // 2508662 // 2506759 // 2507131 // 2508935 // 2509031 // 2506758 // 2507312 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_DATE | `race_date` | 70 | ISO_DATE | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_DATE | `generated_timestamp` | 40 | ISO_DATE | 2026-07-16T00:09:19.813788+00:00 // 2026-07-16T00:09:19.813908+00:00 // 2026-07-16T00:09:19.813957+00:00 // 2026-07-16T00:09:19.813990+00:00 // 2026-07-16T00:09 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_DATE | `governance_generated_at` | 40 | ISO_DATE | 2026-07-16T07:52:45Z |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_DATE | `identity_natural_key` | 40 | ISO_DATE | 2001-04-01/VIC/ARARAT/3/390280.0/2507317/557016.0 // 2001-04-01/VIC/ARARAT/3/390280.0/2508662/418335.0 // 2001-04-01/VIC/ARARAT/3/390280.0/2506759/424845.0 // 2 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_DATE | `race_context_key` | 40 | ISO_DATE | 2001-04-01/VIC/ARARAT/3/390280.0 // 2001-04-01/VIC/ARARAT/4/390282.0 // 2001-04-01/VIC/ARARAT/5/390283.0 // 2001-04-01/VIC/ARARAT/9/390284.0 // 2001-04-01/VIC/A |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_ID | `race_id` | 100 | NUMERIC | 390280.0 // 390282.0 // 390283.0 // 390284.0 // 390285.0 // 390286.0 // 390287.0 // 434649.0 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_NUMBER | `race_number` | 160 | NUMERIC | 3.0 // 4.0 // 5.0 // 9.0 // 8.0 // 6.0 // 7.0 // 1.0 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_NUMBER | `race_benchmark_eligible` | 30 | TEXT | True // False |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_NUMBER | `race_class` | 30 | TEXT | 3Y MDN-SW // 4UP MDN-SW // CL1 // CL2 // CL3 // HCP // MDN-SW // 2Y HCP |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_NUMBER | `race_context_key` | 30 | ISO_DATE | 2001-04-01/VIC/ARARAT/3/390280.0 // 2001-04-01/VIC/ARARAT/4/390282.0 // 2001-04-01/VIC/ARARAT/5/390283.0 // 2001-04-01/VIC/ARARAT/9/390284.0 // 2001-04-01/VIC/A |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_NUMBER | `race_date` | 30 | ISO_DATE | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_NUMBER | `race_id` | 30 | NUMERIC | 390280.0 // 390282.0 // 390283.0 // 390284.0 // 390285.0 // 390286.0 // 390287.0 // 434649.0 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_NUMBER | `race_name` | 30 | MULTIWORD_TEXT | SUPER VOBIS THREE-YEARS-OLD MAIDEN PLATE // TOOHEYS NEW MAIDEN PLATE (4YO & UP) // NISSAN CLASS 1 HANDICAP // STAWELL FOR EASTER CLASS 2 HANDICAP // HORSHAM HIR |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_NUMBER | `race_time_consistency_state` | 30 | CODE_OR_ID | CONSISTENT_COMPLETE // CONSISTENT_WITH_MISSING |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_NUMBER | `race_time_governed_seconds` | 30 | NUMERIC | 123.83 // 125.23 // 63.76 // 77.47 // 121.92 // 63.95 // 121.03 // 78.52 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_NUMBER | `race_time_source_unit` | 30 | CODE_OR_ID | CENTISECONDS |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | RACE_NUMBER | `race_time_unit_state` | 30 | CODE_OR_ID | CENTISECONDS_CONFIRMED // DISTANCE_UNAVAILABLE_OR_CONFLICTED |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | SOURCE | `race_time_source_unit` | 30 | CODE_OR_ID | CENTISECONDS |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | SOURCE | `source_row_number` | 30 | INTEGER | 1 // 2 // 3 // 4 // 5 // 6 // 7 // 8 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | SOURCE | `source_version` | 30 | CODE_OR_ID | EDGEIQ_RESULTS_WAREHOUSE_V2 |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | TRACK | `track` | 100 | CODE_OR_ID | ARARAT // WANGARATTA // SWAN HILL // MOE // SANDOWN // CRANBOURNE // HAMILTON // BENDIGO |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | TRACK | `track_condition` | 40 | TEXT | Good // Soft // Heavy |
| `CANONICAL_PERFORMANCE_FACTS_V0_2` | TRACK | `track_rating` | 30 | INTEGER | 3 // 7 // 5 // 10 |
| `EPI_PERFORMANCE_FACT_V1` | HORSE_ID | `canonical_horse_id` | 45 | CODE_OR_ID | EIQ_HORSE_C3C7CF14BD12CFCF // EIQ_HORSE_0FDF1361186C3EA0 // EIQ_HORSE_9B9263EC0ACF63FC // EIQ_HORSE_B8941A9A11E478C7 // EIQ_HORSE_A7BCA372AD2CE378 // EIQ_HORSE_ |
| `EPI_PERFORMANCE_FACT_V1` | HORSE_NAME | `canonical_horse_id` | 30 | CODE_OR_ID | EIQ_HORSE_C3C7CF14BD12CFCF // EIQ_HORSE_0FDF1361186C3EA0 // EIQ_HORSE_9B9263EC0ACF63FC // EIQ_HORSE_B8941A9A11E478C7 // EIQ_HORSE_A7BCA372AD2CE378 // EIQ_HORSE_ |
| `EPI_PERFORMANCE_FACT_V1` | HORSE_NAME | `runner_lengths_v_standard` | 30 | NUMERIC | -20.6900 // 1.1100 // -15.6900 // -4.1900 // -15.2900 // -3.3900 // -23.6900 // -8.4900 |
| `EPI_PERFORMANCE_FACT_V1` | HORSE_NAME | `runner_time_equivalent_seconds` | 30 | NUMERIC | 127.4633 // 123.8300 // 126.6300 // 124.7133 // 126.5633 // 124.5800 // 127.9633 // 125.4300 |
| `EPI_PERFORMANCE_FACT_V1` | RACE_ID | `canonical_race_id` | 45 | CODE_OR_ID | EIQ_RACE_162CAACA9FFCD4E2 // EIQ_RACE_638BD84989E0FD2B // EIQ_RACE_9F5E835472B1308D // EIQ_RACE_A3EF7EC2B622E0CB // EIQ_RACE_593E705699ABCF4C // EIQ_RACE_EE44FD |
| `EPI_PERFORMANCE_FACT_V1` | RACE_NUMBER | `canonical_race_id` | 30 | CODE_OR_ID | EIQ_RACE_162CAACA9FFCD4E2 // EIQ_RACE_638BD84989E0FD2B // EIQ_RACE_9F5E835472B1308D // EIQ_RACE_A3EF7EC2B622E0CB // EIQ_RACE_593E705699ABCF4C // EIQ_RACE_EE44FD |
| `EPI_PERFORMANCE_FACT_V1` | RACE_NUMBER | `race_strength_adjustment` | 30 | BLANK |  |
| `EPI_PERFORMANCE_FACT_V1` | SOURCE | `weight_adjustment_coefficient_provenance` | 30 | TEXT | NONE |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | HORSE_ID | `runner_id` | 115 | INTEGER | 2507317 // 2508662 // 2506759 // 2507131 // 2508935 // 2509031 // 2506758 // 2507312 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | HORSE_ID | `horse_code` | 100 | NUMERIC | 557016.0 // 418335.0 // 424845.0 // 556646.0 // 417501.0 // 410226.0 // 556083.0 // 424706.0 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | HORSE_NAME | `horse` | 110 | MULTIWORD_TEXT | BE MY PATRIARCH // COCORICO // GOLDEN CORN // MOONLIGHT COWBOY // READY BLETCH // STARDOM ROAD // TUYET DIEU // CANALETTA |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | HORSE_NAME | `race_name` | 40 | MULTIWORD_TEXT | SUPER VOBIS THREE-YEARS-OLD MAIDEN PLATE // TOOHEYS NEW MAIDEN PLATE (4YO & UP) // NISSAN CLASS 1 HANDICAP // STAWELL FOR EASTER CLASS 2 HANDICAP // HORSHAM HIR |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | HORSE_NAME | `horse_code` | 30 | NUMERIC | 557016.0 // 418335.0 // 424845.0 // 556646.0 // 417501.0 // 410226.0 // 556083.0 // 424706.0 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | HORSE_NAME | `runner_id` | 30 | INTEGER | 2507317 // 2508662 // 2506759 // 2507131 // 2508935 // 2509031 // 2506758 // 2507312 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | HORSE_NAME | `venue_name` | 30 | CODE_OR_ID | ararat // sportsbet-wangaratta // swan-hill // moe // sandown // cranbourne // bet365-hamilton // apiam-bendigo |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_DATE | `race_date` | 70 | ISO_DATE | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_DATE | `built_at` | 40 | ISO_DATE | 2026-06-22T03:08:58.119Z // 2026-06-22T03:08:58.120Z // 2026-06-22T03:08:58.121Z // 2026-06-22T03:08:58.122Z // 2026-06-22T03:08:58.123Z // 2026-06-22T03:09:18. |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_DATE | `built_at_warehouse_v2` | 40 | ISO_DATE | 2026-06-23T04:48:25.259461+00:00 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_DATE | `race_time_utc` | 40 | ISO_DATE | 2001-04-01T03:34:00.000Z // 2001-04-01T04:10:00.000Z // 2001-04-01T04:46:00.000Z // 2001-04-01T07:15:00.000Z // 2001-04-01T06:40:00.000Z // 2001-04-01T05:22:00. |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_ID | `race_id` | 100 | NUMERIC | 390280.0 // 390282.0 // 390283.0 // 390284.0 // 390285.0 // 390286.0 // 390287.0 // 434649.0 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_NUMBER | `race_no` | 130 | NUMERIC | 3.0 // 4.0 // 5.0 // 9.0 // 8.0 // 6.0 // 7.0 // 1.0 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_NUMBER | `race_class` | 30 | TEXT | 3Y MDN-SW // 4UP MDN-SW // CL1 // CL2 // CL3 // HCP // MDN-SW // 2Y HCP |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_NUMBER | `race_date` | 30 | ISO_DATE | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_NUMBER | `race_entry_number` | 30 | NUMERIC | 1.0 // 2.0 // 3.0 // 4.0 // 5.0 // 6.0 // 7.0 // 8.0 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_NUMBER | `race_id` | 30 | NUMERIC | 390280.0 // 390282.0 // 390283.0 // 390284.0 // 390285.0 // 390286.0 // 390287.0 // 434649.0 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_NUMBER | `race_name` | 30 | MULTIWORD_TEXT | SUPER VOBIS THREE-YEARS-OLD MAIDEN PLATE // TOOHEYS NEW MAIDEN PLATE (4YO & UP) // NISSAN CLASS 1 HANDICAP // STAWELL FOR EASTER CLASS 2 HANDICAP // HORSHAM HIR |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_NUMBER | `race_status` | 30 | TEXT | Paying |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | RACE_NUMBER | `race_time_utc` | 30 | ISO_DATE | 2001-04-01T03:34:00.000Z // 2001-04-01T04:10:00.000Z // 2001-04-01T04:46:00.000Z // 2001-04-01T07:15:00.000Z // 2001-04-01T06:40:00.000Z // 2001-04-01T05:22:00. |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | SOURCE | `source` | 100 | CODE_OR_ID | RACING_COM_GRAPHQL_GET_RACES_FOR_MEET_APR2001 // RACING_COM_GRAPHQL_GET_RACES_FOR_MEET_APR2002 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | SOURCE | `source_file` | 30 | TEXT | edgeiq_graphql_april_2001_results_v1.csv // edgeiq_graphql_april_2002_results_v1.csv |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | TRACK | `track` | 100 | CODE_OR_ID | ARARAT // WANGARATTA // SWAN HILL // MOE // SANDOWN // CRANBOURNE // HAMILTON // BENDIGO |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | TRACK | `track_condition` | 40 | TEXT | Good // Soft // Heavy |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | TRACK | `track_rating` | 30 | INTEGER | 3 // 7 // 5 // 10 |
| `HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL` | TRACK | `venue_name` | 30 | CODE_OR_ID | ararat // sportsbet-wangaratta // swan-hill // moe // sandown // cranbourne // bet365-hamilton // apiam-bendigo |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_ID | `horse_identity_resolution_method` | 45 | CODE_OR_ID | EXACT_SOURCE_ID |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_ID | `horse_identity_resolution_status` | 45 | CODE_OR_ID | IDENTITY_RESOLVED |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_ID | `source_horse_id` | 45 | INTEGER | 2026221 // 2029649 // 2029654 // 2029659 // 2029881 // 2031157 // 2031158 // 2031727 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_ID | `canonical_horse_id` | 30 | TEXT | HORSE/RACINGCOM/2026221 // HORSE/RACINGCOM/2029649 // HORSE/RACINGCOM/2029654 // HORSE/RACINGCOM/2029659 // HORSE/RACINGCOM/2029881 // HORSE/RACINGCOM/2031157 / |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_NAME | `canonical_horse_name` | 60 | BLANK |  |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_NAME | `source_horse_name` | 60 | BLANK |  |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_NAME | `canonical_horse_id` | 40 | TEXT | HORSE/RACINGCOM/2026221 // HORSE/RACINGCOM/2029649 // HORSE/RACINGCOM/2029654 // HORSE/RACINGCOM/2029659 // HORSE/RACINGCOM/2029881 // HORSE/RACINGCOM/2031157 / |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_NAME | `jockey_name` | 40 | TEXT | D.Gauci // N.Rawiller // B.Park // S.J.Hyland // B.MacDonald // N.Wilson // P.Mertens // B.Prebble |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_NAME | `trainer_name` | 40 | TEXT | R.G.Hore-Lacy // A.J.Macpherson // R.G.Symons // P.T.Hyland // C.C.Parry // D.L.Freedman // J.F.Moloney // M.J.Ellerton |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_NAME | `horse_identity_resolution_method` | 30 | CODE_OR_ID | EXACT_SOURCE_ID |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_NAME | `horse_identity_resolution_status` | 30 | CODE_OR_ID | IDENTITY_RESOLVED |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | HORSE_NAME | `source_horse_id` | 30 | INTEGER | 2026221 // 2029649 // 2029654 // 2029659 // 2029881 // 2031157 // 2031158 // 2031727 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | RACE_DATE | `race_date` | 70 | ISO_DATE | 2000-08-02 // 2000-08-03 // 2000-08-05 // 2000-08-06 // 2000-08-07 // 2000-08-08 // 2000-08-09 // 2000-08-10 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | RACE_ID | `canonical_race_id` | 45 | INTEGER | 351360 // 351360.0 // 351361 // 351361.0 // 351362 // 351362.0 // 351363 // 351363.0 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | RACE_NUMBER | `race_number` | 175 | INTEGER | 3 // 1 // 5 // 4 // 8 // 7 // 2 // 6 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | RACE_NUMBER | `canonical_race_id` | 45 | INTEGER | 351360 // 351360.0 // 351361 // 351361.0 // 351362 // 351362.0 // 351363 // 351363.0 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | RACE_NUMBER | `race_distance_metres` | 45 | INTEGER | 1400 // 1000 // 1600 // 2000 // 1800 // 1200 // 2025 // 1100 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | RACE_NUMBER | `official_race_time_seconds` | 30 | BLANK |  |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | RACE_NUMBER | `race_class` | 30 | TEXT | 3YC&G 1MW // 3YF 1MW // 4UP CL6 // 1MW LY // 1MW-LY // MARES1MWLY // MARES CL6 // 3Y MDN-SW |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | RACE_NUMBER | `race_date` | 30 | ISO_DATE | 2000-08-02 // 2000-08-03 // 2000-08-05 // 2000-08-06 // 2000-08-07 // 2000-08-08 // 2000-08-09 // 2000-08-10 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | SOURCE | `source_file_sha256` | 30 | HASH_OR_ID | b8ca32d050d0c834a69da3fba5ec507c6ee099d86ee74a39d1903305c9e375c2 // 13f17e2ae21802aef5017a9a09cbb9ec572c9fda4c8fa8f85da27231e8828974 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | SOURCE | `source_horse_id` | 30 | INTEGER | 2026221 // 2029649 // 2029654 // 2029659 // 2029881 // 2031157 // 2031158 // 2031727 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | SOURCE | `source_horse_name` | 30 | BLANK |  |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | SOURCE | `source_path` | 30 | TEXT | public\data\edgeiq_graphql_august_2000_results_v1.csv // public\data\edgeiq_historical_results_warehouse_v2_graphql.csv |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | SOURCE | `source_row_evidence_sha256` | 30 | HASH_OR_ID | 27cb23cf24e353c140e8198023ad64ae47c2224798adec34f274c76713442b88 // 3c4f93838ba8dc55d437d4de8e97aee95bea684675578b01b3fdfbcf5cfc0445 // 70f1e288739f12a3e832c3b0 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | SOURCE | `source_row_number` | 30 | INTEGER | 4 // 5 // 6 // 9 // 2 // 7 // 8 // 3 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | SOURCE | `source_system` | 30 | CODE_OR_ID | RACINGCOM |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | TRACK | `track_condition` | 40 | TEXT | Soft // Good // Heavy // 5 |
| `HISTORICAL_RUN_OBSERVATION_FACT_V2` | TRACK | `canonical_track` | 30 | CODE_OR_ID | FLEMINGTON // CRANBOURNE // CAULFIELD // SALE // THE VALLEY // HAMILTON // MORNINGTON // SANDOWN |
| `PERFORMANCE_WAREHOUSE_V1` | HORSE_ID | `canonical_horse_id` | 45 | CODE_OR_ID | EIQ_HORSE_C3C7CF14BD12CFCF // EIQ_HORSE_0FDF1361186C3EA0 // EIQ_HORSE_9B9263EC0ACF63FC // EIQ_HORSE_B8941A9A11E478C7 // EIQ_HORSE_A7BCA372AD2CE378 // EIQ_HORSE_ |
| `PERFORMANCE_WAREHOUSE_V1` | HORSE_NAME | `canonical_horse_id` | 30 | CODE_OR_ID | EIQ_HORSE_C3C7CF14BD12CFCF // EIQ_HORSE_0FDF1361186C3EA0 // EIQ_HORSE_9B9263EC0ACF63FC // EIQ_HORSE_B8941A9A11E478C7 // EIQ_HORSE_A7BCA372AD2CE378 // EIQ_HORSE_ |
| `PERFORMANCE_WAREHOUSE_V1` | HORSE_NAME | `runner_time` | 30 | BLANK |  |
| `PERFORMANCE_WAREHOUSE_V1` | RACE_DATE | `race_date` | 70 | ISO_DATE | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| `PERFORMANCE_WAREHOUSE_V1` | RACE_DATE | `source_record_key` | 40 | ISO_DATE | 2001-04-01/ARARAT/390280.0/3.0/2507317/BE MY PATRIARCH // 2001-04-01/ARARAT/390280.0/3.0/2508662/COCORICO // 2001-04-01/ARARAT/390280.0/3.0/2506759/GOLDEN CORN  |
| `PERFORMANCE_WAREHOUSE_V1` | RACE_ID | `canonical_race_id` | 45 | CODE_OR_ID | EIQ_RACE_162CAACA9FFCD4E2 // EIQ_RACE_638BD84989E0FD2B // EIQ_RACE_9F5E835472B1308D // EIQ_RACE_A3EF7EC2B622E0CB // EIQ_RACE_593E705699ABCF4C // EIQ_RACE_EE44FD |
| `PERFORMANCE_WAREHOUSE_V1` | RACE_NUMBER | `race_number` | 160 | NUMERIC | 3.0 // 4.0 // 5.0 // 9.0 // 8.0 // 6.0 // 7.0 // 1.0 |
| `PERFORMANCE_WAREHOUSE_V1` | RACE_NUMBER | `canonical_race_id` | 30 | CODE_OR_ID | EIQ_RACE_162CAACA9FFCD4E2 // EIQ_RACE_638BD84989E0FD2B // EIQ_RACE_9F5E835472B1308D // EIQ_RACE_A3EF7EC2B622E0CB // EIQ_RACE_593E705699ABCF4C // EIQ_RACE_EE44FD |
| `PERFORMANCE_WAREHOUSE_V1` | RACE_NUMBER | `official_race_time` | 30 | NUMERIC | 12383.0 // 12523.0 // 6376.0 // 7747.0 // 12192.0 // 6395.0 // 12103.0 // 7852.0 |
| `PERFORMANCE_WAREHOUSE_V1` | RACE_NUMBER | `official_race_time_seconds` | 30 | NUMERIC | 123.8300 // 125.2300 // 63.7600 // 77.4700 // 121.9200 // 63.9500 // 121.0300 // 78.5200 |
| `PERFORMANCE_WAREHOUSE_V1` | RACE_NUMBER | `race_class` | 30 | TEXT | 3Y MDN-SW // 4UP MDN-SW // CL1 // CL2 // CL3 // HCP // MDN-SW // 2Y HCP |
| `PERFORMANCE_WAREHOUSE_V1` | RACE_NUMBER | `race_class_group` | 30 | TEXT | MAIDEN // CL1 // CL2 // CL3 // HANDICAP // 4UP CL3 // CL4 // WANG CUP |
| `PERFORMANCE_WAREHOUSE_V1` | RACE_NUMBER | `race_date` | 30 | ISO_DATE | 2001-04-01 // 2001-04-02 // 2001-04-03 // 2001-04-04 // 2001-04-05 // 2001-04-06 // 2001-04-07 // 2001-04-08 |
| `PERFORMANCE_WAREHOUSE_V1` | SOURCE | `source_dataset` | 30 | TEXT | public/data/edgeiq_historical_results_warehouse_v2_graphql.csv |
| `PERFORMANCE_WAREHOUSE_V1` | SOURCE | `source_record_key` | 30 | ISO_DATE | 2001-04-01/ARARAT/390280.0/3.0/2507317/BE MY PATRIARCH // 2001-04-01/ARARAT/390280.0/3.0/2508662/COCORICO // 2001-04-01/ARARAT/390280.0/3.0/2506759/GOLDEN CORN  |
| `PERFORMANCE_WAREHOUSE_V1` | TRACK | `track` | 100 | CODE_OR_ID | ARARAT // WANGARATTA // SWAN HILL // MOE // SANDOWN // CRANBOURNE // HAMILTON // BENDIGO |
| `PERFORMANCE_WAREHOUSE_V1` | TRACK | `track_condition` | 40 | TEXT | Good // Soft // Heavy |
| `PERFORMANCE_WAREHOUSE_V1` | TRACK | `track_condition_group` | 40 | TEXT | GOOD // SOFT // HEAVY |
| `PERFORMANCE_WAREHOUSE_V1` | TRACK | `canonical_track_id` | 30 | CODE_OR_ID | EIQ_TRACK_D12B1A9218E933A9 // EIQ_TRACK_97BB7B956FD8CF6F // EIQ_TRACK_E6827ECDD35C15E9 // EIQ_TRACK_0352DC718DDC7A78 // EIQ_TRACK_C1704BD15A3B2ADA // EIQ_TRACK_ |
| `PERFORMANCE_WAREHOUSE_V1` | TRACK | `track_layout` | 30 | CODE_OR_ID | ararat // sportsbet-wangaratta // swan-hill // moe // sandown // cranbourne // bet365-hamilton // apiam-bendigo |

## Builder Field Assignments

- Assignment records: 1376

## Audit

- **PASS** — `dataset_schema_profile`: profiled_targets=6; expected=6
- **PASS** — `identity_candidate_detection`: candidate_targets=6; expected=6
- **PASS** — `builder_assignment_extraction`: records=1376; errors=0
- **PASS** — `builder_availability`: missing_builders=0

## Governance

- All source datasets were read only.
- No field aliases were changed automatically.
- No canonical mapping was declared.
- No production builder was modified.
