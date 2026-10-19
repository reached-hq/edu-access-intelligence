-- AP3 teacher-pressure output (#146, D-045, D-047, D-050).
-- Grain: regular city or municipality x school year x education level.
-- Project-defined and provisional: not DepEd's teacher-learner indicator.
-- A failed validation gate must not replace the published output.

CREATE SCHEMA IF NOT EXISTS edu_access.`06-analytics`;

ALTER SCHEMA edu_access.`06-analytics`
OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE
  edu_access.`06-analytics`.ap3_teacher_pressure_candidate
USING DELTA AS

WITH lgus AS (
  SELECT
    city_mun_psgc_code,
    city_mun_name,
    lgu_type,
    province_psgc_code,
    province_name,
    region_psgc_code,
    region_name
  FROM edu_access.`05-gold`.dim_city_municipality
  WHERE member_type = 'regular'
),

years AS (
  SELECT DISTINCT school_year
  FROM edu_access.`05-gold`.fact_school_enrollment
),

levels AS (
  SELECT *
  FROM VALUES ('ES'), ('JHS'), ('SHS')
    AS v(education_level_code)
),

source_availability AS (
  SELECT
    school_year,
    MAX(
      CASE
        WHEN source_id = 'deped_personnel' AND has_data
        THEN 1
        ELSE 0
      END
    ) AS personnel_available
  FROM edu_access.`05-gold`.fact_school_year_source_availability
  GROUP BY school_year
),

active_schools AS (
  SELECT
    school_id,
    school_year,
    MAX(
      CASE
        WHEN is_offered AND learner_count > 0 THEN 1
        ELSE 0
      END
    ) AS is_active
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE sector = 'Public'
    AND city_mun_psgc_code NOT IN ('UNKNOWN', 'EXCLUDED')
    AND psgc_match_status = 'matched'
  GROUP BY school_id, school_year
),

school_levels AS (
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

    COALESCE(t.teacher_count > 0, FALSE)
      AS teacher_denominator_usable,

    COALESCE(
      e.annex_status = 'Annex/Extension School'
      AND t.teacher_count = 0,
      FALSE
    ) AS zero_teacher_annex

  FROM edu_access.`05-gold`.fact_school_enrollment AS e

  JOIN active_schools AS a
    ON a.school_id = e.school_id
    AND a.school_year = e.school_year

  JOIN lgus AS g
    ON g.city_mun_psgc_code = e.city_mun_psgc_code

  LEFT JOIN edu_access.`05-gold`.fact_school_teacher_capacity AS t
    ON t.school_id = e.school_id
    AND t.school_year = e.school_year
    AND t.education_level_code = e.education_level_code

  WHERE e.sector = 'Public'
    AND e.psgc_match_status = 'matched'
    AND e.is_offered
    AND a.is_active = 1
),

school_metrics AS (
  SELECT
    city_mun_psgc_code,
    school_year,
    education_level_code,

    COUNT(DISTINCT school_id) AS public_school_count,

    COUNT(DISTINCT CASE
      WHEN learner_count IS NULL THEN school_id
    END) AS incomplete_enrollment_school_count,

    COUNT(DISTINCT CASE
      WHEN teacher_denominator_usable THEN school_id
    END) AS schools_with_usable_teacher_count,

    COUNT(DISTINCT CASE
      WHEN NOT has_capacity_row THEN school_id
    END) AS schools_without_capacity_row,

    COUNT(DISTINCT CASE
      WHEN teacher_count IS NULL THEN school_id
    END) AS schools_without_teacher_data,

    COUNT(DISTINCT CASE
      WHEN teacher_count = 0 THEN school_id
    END) AS zero_teacher_school_count,

    COUNT(DISTINCT CASE
      WHEN zero_teacher_annex THEN school_id
    END) AS zero_teacher_annex_school_count,

    SUM(CASE
      WHEN zero_teacher_annex THEN learner_count
      ELSE 0
    END) AS zero_teacher_annex_learner_count,

    SUM(CASE
      WHEN teacher_count = 0 AND NOT zero_teacher_annex
      THEN learner_count
      ELSE 0
    END) AS learners_without_same_level_teachers,

    -- NULL learner counts are not replaced with zero.
    SUM(learner_count) AS public_school_enrollment,

    SUM(CASE
      WHEN teacher_denominator_usable OR zero_teacher_annex
      THEN learner_count
    END) AS enrollment_included_in_ratio,

    -- Teacher and learner totals cover the same complete-enrollment rows.
    SUM(CASE
      WHEN teacher_denominator_usable
        AND learner_count IS NOT NULL
      THEN teacher_count
    END) AS teacher_count,

    -- Funding columns are subsets of teacher_count, not extra teachers.
    SUM(CASE
      WHEN teacher_denominator_usable
        AND learner_count IS NOT NULL
      THEN sef_provincial_teacher_count
    END) AS sef_provincial_teacher_count,

    SUM(CASE
      WHEN teacher_denominator_usable
        AND learner_count IS NOT NULL
      THEN sef_city_municipal_teacher_count
    END) AS sef_city_municipal_teacher_count,

    SUM(CASE
      WHEN teacher_denominator_usable
        AND learner_count IS NOT NULL
      THEN lgu_funded_teacher_count
    END) AS lgu_funded_teacher_count,

    SUM(CASE
      WHEN teacher_denominator_usable
        AND learner_count IS NOT NULL
      THEN other_funded_teacher_count
    END) AS other_funded_teacher_count

  FROM school_levels
  GROUP BY
    city_mun_psgc_code,
    school_year,
    education_level_code
),

grid AS (
  SELECT
    g.*,
    y.school_year,
    l.education_level_code,
    COALESCE(a.personnel_available, 0) = 1
      AS personnel_available
  FROM lgus AS g
  CROSS JOIN years AS y
  CROSS JOIN levels AS l
  LEFT JOIN source_availability AS a
    ON a.school_year = y.school_year
)

SELECT
  g.*,

  COALESCE(m.public_school_count, 0)
    AS public_school_count,

  COALESCE(m.incomplete_enrollment_school_count, 0)
    AS incomplete_enrollment_school_count,

  COALESCE(m.schools_with_usable_teacher_count, 0)
    AS schools_with_usable_teacher_count,

  COALESCE(m.schools_without_capacity_row, 0)
    AS schools_without_capacity_row,

  COALESCE(m.schools_without_teacher_data, 0)
    AS schools_without_teacher_data,

  COALESCE(m.zero_teacher_school_count, 0)
    AS zero_teacher_school_count,

  COALESCE(m.zero_teacher_annex_school_count, 0)
    AS zero_teacher_annex_school_count,

  m.zero_teacher_annex_learner_count,
  m.learners_without_same_level_teachers,
  m.public_school_enrollment,

  CASE WHEN g.personnel_available
    THEN m.enrollment_included_in_ratio
  END AS enrollment_included_in_ratio,

  CASE WHEN g.personnel_available
    THEN m.teacher_count
  END AS teacher_count,

  CASE WHEN g.personnel_available
    THEN m.sef_provincial_teacher_count
  END AS sef_provincial_teacher_count,

  CASE WHEN g.personnel_available
    THEN m.sef_city_municipal_teacher_count
  END AS sef_city_municipal_teacher_count,

  CASE WHEN g.personnel_available
    THEN m.lgu_funded_teacher_count
  END AS lgu_funded_teacher_count,

  CASE WHEN g.personnel_available
    THEN m.other_funded_teacher_count
  END AS other_funded_teacher_count,

  CASE WHEN g.personnel_available
    THEN CAST(m.enrollment_included_in_ratio AS DOUBLE)
      / NULLIF(m.teacher_count, 0)
  END AS learners_per_teacher,

  CASE WHEN g.personnel_available
    THEN 100.0 * m.schools_with_usable_teacher_count
      / NULLIF(m.public_school_count, 0)
  END AS school_coverage_pct,

  CASE WHEN g.personnel_available
    THEN 100.0 * COALESCE(m.enrollment_included_in_ratio, 0)
      / NULLIF(m.public_school_enrollment, 0)
  END AS learner_coverage_pct,

  CASE
    WHEN NOT g.personnel_available
      THEN 'personnel source not available for school year'
    WHEN COALESCE(m.public_school_count, 0) = 0
      THEN 'no active public school offering this level'
    WHEN m.public_school_enrollment IS NULL
      THEN 'no complete enrollment at this level'
    WHEN COALESCE(m.teacher_count, 0) = 0
      THEN 'no usable positive teacher denominator'
    ELSE NULL
  END AS ratio_null_reason,

  'project-defined' AS indicator_type,
  'provisional' AS validation_status,
  'not applicable' AS benchmark_status

FROM grid AS g
LEFT JOIN school_metrics AS m
  ON m.city_mun_psgc_code = g.city_mun_psgc_code
  AND m.school_year = g.school_year
  AND m.education_level_code = g.education_level_code;

COMMENT ON TABLE
  edu_access.`06-analytics`.ap3_teacher_pressure_candidate
IS 'Unpublished AP3 candidate. Read ap3_teacher_pressure only after its validation gate passes.';

ALTER TABLE
  edu_access.`06-analytics`.ap3_teacher_pressure_candidate
OWNER TO `reached-hq`;