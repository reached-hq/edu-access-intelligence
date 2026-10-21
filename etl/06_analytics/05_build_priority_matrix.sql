-- LGU priority table under D-062, from the published AP1 to AP3 outputs, with AP4 as context.
-- grain: one regular city or municipality, SY 2023-24.
-- BQ composite (D-062), each step cited in config/analytics_benchmarks.json under bq:
--   1. gap per AP = GREATEST(0, ratio / baseline - 1). AP2: pooled learners per reported room against PIDS 50.
--      AP3: reference teachers (eligible learners / D-059 reference, summed over offered levels) against reported
--      teachers. AP1: school-age population per public school against the median of assessed LGUs of the same type,
--      because no published AP1 ratio exists (D-061).
--   2. each gap becomes a 0-100 score with 100 * PERCENT_RANK() among LGUs with all three gaps (OECD/JRC 2008
--      ranking normalisation; CDC/ATSDR SVI percentile rank, (rank - 1) / (n - 1)). a zero gap scores 0.
--   3. composite = equal-weight mean of the three scores (OECD/JRC 2008 linear aggregation, equal weights).
--   4. bq_priority_rank = DENSE_RANK() on the composite, highest first; exact ties share a rank.
-- an LGU missing any AP (coverage gate or NULL ratio) is data_review with no score: missing is never 0.
-- robustness: ranks without each AP and with min-max scores, summarised in bq_priority_sensitivity.
-- D-060's classroom queue stays as AP2's school-level drill-down; it is not the BQ ranking.

CREATE SCHEMA IF NOT EXISTS edu_access.`06-analytics`;
ALTER SCHEMA edu_access.`06-analytics` OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.lgu_priority_matrix_candidate USING DELTA AS
WITH joined AS (
  SELECT
    l.city_mun_psgc_code, l.city_mun_name, l.lgu_type, l.province_psgc_code, l.province_name,
    l.region_psgc_code, l.region_name,
    CAST('2023-24' AS STRING) AS school_year,
    a.learners_per_public_school AS ap1_learners_per_public_school,
    a.coverage_pct AS ap1_coverage_pct,
    a.is_assessed AS ap1_assessed,
    a.public_school_enrollment AS ap1_public_school_enrollment,
    a.school_age_population_per_public_school AS ap1_school_age_population_per_public_school,
    a.barangays_without_public_es AS ap1_barangays_without_public_es,
    a.barangays_without_public_es_pct AS ap1_barangays_without_public_es_pct,
    a.es_count_is_upper_bound AS ap1_es_count_is_upper_bound,
    a.benchmark_status AS ap1_school_presence_status,
    a.isolated_es_school_count AS ap1_isolated_es_school_count,
    a.spacing_benchmark_status AS ap1_spacing_status,
    b.learners_per_classroom AS ap2_learners_per_reported_room,
    b.learner_coverage_pct AS ap2_learner_coverage_pct,
    b.is_assessed AS ap2_assessed,
    b.congested_school_count AS ap2_screened_congested_school_count,
    b.learners_in_congested_schools AS ap2_affected_learners,
    b.congested_learner_share_pct AS ap2_affected_learner_share_pct,
    b.benchmark_status AS ap2_screen_status,
    c.es_learners_per_teacher AS ap3_es_learners_per_teacher,
    c.jhs_learners_per_teacher AS ap3_jhs_learners_per_teacher,
    c.shs_learners_per_teacher AS ap3_shs_learners_per_teacher,
    c.is_assessed AS ap3_fully_assessed,
    c.benchmark_status AS ap3_review_status,
    d.ap4_gap_2020, d.ap4_gap_2024, d.ap4_gap_rate_2020_pct, d.ap4_gap_rate_2024_pct, d.ap4_gap_change,
    d.ap4_enrollment_trend, d.ap4_enrollment_change_pct
  FROM edu_access.`05-gold`.dim_city_municipality AS l
  LEFT JOIN edu_access.`06-analytics`.ap1_school_provision AS a USING (city_mun_psgc_code)
  LEFT JOIN edu_access.`06-analytics`.ap2_classroom_pressure AS b USING (city_mun_psgc_code)
  LEFT JOIN edu_access.`06-analytics`.ap3_teacher_pressure AS c USING (city_mun_psgc_code)
  LEFT JOIN (
    SELECT city_mun_psgc_code,
           MAX(CASE WHEN school_year = '2020-21' THEN population_enrollment_gap END) AS ap4_gap_2020,
           MAX(CASE WHEN school_year = '2024-25' THEN population_enrollment_gap END) AS ap4_gap_2024,
           MAX(CASE WHEN school_year = '2020-21' THEN 100 * gap_share END) AS ap4_gap_rate_2020_pct,
           MAX(CASE WHEN school_year = '2024-25' THEN 100 * gap_share END) AS ap4_gap_rate_2024_pct,
           CASE WHEN BOOL_AND(is_2020_2024_geography_comparable)
                THEN MAX(CASE WHEN school_year = '2024-25' THEN population_enrollment_gap END)
                   - MAX(CASE WHEN school_year = '2020-21' THEN population_enrollment_gap END) END AS ap4_gap_change,
           MAX(enrollment_trend) AS ap4_enrollment_trend,
           MAX(enrollment_change_pct_first_to_latest) AS ap4_enrollment_change_pct
    FROM edu_access.`06-analytics`.ap4_enrollment_trend
    WHERE member_type = 'regular'
    GROUP BY city_mun_psgc_code
  ) AS d USING (city_mun_psgc_code)
  WHERE l.member_type = 'regular'
), classroom_ranked AS (
  SELECT city_mun_psgc_code,
         DENSE_RANK() OVER (ORDER BY ap2_affected_learners DESC,
           ap2_screened_congested_school_count DESC,
           ap2_learners_per_reported_room DESC) AS classroom_priority_rank
  FROM joined
  WHERE ap2_assessed AND ap2_affected_learners > 0
), ap1_baseline AS (
  SELECT lgu_type,
         PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ap1_school_age_population_per_public_school) AS ap1_baseline
  FROM joined
  WHERE ap1_assessed AND ap1_school_age_population_per_public_school IS NOT NULL
  GROUP BY lgu_type
), gaps AS (
  SELECT j.city_mun_psgc_code, b.ap1_baseline AS ap1_baseline_school_age_population_per_school,
         CASE WHEN j.ap1_assessed THEN GREATEST(0.0,
           j.ap1_school_age_population_per_public_school / NULLIF(b.ap1_baseline, 0) - 1) END AS ap1_gap,
         CASE WHEN j.ap2_assessed THEN GREATEST(0.0, j.ap2_learners_per_reported_room / 50.0 - 1) END AS ap2_gap,
         t.reference_teachers AS ap3_reference_teachers, t.reported_teachers AS ap3_reported_teachers,
         CASE WHEN j.ap3_fully_assessed THEN GREATEST(0.0,
           t.reference_teachers / NULLIF(t.reported_teachers, 0) - 1) END AS ap3_gap
  FROM joined AS j
  LEFT JOIN ap1_baseline AS b USING (lgu_type)
  LEFT JOIN (
    SELECT city_mun_psgc_code,
           COALESCE(CASE WHEN es_offered_school_count > 0 THEN es_eligible_learners / 35.0 END, 0)
             + COALESCE(CASE WHEN jhs_offered_school_count > 0 THEN jhs_eligible_learners / 36.0 END, 0)
             + COALESCE(CASE WHEN shs_offered_school_count > 0 THEN shs_eligible_learners / (80.0 / 3) END, 0)
             AS reference_teachers,
           CAST(COALESCE(es_teacher_count, 0) + COALESCE(jhs_teacher_count, 0) + COALESCE(shs_teacher_count, 0) AS DOUBLE)
             AS reported_teachers
    FROM edu_access.`06-analytics`.ap3_teacher_pressure
  ) AS t USING (city_mun_psgc_code)
), scored AS (
  SELECT g.*,
         100 * PERCENT_RANK() OVER (ORDER BY g.ap1_gap) AS ap1_score,
         100 * PERCENT_RANK() OVER (ORDER BY g.ap2_gap) AS ap2_score,
         100 * PERCENT_RANK() OVER (ORDER BY g.ap3_gap) AS ap3_score,
         100 * (g.ap1_gap - MIN(g.ap1_gap) OVER ()) / NULLIF(MAX(g.ap1_gap) OVER () - MIN(g.ap1_gap) OVER (), 0) AS ap1_min_max,
         100 * (g.ap2_gap - MIN(g.ap2_gap) OVER ()) / NULLIF(MAX(g.ap2_gap) OVER () - MIN(g.ap2_gap) OVER (), 0) AS ap2_min_max,
         100 * (g.ap3_gap - MIN(g.ap3_gap) OVER ()) / NULLIF(MAX(g.ap3_gap) OVER () - MIN(g.ap3_gap) OVER (), 0) AS ap3_min_max
  FROM gaps AS g
  WHERE g.ap1_gap IS NOT NULL AND g.ap2_gap IS NOT NULL AND g.ap3_gap IS NOT NULL
), composite AS (
  SELECT s.*,
         (s.ap1_score + s.ap2_score + s.ap3_score) / 3 AS composite_score,
         (COALESCE(s.ap1_min_max, 0) + COALESCE(s.ap2_min_max, 0) + COALESCE(s.ap3_min_max, 0)) / 3 AS composite_min_max
  FROM scored AS s
), ranked AS (
  SELECT c.city_mun_psgc_code, c.ap1_score, c.ap2_score, c.ap3_score, c.composite_score,
         DENSE_RANK() OVER (ORDER BY c.composite_score DESC) AS bq_priority_rank,
         DENSE_RANK() OVER (ORDER BY (c.ap2_score + c.ap3_score) / 2 DESC) AS bq_rank_without_ap1,
         DENSE_RANK() OVER (ORDER BY (c.ap1_score + c.ap3_score) / 2 DESC) AS bq_rank_without_ap2,
         DENSE_RANK() OVER (ORDER BY (c.ap1_score + c.ap2_score) / 2 DESC) AS bq_rank_without_ap3,
         DENSE_RANK() OVER (ORDER BY c.composite_min_max DESC) AS bq_rank_min_max
  FROM composite AS c
)
SELECT j.*,
       CASE WHEN NOT COALESCE(j.ap2_assessed, FALSE) THEN 'data_review'
            WHEN j.ap2_affected_learners > 0 THEN 'reported_congestion_screen'
            ELSE 'no_reported_congestion_screen' END AS classroom_priority_group,
       r.classroom_priority_rank,
       CASE WHEN NOT COALESCE(j.ap2_assessed, FALSE)
              THEN 'Classroom data do not pass the coverage gate, no classroom priority is assigned'
            WHEN j.ap2_affected_learners > 0
              THEN 'PIDS-style illustrative school screen, ordered by affected learners, affected schools, then pooled reported-room ratio'
            ELSE 'No school crosses the illustrative reported-room screen, this is not proof of classroom adequacy'
       END AS classroom_priority_basis,
       g.ap1_baseline_school_age_population_per_school, g.ap1_gap, g.ap2_gap,
       g.ap3_reference_teachers, g.ap3_reported_teachers, g.ap3_gap,
       k.ap1_score, k.ap2_score, k.ap3_score, k.composite_score,
       CASE WHEN k.city_mun_psgc_code IS NOT NULL THEN 'ranked' ELSE 'data_review' END AS bq_priority_group,
       k.bq_priority_rank, k.bq_rank_without_ap1, k.bq_rank_without_ap2, k.bq_rank_without_ap3, k.bq_rank_min_max,
       CASE WHEN k.city_mun_psgc_code IS NOT NULL
              THEN 'Relative review priority against published references (AP2, AP3) and the same-type median (AP1), not a shortage'
            ELSE 'At least one of AP1 to AP3 does not pass its coverage gate, so no composite score is assigned'
       END AS bq_priority_basis,
       'D-062' AS rule_version,
       :code_revision AS code_revision
FROM joined AS j
LEFT JOIN classroom_ranked AS r USING (city_mun_psgc_code)
LEFT JOIN gaps AS g USING (city_mun_psgc_code)
LEFT JOIN ranked AS k USING (city_mun_psgc_code);

COMMENT ON TABLE edu_access.`06-analytics`.lgu_priority_matrix_candidate IS 'Unpublished LGU priority table under D-062. Do not read: use lgu_priority_matrix.';
ALTER TABLE edu_access.`06-analytics`.lgu_priority_matrix_candidate OWNER TO `reached-hq`;

-- how much the ranking moves when one AP is dropped or min-max replaces percentile scores (OECD/JRC 2008, step 7).
-- spearman is the correlation of the two dense ranks; top-50 overlap counts LGUs in the top 50 under both.
CREATE OR REPLACE TABLE edu_access.`06-analytics`.bq_priority_sensitivity_candidate USING DELTA AS
WITH m AS (
  SELECT * FROM edu_access.`06-analytics`.lgu_priority_matrix_candidate WHERE bq_priority_group = 'ranked'
), variants AS (
  SELECT 'without_ap1' AS variant, bq_priority_rank AS base_rank, bq_rank_without_ap1 AS variant_rank FROM m
  UNION ALL SELECT 'without_ap2', bq_priority_rank, bq_rank_without_ap2 FROM m
  UNION ALL SELECT 'without_ap3', bq_priority_rank, bq_rank_without_ap3 FROM m
  UNION ALL SELECT 'min_max_scores', bq_priority_rank, bq_rank_min_max FROM m
)
SELECT v.variant, COUNT(v.base_rank) AS ranked_lgus,
       CORR(CAST(v.base_rank AS DOUBLE), CAST(v.variant_rank AS DOUBLE)) AS spearman_rank_correlation,
       COUNT_IF(v.base_rank <= 50 AND v.variant_rank <= 50) AS top_50_overlap,
       COUNT_IF(v.base_rank <= 50) AS top_50_lgus,
       'D-062' AS rule_version,
       :code_revision AS code_revision
FROM (SELECT * FROM variants UNION ALL
      SELECT * FROM VALUES ('without_ap1', NULL, NULL), ('without_ap2', NULL, NULL), ('without_ap3', NULL, NULL),
        ('min_max_scores', NULL, NULL) AS e(variant, base_rank, variant_rank)) AS v
GROUP BY v.variant;

COMMENT ON TABLE edu_access.`06-analytics`.bq_priority_sensitivity_candidate IS 'Unpublished D-062 sensitivity summary. Do not read: use bq_priority_sensitivity.';
ALTER TABLE edu_access.`06-analytics`.bq_priority_sensitivity_candidate OWNER TO `reached-hq`;
