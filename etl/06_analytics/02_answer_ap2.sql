-- AP2 classroom-pressure output (#145, D-044, D-045, D-047, D-050, D-057).
--
-- Grain: one regular city or municipality of dim_city_municipality for SY 2023-24, key
-- (city_mun_psgc_code, school_year). Every regular LGU has a row, with or without schools.
--
-- Reads published Gold only: fact_school_enrollment, fact_school_classroom_capacity and
-- dim_city_municipality. Writes ap2_classroom_pressure_candidate; the gate (90_validate_ap2.sql)
-- checks it and publishes ap2_classroom_pressure only if no check fails, so a FAIL keeps the last
-- good output. It rebuilds on every run.
--
-- Rules (metric specification, "AP2 · Classroom pressure"):
--   - School year 2023-24 only, the one year facilities and enrollment both cover.
--   - Scope: sector = 'Public' schools whose enrollment row for the year is matched to a regular city or
--     municipality. Overseas (PSO) schools and other excluded or unmatched schools carry the EXCLUDED or
--     UNKNOWN member, so they never enter an LGU; the gate reports them nationally.
--   - Enrollment is first summed to one row per school (school x school year), then joined to the room
--     fact, which has that grain, so the join cannot repeat learners or rooms.
--   - Active school: at least one offered level has a complete learner_count above 0. All-level total:
--     the offered levels' sum only when no level is NULL; otherwise NULL, never a partial sum.
--   - Rooms: instructional_classrooms_total. NULL (all three level counts blank) is missing; 0 is a
--     reported zero; only a total above 0 is usable. Temporary and makeshift spaces are not added.
--   - Ratio: the sum of complete all-level totals over the sum of rooms, for the same schools
--     (active, complete enrollment, usable rooms). Never an average of school ratios.
--   - School coverage: active schools with usable rooms / active schools. Learner coverage: complete
--     learners in usable-room schools / complete learners in all active schools (D-047).
--   - Annexes stay in the totals; DepEd publishes no mother-school ID (D-044), so an annex without a
--     usable room count is counted for review rather than read as a school with no rooms. The output
--     is provisional until annexes are linked and the upper tail is reviewed (D-057 outlier check).
--   - Benchmark status is 'not applicable' (D-045). No rank, tier, or classroom gap is computed here.

CREATE SCHEMA IF NOT EXISTS edu_access.`06-analytics`;
ALTER SCHEMA edu_access.`06-analytics` OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap2_classroom_pressure_candidate USING DELTA AS
WITH lgus AS (
  SELECT city_mun_psgc_code, city_mun_name, lgu_type, province_psgc_code, province_name,
         region_psgc_code, region_name, source_psgc_quarter
  FROM edu_access.`05-gold`.dim_city_municipality
  WHERE member_type = 'regular'
),
schools AS (
  SELECT
    e.school_id, e.school_year, e.city_mun_psgc_code,
    MAX(CASE WHEN e.annex_status = 'Annex/Extension School' THEN 1 ELSE 0 END) AS is_annex,
    MAX(CASE WHEN e.is_offered AND e.learner_count > 0 THEN 1 ELSE 0 END) AS is_active,
    COUNT_IF(e.learner_count IS NULL) AS incomplete_levels,
    SUM(CASE WHEN e.is_offered AND e.learner_count IS NOT NULL THEN e.learner_count ELSE 0 END)
      AS complete_level_learners
  FROM edu_access.`05-gold`.fact_school_enrollment AS e
  JOIN lgus AS l ON l.city_mun_psgc_code = e.city_mun_psgc_code
  WHERE e.school_year = '2023-24' AND e.sector = 'Public'
  GROUP BY e.school_id, e.school_year, e.city_mun_psgc_code
),
school_rooms AS (
  SELECT
    s.school_id, s.school_year, s.city_mun_psgc_code, s.is_annex, s.is_active,
    s.incomplete_levels = 0 AS enrollment_complete,
    CASE WHEN s.incomplete_levels = 0 THEN s.complete_level_learners END AS total_learners,
    s.complete_level_learners,
    c.school_id IS NOT NULL AS has_facilities_row,
    c.instructional_classrooms_total AS rooms
  FROM schools AS s
  LEFT JOIN edu_access.`05-gold`.fact_school_classroom_capacity AS c
    ON c.school_id = s.school_id AND c.school_year = s.school_year
),
flags AS (
  SELECT *,
    COALESCE(rooms > 0, FALSE) AS rooms_usable,
    COALESCE(rooms > 0, FALSE) AND enrollment_complete AS in_ratio
  FROM school_rooms
),
metrics AS (
  SELECT
    city_mun_psgc_code,
    COUNT_IF(is_active = 0) AS inactive_public_school_count,
    COUNT_IF(is_active = 1) AS active_public_school_count,
    COUNT_IF(is_active = 1 AND enrollment_complete) AS complete_enrollment_school_count,
    COUNT_IF(is_active = 1 AND NOT enrollment_complete) AS incomplete_enrollment_school_count,
    SUM(CASE WHEN is_active = 1 AND NOT enrollment_complete THEN complete_level_learners ELSE 0 END)
      AS incomplete_enrollment_complete_level_learners,
    SUM(CASE WHEN is_active = 1 THEN total_learners ELSE 0 END) AS public_school_enrollment,
    COUNT_IF(is_active = 1 AND rooms_usable) AS usable_room_school_count,
    COUNT_IF(is_active = 1 AND rooms_usable AND NOT enrollment_complete) AS usable_room_incomplete_enrollment_school_count,
    COUNT_IF(is_active = 1 AND in_ratio) AS ratio_school_count,
    SUM(CASE WHEN is_active = 1 AND in_ratio THEN total_learners ELSE 0 END) AS ratio_learners,
    SUM(CASE WHEN is_active = 1 AND in_ratio THEN rooms ELSE 0 END) AS ratio_instructional_rooms,
    COUNT_IF(is_active = 1 AND has_facilities_row AND rooms IS NULL) AS missing_room_school_count,
    SUM(CASE WHEN is_active = 1 AND has_facilities_row AND rooms IS NULL THEN total_learners ELSE 0 END)
      AS missing_room_learners,
    COUNT_IF(is_active = 1 AND rooms = 0) AS zero_room_school_count,
    SUM(CASE WHEN is_active = 1 AND rooms = 0 THEN total_learners ELSE 0 END) AS zero_room_learners,
    COUNT_IF(is_active = 1 AND NOT has_facilities_row) AS no_facilities_row_school_count,
    SUM(CASE WHEN is_active = 1 AND NOT has_facilities_row THEN total_learners ELSE 0 END)
      AS no_facilities_row_learners,
    COUNT_IF(is_active = 1 AND is_annex = 1) AS annex_school_count,
    COUNT_IF(is_active = 1 AND is_annex = 1 AND NOT rooms_usable) AS annex_without_usable_room_school_count,
    SUM(CASE WHEN is_active = 1 AND is_annex = 1 AND NOT rooms_usable THEN total_learners ELSE 0 END)
      AS annex_without_usable_room_learners
  FROM flags
  GROUP BY city_mun_psgc_code
),
lgu_metrics AS (
  SELECT
    l.*,
    CAST('2023-24' AS STRING) AS school_year,
    COALESCE(m.inactive_public_school_count, 0) AS inactive_public_school_count,
    COALESCE(m.active_public_school_count, 0) AS active_public_school_count,
    COALESCE(m.complete_enrollment_school_count, 0) AS complete_enrollment_school_count,
    COALESCE(m.incomplete_enrollment_school_count, 0) AS incomplete_enrollment_school_count,
    CAST(COALESCE(m.incomplete_enrollment_complete_level_learners, 0) AS BIGINT)
      AS incomplete_enrollment_complete_level_learners,
    CAST(COALESCE(m.public_school_enrollment, 0) AS BIGINT) AS public_school_enrollment,
    COALESCE(m.usable_room_school_count, 0) AS usable_room_school_count,
    COALESCE(m.usable_room_incomplete_enrollment_school_count, 0) AS usable_room_incomplete_enrollment_school_count,
    COALESCE(m.ratio_school_count, 0) AS ratio_school_count,
    CAST(COALESCE(m.ratio_learners, 0) AS BIGINT) AS ratio_learners,
    CAST(COALESCE(m.ratio_instructional_rooms, 0) AS BIGINT) AS ratio_instructional_rooms,
    COALESCE(m.missing_room_school_count, 0) AS missing_room_school_count,
    CAST(COALESCE(m.missing_room_learners, 0) AS BIGINT) AS missing_room_learners,
    COALESCE(m.zero_room_school_count, 0) AS zero_room_school_count,
    CAST(COALESCE(m.zero_room_learners, 0) AS BIGINT) AS zero_room_learners,
    COALESCE(m.no_facilities_row_school_count, 0) AS no_facilities_row_school_count,
    CAST(COALESCE(m.no_facilities_row_learners, 0) AS BIGINT) AS no_facilities_row_learners,
    COALESCE(m.annex_school_count, 0) AS annex_school_count,
    COALESCE(m.annex_without_usable_room_school_count, 0) AS annex_without_usable_room_school_count,
    CAST(COALESCE(m.annex_without_usable_room_learners, 0) AS BIGINT) AS annex_without_usable_room_learners
  FROM lgus AS l
  LEFT JOIN metrics AS m USING (city_mun_psgc_code)
)
SELECT
  city_mun_psgc_code, city_mun_name, lgu_type, province_psgc_code, province_name,
  region_psgc_code, region_name, school_year,
  'Learners per reported instructional room' AS measure_label,
  'DepEd School Facilities (NSBI)' AS source_label,
  ratio_learners,
  ratio_instructional_rooms,
  ratio_school_count,
  CAST(ratio_learners AS DOUBLE) / NULLIF(ratio_instructional_rooms, 0) AS learners_per_nsbi_instructional_room,
  CASE
    WHEN active_public_school_count = 0 THEN 'no active public school'
    WHEN usable_room_school_count = 0 THEN 'no school with a reported room count above 0'
    WHEN ratio_school_count = 0 THEN 'no school with both complete enrollment and a reported room count above 0'
  END AS ratio_null_reason,
  active_public_school_count,
  usable_room_school_count,
  CAST(100.0 * usable_room_school_count / NULLIF(active_public_school_count, 0) AS DOUBLE) AS school_coverage_pct,
  public_school_enrollment,
  -- ratio_learners is also the learner-coverage numerator: an incomplete school has no total to count.
  CAST(100.0 * ratio_learners / NULLIF(public_school_enrollment, 0) AS DOUBLE) AS learner_coverage_pct,
  CASE
    WHEN active_public_school_count = 0 THEN 'no active public school'
    WHEN public_school_enrollment = 0 THEN 'no active public school with complete enrollment'
  END AS coverage_null_reason,
  inactive_public_school_count,
  complete_enrollment_school_count,
  incomplete_enrollment_school_count,
  incomplete_enrollment_complete_level_learners,
  usable_room_incomplete_enrollment_school_count,
  missing_room_school_count,
  missing_room_learners,
  zero_room_school_count,
  zero_room_learners,
  no_facilities_row_school_count,
  no_facilities_row_learners,
  annex_school_count,
  annex_without_usable_room_school_count,
  annex_without_usable_room_learners,
  'project-defined' AS indicator_type,
  'provisional' AS validation_status,
  'not applicable' AS benchmark_status,
  source_psgc_quarter,
  :code_revision AS code_revision
FROM lgu_metrics;

COMMENT ON TABLE edu_access.`06-analytics`.ap2_classroom_pressure_candidate IS 'Unpublished AP2 build. Do not read: use ap2_classroom_pressure.';
ALTER TABLE edu_access.`06-analytics`.ap2_classroom_pressure_candidate OWNER TO `reached-hq`;
