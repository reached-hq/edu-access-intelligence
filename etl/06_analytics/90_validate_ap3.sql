-- AP3 validation gate (#146).
-- Reads published Gold inputs and checks the AP3 candidate.
-- A failed candidate never replaces the last published output.

DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();

-- Independently reconstruct the eligible school-level rows from Gold.
CREATE OR REPLACE TEMPORARY VIEW ap3_expected_school_rows AS
WITH active AS (
  SELECT school_id, school_year
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE sector = 'Public'
    AND psgc_match_status = 'matched'
    AND city_mun_psgc_code NOT IN ('UNKNOWN', 'EXCLUDED')
    AND is_offered
    AND learner_count > 0
  GROUP BY school_id, school_year
)
SELECT
  e.school_id,
  e.school_year,
  e.education_level_code,
  e.city_mun_psgc_code,
  e.annex_status,
  e.learner_count,
  t.school_id IS NOT NULL AS has_capacity_row,
  t.teacher_count,
  t.sef_provincial_teacher_count,
  t.sef_city_municipal_teacher_count,
  t.lgu_funded_teacher_count,
  t.other_funded_teacher_count,

  COALESCE(t.teacher_count > 0, FALSE) AS usable,

  COALESCE(
    e.annex_status = 'Annex/Extension School'
    AND t.teacher_count = 0,
    FALSE
  ) AS annex_zero

FROM edu_access.`05-gold`.fact_school_enrollment AS e

JOIN active AS a
  ON a.school_id = e.school_id
  AND a.school_year = e.school_year

JOIN edu_access.`05-gold`.dim_city_municipality AS g
  ON g.city_mun_psgc_code = e.city_mun_psgc_code
  AND g.member_type = 'regular'

LEFT JOIN edu_access.`05-gold`.fact_school_teacher_capacity AS t
  ON t.school_id = e.school_id
  AND t.school_year = e.school_year
  AND t.education_level_code = e.education_level_code

WHERE e.sector = 'Public'
  AND e.psgc_match_status = 'matched'
  AND e.is_offered;

CREATE OR REPLACE TEMPORARY VIEW ap3_expected_metrics AS
SELECT
  city_mun_psgc_code,
  school_year,
  education_level_code,

  COUNT(DISTINCT school_id) AS schools,

  COUNT(DISTINCT CASE
    WHEN learner_count IS NULL THEN school_id
  END) AS incomplete_schools,

  COUNT(DISTINCT CASE
    WHEN usable THEN school_id
  END) AS usable_schools,

  COUNT(DISTINCT CASE
    WHEN NOT has_capacity_row THEN school_id
  END) AS missing_capacity_schools,

  COUNT(DISTINCT CASE
    WHEN teacher_count IS NULL THEN school_id
  END) AS missing_teacher_schools,

  COUNT(DISTINCT CASE
    WHEN teacher_count = 0 THEN school_id
  END) AS zero_teacher_schools,

  COUNT(DISTINCT CASE
    WHEN annex_zero THEN school_id
  END) AS annex_zero_schools,

  SUM(CASE
    WHEN annex_zero THEN learner_count
    ELSE 0
  END) AS annex_zero_learners,

  SUM(CASE
    WHEN teacher_count = 0 AND NOT annex_zero THEN learner_count
    ELSE 0
  END) AS learners_without_teachers,

  SUM(learner_count) AS learners,

  SUM(CASE
    WHEN usable OR annex_zero THEN learner_count
  END) AS included_learners,

  SUM(CASE
    WHEN usable AND learner_count IS NOT NULL THEN teacher_count
  END) AS teachers,

  SUM(CASE
    WHEN usable AND learner_count IS NOT NULL
    THEN sef_provincial_teacher_count
  END) AS provincial_teachers,

  SUM(CASE
    WHEN usable AND learner_count IS NOT NULL
    THEN sef_city_municipal_teacher_count
  END) AS city_municipal_teachers,

  SUM(CASE
    WHEN usable AND learner_count IS NOT NULL
    THEN lgu_funded_teacher_count
  END) AS lgu_teachers,

  SUM(CASE
    WHEN usable AND learner_count IS NOT NULL
    THEN other_funded_teacher_count
  END) AS other_teachers

FROM ap3_expected_school_rows
GROUP BY
  city_mun_psgc_code,
  school_year,
  education_level_code;

CREATE OR REPLACE TEMPORARY VIEW ap3_gate_summary AS
WITH candidate AS (
  SELECT *
  FROM edu_access.`06-analytics`.ap3_teacher_pressure_candidate
),

availability AS (
  SELECT
    school_year,
    MAX(
      CASE
        WHEN source_id = 'deped_personnel' AND has_data THEN 1
        ELSE 0
      END
    ) = 1 AS personnel_available
  FROM edu_access.`05-gold`.fact_school_year_source_availability
  GROUP BY school_year
),

expected_keys AS (
  SELECT
    c.city_mun_psgc_code,
    y.school_year,
    l.education_level_code
  FROM edu_access.`05-gold`.dim_city_municipality AS c

  CROSS JOIN (
    SELECT DISTINCT school_year
    FROM edu_access.`05-gold`.fact_school_enrollment
  ) AS y

  CROSS JOIN (
    SELECT *
    FROM VALUES ('ES'), ('JHS'), ('SHS')
      AS v(education_level_code)
  ) AS l

  WHERE c.member_type = 'regular'
),

joined AS (
  SELECT
    o.*,

    g.city_mun_name AS expected_city_name,
    g.lgu_type AS expected_lgu_type,
    g.province_psgc_code AS expected_province_code,
    g.province_name AS expected_province_name,
    g.region_psgc_code AS expected_region_code,
    g.region_name AS expected_region_name,

    COALESCE(a.personnel_available, FALSE)
      AS expected_personnel_available,

    m.schools,
    m.incomplete_schools,
    m.usable_schools,
    m.missing_capacity_schools,
    m.missing_teacher_schools,
    m.zero_teacher_schools,
    m.annex_zero_schools,
    m.annex_zero_learners,
    m.learners_without_teachers,
    m.learners,
    m.included_learners,
    m.teachers,
    m.provincial_teachers,
    m.city_municipal_teachers,
    m.lgu_teachers,
    m.other_teachers

  FROM candidate AS o

  LEFT JOIN edu_access.`05-gold`.dim_city_municipality AS g
    ON g.city_mun_psgc_code = o.city_mun_psgc_code
    AND g.member_type = 'regular'

  LEFT JOIN availability AS a
    ON a.school_year = o.school_year

  LEFT JOIN ap3_expected_metrics AS m
    ON m.city_mun_psgc_code = o.city_mun_psgc_code
    AND m.school_year = o.school_year
    AND m.education_level_code = o.education_level_code
)

SELECT
  (
    SELECT COUNT(*)
    FROM (
      SELECT city_mun_psgc_code, school_year, education_level_code
      FROM candidate
      GROUP BY city_mun_psgc_code, school_year, education_level_code
      HAVING COUNT(*) > 1
    ) AS duplicates
  ) AS duplicate_output_keys,

  (
    SELECT COUNT(*)
    FROM candidate
    WHERE city_mun_psgc_code IS NULL
      OR school_year IS NULL
      OR education_level_code IS NULL
  ) AS null_output_keys,

  (
    SELECT COUNT(*)
    FROM expected_keys AS e
    FULL OUTER JOIN candidate AS o
      ON o.city_mun_psgc_code = e.city_mun_psgc_code
      AND o.school_year = e.school_year
      AND o.education_level_code = e.education_level_code
    WHERE e.city_mun_psgc_code IS NULL
      OR o.city_mun_psgc_code IS NULL
  ) AS mismatched_grid_keys,

  (
    SELECT COUNT(*)
    FROM joined
    WHERE city_mun_name IS DISTINCT FROM expected_city_name
      OR lgu_type IS DISTINCT FROM expected_lgu_type
      OR province_psgc_code IS DISTINCT FROM expected_province_code
      OR province_name IS DISTINCT FROM expected_province_name
      OR region_psgc_code IS DISTINCT FROM expected_region_code
      OR region_name IS DISTINCT FROM expected_region_name
  ) AS identity_mismatches,

  (
    SELECT COUNT(*)
    FROM joined
    WHERE personnel_available
      IS DISTINCT FROM expected_personnel_available
  ) AS availability_mismatches,

  (
    SELECT COUNT(*)
    FROM joined
    WHERE public_school_count IS DISTINCT FROM COALESCE(schools, 0)
      OR incomplete_enrollment_school_count
        IS DISTINCT FROM COALESCE(incomplete_schools, 0)
      OR schools_with_usable_teacher_count
        IS DISTINCT FROM COALESCE(usable_schools, 0)
      OR schools_without_capacity_row
        IS DISTINCT FROM COALESCE(missing_capacity_schools, 0)
      OR schools_without_teacher_data
        IS DISTINCT FROM COALESCE(missing_teacher_schools, 0)
      OR zero_teacher_school_count
        IS DISTINCT FROM COALESCE(zero_teacher_schools, 0)
      OR zero_teacher_annex_school_count
        IS DISTINCT FROM COALESCE(annex_zero_schools, 0)
      OR zero_teacher_annex_learner_count
        IS DISTINCT FROM annex_zero_learners
      OR learners_without_same_level_teachers
        IS DISTINCT FROM learners_without_teachers
      OR public_school_enrollment IS DISTINCT FROM learners
  ) AS school_measure_mismatches,

  (
    SELECT COUNT(*)
    FROM joined
    WHERE enrollment_included_in_ratio IS DISTINCT FROM
        CASE WHEN expected_personnel_available
          THEN included_learners END
      OR teacher_count IS DISTINCT FROM
        CASE WHEN expected_personnel_available
          THEN teachers END
      OR sef_provincial_teacher_count IS DISTINCT FROM
        CASE WHEN expected_personnel_available
          THEN provincial_teachers END
      OR sef_city_municipal_teacher_count IS DISTINCT FROM
        CASE WHEN expected_personnel_available
          THEN city_municipal_teachers END
      OR lgu_funded_teacher_count IS DISTINCT FROM
        CASE WHEN expected_personnel_available
          THEN lgu_teachers END
      OR other_funded_teacher_count IS DISTINCT FROM
        CASE WHEN expected_personnel_available
          THEN other_teachers END
  ) AS teacher_measure_mismatches,

  (
    SELECT COUNT(*)
    FROM joined
    WHERE learners_per_teacher IS DISTINCT FROM
      CASE WHEN expected_personnel_available
        THEN CAST(included_learners AS DOUBLE)
          / NULLIF(teachers, 0)
      END

      OR school_coverage_pct IS DISTINCT FROM
      CASE WHEN expected_personnel_available
        THEN 100.0 * usable_schools / NULLIF(schools, 0)
      END

      OR learner_coverage_pct IS DISTINCT FROM
      CASE WHEN expected_personnel_available
        THEN 100.0 * COALESCE(included_learners, 0)
          / NULLIF(learners, 0)
      END
  ) AS arithmetic_mismatches,

  (
    SELECT COUNT(*)
    FROM joined
    WHERE ratio_null_reason IS DISTINCT FROM
      CASE
        WHEN NOT expected_personnel_available
          THEN 'personnel source not available for school year'
        WHEN COALESCE(schools, 0) = 0
          THEN 'no active public school offering this level'
        WHEN learners IS NULL
          THEN 'no complete enrollment at this level'
        WHEN COALESCE(teachers, 0) = 0
          THEN 'no usable positive teacher denominator'
        ELSE NULL
      END

      OR indicator_type IS DISTINCT FROM 'project-defined'
      OR validation_status IS DISTINCT FROM 'provisional'
      OR benchmark_status IS DISTINCT FROM 'not applicable'
  ) AS label_mismatches,

  (
    SELECT COUNT(*)
    FROM candidate
    WHERE school_coverage_pct < 0
      OR school_coverage_pct > 100
      OR learner_coverage_pct < 0
      OR learner_coverage_pct > 100
  ) AS invalid_percentages,

  (
    SELECT COUNT(*)
    FROM (
      SELECT school_id, school_year, education_level_code
      FROM edu_access.`05-gold`.fact_school_enrollment
      GROUP BY school_id, school_year, education_level_code
      HAVING COUNT(*) > 1
    ) AS duplicates
  ) AS duplicate_enrollment_keys,

  (
    SELECT COUNT(*)
    FROM (
      SELECT school_id, school_year, education_level_code
      FROM edu_access.`05-gold`.fact_school_teacher_capacity
      GROUP BY school_id, school_year, education_level_code
      HAVING COUNT(*) > 1
    ) AS duplicates
  ) AS duplicate_teacher_keys,

  (
    SELECT COUNT(*)
    FROM (
      SELECT city_mun_psgc_code
      FROM edu_access.`05-gold`.dim_city_municipality
      GROUP BY city_mun_psgc_code
      HAVING COUNT(*) > 1
    ) AS duplicates
  ) AS duplicate_city_keys,

  (
    SELECT COUNT(*)
    FROM (
      SELECT school_year, source_id
      FROM edu_access.`05-gold`.fact_school_year_source_availability
      GROUP BY school_year, source_id
      HAVING COUNT(*) > 1
    ) AS duplicates
  ) AS duplicate_availability_keys,

  (SELECT COUNT(*) FROM expected_keys) AS expected_output_rows,

  (
    SELECT COUNT(*)
    FROM ap3_expected_school_rows
    WHERE learner_count < 0 OR teacher_count < 0
      OR sef_provincial_teacher_count < 0
      OR sef_city_municipal_teacher_count < 0
      OR lgu_funded_teacher_count < 0
      OR other_funded_teacher_count < 0
  ) AS negative_source_measures,

  (
    SELECT COUNT(*)
    FROM ap3_expected_school_rows
    WHERE learner_count IS NULL
  ) AS incomplete_enrollment_rows;

INSERT INTO edu_access.`01-control`.data_quality_results (
  run_id,
  batch_id,
  source_id,
  layer,
  table_name,
  check_name,
  status,
  expected,
  actual,
  checked_at_utc,
  code_revision
)
SELECT
  :run_id,
  NULL,
  'ap3',
  'analytics',
  'edu_access.06-analytics.ap3_teacher_pressure',
  check_name,
  status,
  expected,
  actual,
  current_timestamp(),
  :code_revision
FROM (
  SELECT
    'output_key_unique' AS check_name,
    CASE WHEN duplicate_output_keys = 0
      THEN 'PASS' ELSE 'FAIL' END AS status,
    '0' AS expected,
    CAST(duplicate_output_keys AS STRING) AS actual
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'output_key_not_null',
    CASE WHEN null_output_keys = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(null_output_keys AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'complete_lgu_year_level_grid',
    CASE WHEN mismatched_grid_keys = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(mismatched_grid_keys AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'identity_equals_gold',
    CASE WHEN identity_mismatches = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(identity_mismatches AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'availability_equals_gold',
    CASE WHEN availability_mismatches = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(availability_mismatches AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'school_measures_equal_gold',
    CASE WHEN school_measure_mismatches = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(school_measure_mismatches AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'teacher_measures_equal_gold',
    CASE WHEN teacher_measure_mismatches = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(teacher_measure_mismatches AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'ratio_and_coverage_arithmetic',
    CASE WHEN arithmetic_mismatches = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(arithmetic_mismatches AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'labels_follow_contract',
    CASE WHEN label_mismatches = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(label_mismatches AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'coverage_within_bounds',
    CASE WHEN invalid_percentages = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(invalid_percentages AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'enrollment_join_key_unique',
    CASE WHEN duplicate_enrollment_keys = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(duplicate_enrollment_keys AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'teacher_join_key_unique',
    CASE WHEN duplicate_teacher_keys = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(duplicate_teacher_keys AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'city_join_key_unique',
    CASE WHEN duplicate_city_keys = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(duplicate_city_keys AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'availability_key_unique',
    CASE WHEN duplicate_availability_keys = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(duplicate_availability_keys AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'expected_grid_not_empty',
    CASE WHEN expected_output_rows > 0 THEN 'PASS' ELSE 'FAIL' END,
    '> 0', CAST(expected_output_rows AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'source_measures_nonnegative',
    CASE WHEN negative_source_measures = 0 THEN 'PASS' ELSE 'FAIL' END,
    '0', CAST(negative_source_measures AS STRING)
  FROM ap3_gate_summary

  UNION ALL
  SELECT 'incomplete_enrollment',
    CASE WHEN incomplete_enrollment_rows = 0 THEN 'PASS' ELSE 'WARN' END,
    '0', CAST(incomplete_enrollment_rows AS STRING)
  FROM ap3_gate_summary
) AS results;

SELECT CASE
  WHEN COUNT(*) > 0 THEN raise_error(
    'Analytics gate failed for AP3: '
    || CAST(COUNT(*) AS STRING)
    || ' FAIL result(s)'
  )
END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id
  AND source_id = 'ap3'
  AND layer = 'analytics'
  AND status = 'FAIL'
  AND checked_at_utc >= session.analytics_gate_started_at_utc;

-- Reached only when every FAIL-level check passed.
CREATE OR REPLACE TABLE
  edu_access.`06-analytics`.ap3_teacher_pressure
USING DELTA AS
SELECT *
FROM edu_access.`06-analytics`.ap3_teacher_pressure_candidate;

COMMENT ON TABLE
  edu_access.`06-analytics`.ap3_teacher_pressure
IS 'Project-defined provisional public-school learners per teacher by LGU, school year and education level. No official benchmark.';

ALTER TABLE
  edu_access.`06-analytics`.ap3_teacher_pressure
OWNER TO `reached-hq`;