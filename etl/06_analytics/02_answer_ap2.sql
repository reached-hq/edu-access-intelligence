-- ap2 classroom-pressure screening and relative review priority (D-061).
-- outputs: one denominator-usable public school, and one regular city or municipality, for SY 2023-24.
-- measure: enrollment in denominator-usable schools / reported instructional rooms in the same schools (D-047).
-- coverage gate: learner coverage, the share of learners in schools with a usable room count, at least 90%.
-- school coverage is shown beside it, with incomplete and blank-enrollment schools in its denominator.
-- absolute screen: each denominator-usable school at >=50 learners per reported instructional room is screened as
-- congested, following the aggregation used in PIDS Discussion Paper 2025-10. Relative screen: PERCENT_RANK over
-- every denominator-usable school nationally; >=0.90 is a top-decile review flag adapted from CDC/ATSDR SVI 2022.
-- Both are review signals, not official DepEd indicators, shortage counts, or classroom entitlements.

CREATE SCHEMA IF NOT EXISTS edu_access.`06-analytics`;
ALTER SCHEMA edu_access.`06-analytics` OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap2_school_classroom_pressure_candidate USING DELTA AS
WITH enrollment AS (
  SELECT school_id, city_mun_psgc_code,
         MAX(CASE WHEN is_offered AND learner_count > 0 THEN 1 ELSE 0 END) AS is_active,
         COUNT_IF(is_offered AND learner_count IS NULL) AS incomplete_levels,
         SUM(CASE WHEN is_offered AND learner_count IS NOT NULL THEN learner_count ELSE 0 END) AS total_learners
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year = '2023-24' AND sector = 'Public' AND psgc_match_status = 'matched'
  GROUP BY school_id, city_mun_psgc_code
), usable AS (
  SELECT e.school_id, e.city_mun_psgc_code, CAST('2023-24' AS STRING) AS school_year,
         CAST(e.total_learners AS BIGINT) AS total_learners,
         CAST(c.instructional_classrooms_total AS BIGINT) AS reported_instructional_rooms,
         CAST(e.total_learners AS DOUBLE) / c.instructional_classrooms_total AS learners_per_reported_room
  FROM enrollment AS e
  JOIN edu_access.`05-gold`.dim_city_municipality AS l
    ON l.city_mun_psgc_code = e.city_mun_psgc_code AND l.member_type = 'regular'
  JOIN edu_access.`05-gold`.fact_school_classroom_capacity AS c
    ON c.school_id = e.school_id AND c.school_year = '2023-24'
  WHERE e.is_active = 1 AND e.incomplete_levels = 0 AND c.instructional_classrooms_total > 0
), ranked AS (
  SELECT u.*,
         CAST(PERCENT_RANK() OVER (ORDER BY learners_per_reported_room) AS DOUBLE)
           AS classroom_pressure_percentile,
         COUNT(*) OVER () AS percentile_comparison_school_count
  FROM usable AS u
)
SELECT r.*,
       r.learners_per_reported_room >= 50 AS passes_pids_style_screen,
       r.classroom_pressure_percentile >= 0.90 AS is_top_decile_relative_pressure,
       CAST(0.90 AS DOUBLE) AS relative_pressure_cutoff_percentile,
       'national denominator-usable public schools, SY 2023-24' AS percentile_comparison_scope,
       'Relative review position, not an official shortage, construction entitlement, or DepEd priority' AS interpretation,
       :code_revision AS code_revision
FROM ranked AS r;

COMMENT ON TABLE edu_access.`06-analytics`.ap2_school_classroom_pressure_candidate IS 'Unpublished school-level AP2 relative classroom-pressure review output. Do not read: use ap2_school_classroom_pressure.';
ALTER TABLE edu_access.`06-analytics`.ap2_school_classroom_pressure_candidate OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap2_classroom_pressure_candidate USING DELTA AS
WITH lgus AS (
  SELECT city_mun_psgc_code, city_mun_name, lgu_type, province_psgc_code, province_name,
         region_psgc_code, region_name
  FROM edu_access.`05-gold`.dim_city_municipality
  WHERE member_type = 'regular'
), enrollment AS (
  SELECT school_id, city_mun_psgc_code,
         MAX(CASE WHEN is_offered AND learner_count > 0 THEN 1 ELSE 0 END) AS is_active,
         COUNT_IF(is_offered AND learner_count IS NULL) AS incomplete_levels,
         COUNT_IF(is_offered) > 0 AND COUNT_IF(is_offered AND learner_count IS NOT NULL) = 0 AS is_blank,
         SUM(CASE WHEN is_offered AND learner_count IS NOT NULL THEN learner_count ELSE 0 END) AS complete_level_learners
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year = '2023-24' AND sector = 'Public' AND psgc_match_status = 'matched'
  GROUP BY school_id, city_mun_psgc_code
), schools AS (
  SELECT e.*, c.instructional_classrooms_total,
         e.incomplete_levels = 0 AS enrollment_complete,
         e.is_active = 1 AND e.incomplete_levels = 0 AND c.instructional_classrooms_total > 0 AS in_ratio,
         CASE WHEN e.incomplete_levels = 0 THEN e.complete_level_learners END AS total_learners
  FROM enrollment AS e
  LEFT JOIN edu_access.`05-gold`.fact_school_classroom_capacity AS c
    ON c.school_id = e.school_id AND c.school_year = '2023-24'
), comparison AS (
  SELECT COUNT(*) AS percentile_comparison_school_count
  FROM edu_access.`06-analytics`.ap2_school_classroom_pressure_candidate
), metrics AS (
  SELECT l.*, CAST('2023-24' AS STRING) AS school_year,
         COALESCE(COUNT_IF(s.is_active = 1), 0) AS active_public_school_count,
         COALESCE(COUNT_IF(s.is_active = 1 AND s.instructional_classrooms_total > 0), 0) AS usable_room_school_count,
         COALESCE(COUNT_IF(s.in_ratio), 0) AS ratio_school_count,
         COALESCE(COUNT_IF(s.is_active = 1 AND NOT s.enrollment_complete), 0) AS incomplete_enrollment_school_count,
         COALESCE(COUNT_IF(s.is_blank), 0) AS blank_enrollment_school_count,
         COALESCE(COUNT_IF(s.is_active = 1 AND s.instructional_classrooms_total IS NULL), 0) AS missing_room_school_count,
         COALESCE(COUNT_IF(s.is_active = 1 AND s.instructional_classrooms_total = 0), 0) AS zero_room_school_count,
         CAST(COALESCE(SUM(CASE WHEN s.is_active = 1 AND s.enrollment_complete THEN s.total_learners ELSE 0 END), 0) AS BIGINT)
           AS public_school_enrollment,
         CAST(COALESCE(SUM(CASE WHEN s.in_ratio THEN s.total_learners ELSE 0 END), 0) AS BIGINT) AS eligible_learners,
         CAST(COALESCE(SUM(CASE WHEN s.in_ratio THEN s.instructional_classrooms_total ELSE 0 END), 0) AS BIGINT)
           AS reported_instructional_classrooms,
         COALESCE(MAX(r.congested_school_count), 0) AS congested_school_count,
         CAST(COALESCE(MAX(r.learners_in_congested_schools), 0) AS BIGINT) AS learners_in_congested_schools,
         COALESCE(MAX(r.top_decile_school_count), 0) AS top_decile_school_count,
         CAST(COALESCE(MAX(r.learners_in_top_decile_schools), 0) AS BIGINT) AS learners_in_top_decile_schools,
         n.percentile_comparison_school_count
  FROM lgus AS l
  CROSS JOIN comparison AS n
  LEFT JOIN schools AS s USING (city_mun_psgc_code)
  LEFT JOIN (
    SELECT city_mun_psgc_code,
           COUNT_IF(passes_pids_style_screen) AS congested_school_count,
           SUM(CASE WHEN passes_pids_style_screen THEN total_learners ELSE 0 END) AS learners_in_congested_schools,
           COUNT_IF(is_top_decile_relative_pressure) AS top_decile_school_count,
           SUM(CASE WHEN is_top_decile_relative_pressure THEN total_learners ELSE 0 END)
             AS learners_in_top_decile_schools
    FROM edu_access.`06-analytics`.ap2_school_classroom_pressure_candidate
    GROUP BY city_mun_psgc_code
  ) AS r USING (city_mun_psgc_code)
  GROUP BY l.city_mun_psgc_code, l.city_mun_name, l.lgu_type, l.province_psgc_code, l.province_name,
           l.region_psgc_code, l.region_name, n.percentile_comparison_school_count
), ratios AS (
  SELECT m.*,
         CAST(m.eligible_learners AS DOUBLE) / NULLIF(m.reported_instructional_classrooms, 0) AS learners_per_classroom,
         CAST(100.0 * m.learners_in_congested_schools / NULLIF(m.public_school_enrollment, 0) AS DOUBLE)
           AS congested_learner_share_pct,
         CAST(100.0 * m.learners_in_top_decile_schools / NULLIF(m.public_school_enrollment, 0) AS DOUBLE)
           AS top_decile_learner_share_pct,
         CAST(100.0 * m.ratio_school_count
           / NULLIF(m.active_public_school_count + m.blank_enrollment_school_count, 0) AS DOUBLE) AS school_coverage_pct,
         CAST(100.0 * m.eligible_learners / NULLIF(m.public_school_enrollment, 0) AS DOUBLE) AS learner_coverage_pct
  FROM metrics AS m
), gated AS (
  SELECT *,
         CASE WHEN active_public_school_count = 0 THEN 'no active public school'
              WHEN learners_per_classroom IS NULL THEN 'no usable classroom denominator'
              WHEN learner_coverage_pct < 90 THEN 'learner coverage below 90%'
         END AS not_assessed_reason
  FROM ratios
)
SELECT g.*,
       g.not_assessed_reason IS NULL AS is_assessed,
       CAST(50.0 AS DOUBLE) AS congestion_benchmark,
       CAST(0.90 AS DOUBLE) AS relative_pressure_cutoff_percentile,
       'national denominator-usable public schools, SY 2023-24' AS percentile_comparison_scope,
       CASE WHEN g.not_assessed_reason IS NOT NULL THEN 'not assessed'
            WHEN g.congested_school_count > 0 THEN 'reported congestion identified'
            ELSE 'no reported congestion identified' END AS benchmark_status,
       CASE WHEN g.not_assessed_reason IS NOT NULL THEN 'not assessed'
            WHEN g.top_decile_school_count > 0 THEN 'top-decile relative pressure identified'
            ELSE 'no top-decile relative pressure identified' END AS relative_pressure_status,
       'PIDS-style illustrative school screen at >=50 learners per reported NSBI instructional room' AS measure_label,
       :code_revision AS code_revision
FROM gated AS g;

COMMENT ON TABLE edu_access.`06-analytics`.ap2_classroom_pressure_candidate IS 'Unpublished AP2 build. Do not read: use ap2_classroom_pressure.';
ALTER TABLE edu_access.`06-analytics`.ap2_classroom_pressure_candidate OWNER TO `reached-hq`;
