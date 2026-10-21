-- D-062 LGU priority-table publication gate; validates source reconciliation, the BQ composite and the classroom queue.
-- the one-row summary is written once to a table named for this run and dropped after the checks are recorded:
-- read many times as a temporary view, the same pattern made Databricks SQL fail with INTERNAL_ERROR (c64e949, #202).
-- FAIL: rows, keys or LGUs that differ from dim_city_municipality, AP1 to AP3 values that differ from the published
-- outputs, a classroom group or rank that does not follow D-060's queue, a gap, score, composite, rank or group that
-- differs from a recomputation under D-062 (including a score on an LGU missing any AP), a rule version other than
-- D-062 (derived_values_reconcile), or a sensitivity summary that does not match the ranked rows (counts_reconcile).
-- Counts only (PASS): queued and data-review LGUs. The rank correlations are in bq_priority_sensitivity.
DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();
DECLARE OR REPLACE VARIABLE analytics_gate_summary STRING;
SET VARIABLE analytics_gate_summary = '`edu_access`.`06-analytics`.`lgu_priority_matrix_gate_summary_r_' || sha2(:run_id, 256) || '`';
DECLARE OR REPLACE VARIABLE analytics_gate_owner_sql STRING;

CREATE OR REPLACE TABLE IDENTIFIER(session.analytics_gate_summary) USING DELTA COMMENT 'Internal unpublished one-row summary for one D-062 gate.' AS
WITH c AS (
  SELECT * FROM edu_access.`06-analytics`.lgu_priority_matrix_candidate
), regular AS (
  SELECT * FROM edu_access.`05-gold`.dim_city_municipality WHERE member_type = 'regular'
), expected AS (
  SELECT r.city_mun_psgc_code,
         a.learners_per_public_school AS ap1_ratio, a.coverage_pct AS ap1_coverage, a.is_assessed AS ap1_assessed,
         a.barangays_without_public_es AS ap1_bgys_without_es, a.barangays_without_public_es_pct AS ap1_bgys_pct,
         a.es_count_is_upper_bound AS ap1_upper_bound, a.benchmark_status AS ap1_presence_status,
         a.isolated_es_school_count AS ap1_isolated, a.spacing_benchmark_status AS ap1_spacing_status,
         b.learners_per_classroom AS ap2_ratio, b.learner_coverage_pct AS ap2_coverage,
         b.is_assessed AS ap2_assessed, b.congested_school_count AS affected_schools,
         b.learners_in_congested_schools AS affected_learners,
         b.congested_learner_share_pct AS affected_share, b.benchmark_status AS screen_status,
         t.es_learners_per_teacher AS es_ratio, t.jhs_learners_per_teacher AS jhs_ratio,
         t.shs_learners_per_teacher AS shs_ratio, t.is_assessed AS teacher_assessed,
         t.benchmark_status AS teacher_status,
         a.school_age_population_per_public_school AS ap1_population_ratio,
         COALESCE(CASE WHEN t.es_offered_school_count > 0 THEN t.es_eligible_learners / 35.0 END, 0)
           + COALESCE(CASE WHEN t.jhs_offered_school_count > 0 THEN t.jhs_eligible_learners / 36.0 END, 0)
           + COALESCE(CASE WHEN t.shs_offered_school_count > 0 THEN t.shs_eligible_learners / (80.0 / 3) END, 0)
           AS reference_teachers,
         CAST(COALESCE(t.es_teacher_count, 0) + COALESCE(t.jhs_teacher_count, 0) + COALESCE(t.shs_teacher_count, 0) AS DOUBLE)
           AS reported_teachers
  FROM regular r
  LEFT JOIN edu_access.`06-analytics`.ap1_school_provision a USING (city_mun_psgc_code)
  LEFT JOIN edu_access.`06-analytics`.ap2_classroom_pressure b USING (city_mun_psgc_code)
  LEFT JOIN edu_access.`06-analytics`.ap3_teacher_pressure t USING (city_mun_psgc_code)
), expected_rank AS (
  SELECT city_mun_psgc_code,
         DENSE_RANK() OVER (ORDER BY affected_learners DESC, affected_schools DESC, ap2_ratio DESC) AS queue_rank
  FROM expected WHERE ap2_assessed AND affected_learners > 0
), baseline AS (
  SELECT r.lgu_type, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY e.ap1_population_ratio) AS ap1_baseline
  FROM regular r JOIN expected e USING (city_mun_psgc_code)
  WHERE e.ap1_assessed AND e.ap1_population_ratio IS NOT NULL
  GROUP BY r.lgu_type
), expected_gap AS (
  SELECT e.city_mun_psgc_code, b.ap1_baseline,
         CASE WHEN e.ap1_assessed THEN GREATEST(0.0, e.ap1_population_ratio / NULLIF(b.ap1_baseline, 0) - 1) END AS ap1_gap,
         CASE WHEN e.ap2_assessed THEN GREATEST(0.0, e.ap2_ratio / 50.0 - 1) END AS ap2_gap,
         CASE WHEN e.teacher_assessed THEN GREATEST(0.0, e.reference_teachers / NULLIF(e.reported_teachers, 0) - 1) END AS ap3_gap
  FROM expected e
  JOIN regular r USING (city_mun_psgc_code)
  LEFT JOIN baseline b USING (lgu_type)
), expected_score AS (
  SELECT city_mun_psgc_code,
         100 * PERCENT_RANK() OVER (ORDER BY ap1_gap) AS ap1_score,
         100 * PERCENT_RANK() OVER (ORDER BY ap2_gap) AS ap2_score,
         100 * PERCENT_RANK() OVER (ORDER BY ap3_gap) AS ap3_score
  FROM expected_gap
  WHERE ap1_gap IS NOT NULL AND ap2_gap IS NOT NULL AND ap3_gap IS NOT NULL
), expected_composite AS (
  SELECT *, (ap1_score + ap2_score + ap3_score) / 3 AS composite,
         DENSE_RANK() OVER (ORDER BY (ap1_score + ap2_score + ap3_score) / 3 DESC) AS composite_rank
  FROM expected_score
), sensitivity AS (
  SELECT * FROM edu_access.`06-analytics`.bq_priority_sensitivity_candidate
)
SELECT
  (SELECT COUNT(*) FROM c) AS rows, (SELECT COUNT(*) FROM regular) AS expected_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT city_mun_psgc_code) FROM c) AS duplicate_keys,
  (SELECT COUNT(*) FROM c FULL OUTER JOIN regular USING (city_mun_psgc_code)
    WHERE c.city_mun_psgc_code IS NULL OR regular.city_mun_psgc_code IS NULL) AS lgu_mismatch,
  (SELECT COUNT(*) FROM c JOIN expected e USING (city_mun_psgc_code)
    WHERE c.ap1_learners_per_public_school IS DISTINCT FROM e.ap1_ratio
       OR c.ap1_coverage_pct IS DISTINCT FROM e.ap1_coverage
       OR c.ap1_assessed IS DISTINCT FROM e.ap1_assessed
       OR c.ap1_barangays_without_public_es IS DISTINCT FROM e.ap1_bgys_without_es
       OR c.ap1_barangays_without_public_es_pct IS DISTINCT FROM e.ap1_bgys_pct
       OR c.ap1_es_count_is_upper_bound IS DISTINCT FROM e.ap1_upper_bound
       OR c.ap1_school_presence_status IS DISTINCT FROM e.ap1_presence_status
       OR c.ap1_isolated_es_school_count IS DISTINCT FROM e.ap1_isolated
       OR c.ap1_spacing_status IS DISTINCT FROM e.ap1_spacing_status
       OR c.ap2_learners_per_reported_room IS DISTINCT FROM e.ap2_ratio
       OR c.ap2_learner_coverage_pct IS DISTINCT FROM e.ap2_coverage
       OR c.ap2_assessed IS DISTINCT FROM e.ap2_assessed
       OR c.ap2_screened_congested_school_count IS DISTINCT FROM e.affected_schools
       OR c.ap2_affected_learners IS DISTINCT FROM e.affected_learners
       OR c.ap2_affected_learner_share_pct IS DISTINCT FROM e.affected_share
       OR c.ap2_screen_status IS DISTINCT FROM e.screen_status
       OR c.ap3_es_learners_per_teacher IS DISTINCT FROM e.es_ratio
       OR c.ap3_jhs_learners_per_teacher IS DISTINCT FROM e.jhs_ratio
       OR c.ap3_shs_learners_per_teacher IS DISTINCT FROM e.shs_ratio
       OR c.ap3_fully_assessed IS DISTINCT FROM e.teacher_assessed
       OR c.ap3_review_status IS DISTINCT FROM e.teacher_status) AS input_mismatch,
  (SELECT COUNT(*) FROM c JOIN expected e USING (city_mun_psgc_code)
    LEFT JOIN expected_rank q USING (city_mun_psgc_code)
    WHERE c.classroom_priority_group IS DISTINCT FROM CASE WHEN NOT COALESCE(e.ap2_assessed, FALSE) THEN 'data_review'
            WHEN e.affected_learners > 0 THEN 'reported_congestion_screen'
            ELSE 'no_reported_congestion_screen' END
       OR c.classroom_priority_rank IS DISTINCT FROM q.queue_rank
       OR c.rule_version IS DISTINCT FROM 'D-062') AS queue_mismatch,
  (SELECT COUNT(*) FROM c JOIN expected_gap g USING (city_mun_psgc_code)
    LEFT JOIN expected_composite x USING (city_mun_psgc_code)
    WHERE NOT COALESCE(ABS(c.ap1_baseline_school_age_population_per_school - g.ap1_baseline) < 1e-9, c.ap1_baseline_school_age_population_per_school IS NULL AND g.ap1_baseline IS NULL)
       OR NOT COALESCE(ABS(c.ap1_gap - g.ap1_gap) < 1e-9, c.ap1_gap IS NULL AND g.ap1_gap IS NULL)
       OR NOT COALESCE(ABS(c.ap2_gap - g.ap2_gap) < 1e-9, c.ap2_gap IS NULL AND g.ap2_gap IS NULL)
       OR NOT COALESCE(ABS(c.ap3_gap - g.ap3_gap) < 1e-9, c.ap3_gap IS NULL AND g.ap3_gap IS NULL)
       OR NOT COALESCE(ABS(c.ap1_score - x.ap1_score) < 1e-9, c.ap1_score IS NULL AND x.ap1_score IS NULL)
       OR NOT COALESCE(ABS(c.ap2_score - x.ap2_score) < 1e-9, c.ap2_score IS NULL AND x.ap2_score IS NULL)
       OR NOT COALESCE(ABS(c.ap3_score - x.ap3_score) < 1e-9, c.ap3_score IS NULL AND x.ap3_score IS NULL)
       OR NOT COALESCE(ABS(c.composite_score - x.composite) < 1e-9, c.composite_score IS NULL AND x.composite IS NULL)
       OR c.bq_priority_rank IS DISTINCT FROM x.composite_rank
       OR c.bq_priority_group IS DISTINCT FROM CASE WHEN x.city_mun_psgc_code IS NULL THEN 'data_review' ELSE 'ranked' END
       OR (x.city_mun_psgc_code IS NULL AND (c.ap1_score IS NOT NULL OR c.ap2_score IS NOT NULL
           OR c.ap3_score IS NOT NULL OR c.composite_score IS NOT NULL OR c.bq_rank_without_ap1 IS NOT NULL
           OR c.bq_rank_without_ap2 IS NOT NULL OR c.bq_rank_without_ap3 IS NOT NULL OR c.bq_rank_min_max IS NOT NULL))
    ) AS composite_mismatch,
  (SELECT COUNT(*) FROM (SELECT 'without_ap1' AS variant UNION ALL SELECT 'without_ap2' UNION ALL SELECT 'without_ap3'
      UNION ALL SELECT 'min_max_scores') AS v
    FULL OUTER JOIN sensitivity s USING (variant)
    WHERE v.variant IS NULL OR s.variant IS NULL OR s.ranked_lgus IS DISTINCT FROM (SELECT COUNT(*) FROM expected_composite)
       OR s.rule_version IS DISTINCT FROM 'D-062') AS sensitivity_mismatch,
  (SELECT COALESCE(COUNT_IF(classroom_priority_group = 'reported_congestion_screen'), 0) FROM c) AS queued_lgus,
  (SELECT COALESCE(COUNT_IF(classroom_priority_group = 'data_review'), 0) FROM c) AS data_review_lgus;
SET VARIABLE analytics_gate_owner_sql = 'ALTER TABLE ' || session.analytics_gate_summary || ' OWNER TO `reached-hq`';
EXECUTE IMMEDIATE analytics_gate_owner_sql;

INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'lgu_priority_matrix', 'analytics', 'edu_access.06-analytics.lgu_priority_matrix_candidate',
       check_name, status, expected, actual, current_timestamp(), :code_revision
FROM (
  SELECT 'rows_match_regular_lgus' AS check_name, CASE WHEN rows = expected_rows THEN 'PASS' ELSE 'FAIL' END AS status,
         CAST(expected_rows AS STRING) AS expected, CAST(rows AS STRING) AS actual FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'key_unique', CASE WHEN duplicate_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(duplicate_keys AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'lgu_membership_reconciles', CASE WHEN lgu_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(lgu_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'inputs_match_ap_outputs', CASE WHEN input_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(input_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'derived_values_reconcile', CASE WHEN composite_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(composite_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'counts_reconcile', CASE WHEN sensitivity_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(sensitivity_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'classroom_queue_follows_d060', CASE WHEN queue_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(queue_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'classroom_queue_lgus', 'PASS', CAST(NULL AS STRING), CAST(queued_lgus AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'classroom_data_review_lgus', 'PASS', CAST(NULL AS STRING), CAST(data_review_lgus AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
) AS checks;

DROP TABLE IF EXISTS IDENTIFIER(session.analytics_gate_summary);

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for lgu_priority_matrix: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') ELSE 1 END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'lgu_priority_matrix' AND layer = 'analytics' AND status = 'FAIL'
  AND checked_at_utc >= session.analytics_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.lgu_priority_matrix USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.lgu_priority_matrix_candidate;
COMMENT ON TABLE edu_access.`06-analytics`.lgu_priority_matrix IS 'LGU priority table under D-062: equal-weight composite of AP1 to AP3 gaps as percentile scores, with the D-060 classroom queue as AP2 drill-down. Relative review priority, not a shortage.';
ALTER TABLE edu_access.`06-analytics`.lgu_priority_matrix OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.bq_priority_sensitivity USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.bq_priority_sensitivity_candidate;
COMMENT ON TABLE edu_access.`06-analytics`.bq_priority_sensitivity IS 'D-062 robustness: rank correlation and top-50 overlap when one AP is dropped or min-max replaces percentile scores.';
ALTER TABLE edu_access.`06-analytics`.bq_priority_sensitivity OWNER TO `reached-hq`;
