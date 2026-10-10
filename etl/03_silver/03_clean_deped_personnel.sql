-- Silver build for deped_personnel. Generated from config/ingestion/deped_personnel.json
-- and config/mappings/deped_personnel.json:
--   python -m src.silver.cli sql --source deped_personnel > etl/03_silver/03_clean_deped_personnel.sql
-- Do not edit by hand; tests/test_silver.py fails if it differs.
-- Builds unpublished candidate tables. The gate publishes them only after every FAIL check is zero.

DECLARE OR REPLACE VARIABLE silver_run_id STRING;
SET VARIABLE silver_run_id = :run_id;
DECLARE OR REPLACE VARIABLE silver_code_revision STRING;
SET VARIABLE silver_code_revision = COALESCE(NULLIF(:code_revision, ''), 'UNSET');
DECLARE OR REPLACE VARIABLE silver_environment STRING;
SET VARIABLE silver_environment = COALESCE(NULLIF(:environment, ''), 'UNSET');
DECLARE OR REPLACE VARIABLE silver_cleaned_at_utc TIMESTAMP;
SET VARIABLE silver_cleaned_at_utc = current_timestamp();

MERGE INTO edu_access.`01-control`.pipeline_runs AS t
USING (SELECT session.silver_run_id AS run_id) AS s
ON t.run_id = s.run_id AND t.pipeline_name = 'silver_build' AND t.source_id = 'deped_personnel'
WHEN MATCHED THEN UPDATE SET status = 'running', started_at_utc = session.silver_cleaned_at_utc, finished_at_utc = NULL, failure_stage = NULL, error_message = NULL, code_revision = session.silver_code_revision, job_run_id = s.run_id
WHEN NOT MATCHED THEN INSERT (run_id, pipeline_name, source_id, environment, status, started_at_utc, code_revision, job_run_id)
  VALUES (s.run_id, 'silver_build', 'deped_personnel', session.silver_environment, 'running', session.silver_cleaned_at_utc, session.silver_code_revision, s.run_id);

CREATE SCHEMA IF NOT EXISTS edu_access.`03-silver`;
ALTER SCHEMA edu_access.`03-silver` OWNER TO `reached-hq`;

CREATE OR REPLACE TEMPORARY VIEW deped_personnel_classified AS
WITH bronze AS (
  SELECT r.* FROM edu_access.`02-bronze`.deped_personnel_raw AS r JOIN edu_access.`01-control`.current_batches AS c ON r.batch_id = c.batch_id WHERE c.source_id = 'deped_personnel'
), enrollment AS (
  SELECT * FROM edu_access.`03-silver`.deped_enrollment_clean
), normalized AS (
  SELECT
    r.school_year,
    r.school_id,
    r.sector,
    r.school_management,
    r.offers_es,
    r.offers_jhs,
    r.offers_shs,
    r.`es_master_teacher_iv` AS es_master_teacher_iv,
    r.`es_master_teacher_iii` AS es_master_teacher_iii,
    r.`es_master_teacher_ii` AS es_master_teacher_ii,
    r.`es_master_teacher_i` AS es_master_teacher_i,
    r.`es_teacher_iii` AS es_teacher_iii,
    r.`es_teacher_ii` AS es_teacher_ii,
    r.`es_teacher_i` AS es_teacher_i,
    r.`es_sped_sned_teacher_v` AS es_sped_sned_teacher_v,
    r.`es_sped_sned_teacher_iv` AS es_sped_sned_teacher_iv,
    r.`es_sped_sned_teacher_iii` AS es_sped_sned_teacher_iii,
    r.`es_sped_sned_teacher_ii` AS es_sped_sned_teacher_ii,
    r.`es_sped_sned_teacher_i` AS es_sped_sned_teacher_i,
    r.`jhs_instructor_iii` AS jhs_instructor_iii,
    r.`jhs_instructor_ii` AS jhs_instructor_ii,
    r.`jhs_instructor_i` AS jhs_instructor_i,
    r.`jhs_master_teacher_iv` AS jhs_master_teacher_iv,
    r.`jhs_master_teacher_iii` AS jhs_master_teacher_iii,
    r.`jhs_master_teacher_ii` AS jhs_master_teacher_ii,
    r.`jhs_master_teacher_i` AS jhs_master_teacher_i,
    r.`jhs_teacher_iii` AS jhs_teacher_iii,
    r.`jhs_teacher_ii` AS jhs_teacher_ii,
    r.`jhs_teacher_i` AS jhs_teacher_i,
    r.`jhs_special_science_teacher_i` AS jhs_special_science_teacher_i,
    r.`jhs_sped_teacher_v` AS jhs_sped_teacher_v,
    r.`jhs_sped_teacher_iv` AS jhs_sped_teacher_iv,
    r.`jhs_sped_teacher_iii` AS jhs_sped_teacher_iii,
    r.`jhs_sped_teacher_ii` AS jhs_sped_teacher_ii,
    r.`jhs_sped_teacher_i` AS jhs_sped_teacher_i,
    r.`shs_master_teacher_iv` AS shs_master_teacher_iv,
    r.`shs_master_teacher_iii` AS shs_master_teacher_iii,
    r.`shs_master_teacher_ii` AS shs_master_teacher_ii,
    r.`shs_master_teacher_i` AS shs_master_teacher_i,
    r.`shs_teacher_iii` AS shs_teacher_iii,
    r.`shs_teacher_ii` AS shs_teacher_ii,
    r.`shs_teacher_i` AS shs_teacher_i,
    r.`shs_special_science_teacher_i` AS shs_special_science_teacher_i,
    r.`es_school_principal_iv` AS es_school_principal_iv,
    r.`es_school_principal_iii` AS es_school_principal_iii,
    r.`es_school_principal_ii` AS es_school_principal_ii,
    r.`es_school_principal_i` AS es_school_principal_i,
    r.`es_head_teacher_vi` AS es_head_teacher_vi,
    r.`es_head_teacher_v` AS es_head_teacher_v,
    r.`es_head_teacher_iv` AS es_head_teacher_iv,
    r.`es_head_teacher_iii` AS es_head_teacher_iii,
    r.`es_head_teacher_ii` AS es_head_teacher_ii,
    r.`es_head_teacher_i` AS es_head_teacher_i,
    r.`es_guidance_coordinator_iii` AS es_guidance_coordinator_iii,
    r.`es_guidance_coordinator_ii` AS es_guidance_coordinator_ii,
    r.`es_guidance_coordinator_i` AS es_guidance_coordinator_i,
    r.`es_guidance_counselor_iii` AS es_guidance_counselor_iii,
    r.`es_guidance_counselor_ii` AS es_guidance_counselor_ii,
    r.`es_guidance_counselor_i` AS es_guidance_counselor_i,
    r.`es_administrative_officer_ii` AS es_administrative_officer_ii,
    r.`es_project_development_officer_i` AS es_project_development_officer_i,
    r.`es_administrative_assistant_iii_(senior_bookkeeper)` AS es_administrative_assistant_iii_senior_bookkeeper,
    r.`es_administrative_assistant_ii_/_(disbursing_officer_ii)` AS es_administrative_assistant_ii_disbursing_officer_ii,
    r.`es_security_guard` AS es_security_guard,
    r.`es_utility_worker_i` AS es_utility_worker_i,
    r.`jhs_vocational_school_administrator_iii` AS jhs_vocational_school_administrator_iii,
    r.`jhs_vocational_school_administrator_ii` AS jhs_vocational_school_administrator_ii,
    r.`jhs_vocational_school_administrator_i` AS jhs_vocational_school_administrator_i,
    r.`jhs_school_principal_iv` AS jhs_school_principal_iv,
    r.`jhs_school_principal_iii` AS jhs_school_principal_iii,
    r.`jhs_school_principal_ii` AS jhs_school_principal_ii,
    r.`jhs_school_principal_i` AS jhs_school_principal_i,
    r.`jhs_assistant_school_principal_iii` AS jhs_assistant_school_principal_iii,
    r.`jhs_assistant_school_principal_ii` AS jhs_assistant_school_principal_ii,
    r.`jhs_assistant_school_principal_i` AS jhs_assistant_school_principal_i,
    r.`jhs_head_teacher_vi` AS jhs_head_teacher_vi,
    r.`jhs_head_teacher_v` AS jhs_head_teacher_v,
    r.`jhs_head_teacher_iv` AS jhs_head_teacher_iv,
    r.`jhs_head_teacher_iii` AS jhs_head_teacher_iii,
    r.`jhs_head_teacher_ii` AS jhs_head_teacher_ii,
    r.`jhs_head_teacher_i` AS jhs_head_teacher_i,
    r.`jhs_guidance_coordinator_iii` AS jhs_guidance_coordinator_iii,
    r.`jhs_guidance_coordinator_ii` AS jhs_guidance_coordinator_ii,
    r.`jhs_guidance_coordinator_i` AS jhs_guidance_coordinator_i,
    r.`jhs_guidance_counselor_iii` AS jhs_guidance_counselor_iii,
    r.`jhs_guidance_counselor_ii` AS jhs_guidance_counselor_ii,
    r.`jhs_guidance_counselor_i` AS jhs_guidance_counselor_i,
    r.`jhs_administrative_officer_iv` AS jhs_administrative_officer_iv,
    r.`jhs_administrative_officer_ii` AS jhs_administrative_officer_ii,
    r.`jhs_project_development_officer_i` AS jhs_project_development_officer_i,
    r.`jhs_school_librarian_iii` AS jhs_school_librarian_iii,
    r.`jhs_school_librarian_ii` AS jhs_school_librarian_ii,
    r.`jhs_school_librarian_i` AS jhs_school_librarian_i,
    r.`jhs_accountant_i` AS jhs_accountant_i,
    r.`jhs_cashier_i` AS jhs_cashier_i,
    r.`jhs_supply_officer_i` AS jhs_supply_officer_i,
    r.`jhs_administrative_assistant_iii_(senior_bookkeeper)` AS jhs_administrative_assistant_iii_senior_bookkeeper,
    r.`jhs_bookkeeper` AS jhs_bookkeeper,
    r.`jhs_administrative_assistant_ii_(disbursing_officer_ii)` AS jhs_administrative_assistant_ii_disbursing_officer_ii,
    r.`jhs_administrative_assistant_ii_(disbursing_officer_i)` AS jhs_administrative_assistant_ii_disbursing_officer_i,
    r.`jhs_administrative_aide_vi` AS jhs_administrative_aide_vi,
    r.`jhs_heavy_equipment_operator_i` AS jhs_heavy_equipment_operator_i,
    r.`jhs_driver_i` AS jhs_driver_i,
    r.`jhs_security_guard_i` AS jhs_security_guard_i,
    r.`jhs_light_equipment_operator` AS jhs_light_equipment_operator,
    r.`jhs_utility_worker_i` AS jhs_utility_worker_i,
    r.`shs_school_principal_iv` AS shs_school_principal_iv,
    r.`shs_school_principal_iii` AS shs_school_principal_iii,
    r.`shs_school_principal_ii` AS shs_school_principal_ii,
    r.`shs_school_principal_i` AS shs_school_principal_i,
    r.`shs_total_school_principal` AS shs_total_school_principal,
    r.`shs_assistant_principal_iii` AS shs_assistant_principal_iii,
    r.`shs_assistant_principal_ii` AS shs_assistant_principal_ii,
    r.`shs_assistant_principal_i` AS shs_assistant_principal_i,
    r.`shs_head_teacher_vi` AS shs_head_teacher_vi,
    r.`shs_head_teacher_v` AS shs_head_teacher_v,
    r.`shs_head_teacher_iv` AS shs_head_teacher_iv,
    r.`shs_head_teacher_iii` AS shs_head_teacher_iii,
    r.`shs_head_teacher_ii` AS shs_head_teacher_ii,
    r.`shs_head_teacher_i` AS shs_head_teacher_i,
    r.`shs_school_nurse_ii` AS shs_school_nurse_ii,
    r.`shs_administrative_officer_iv` AS shs_administrative_officer_iv,
    r.`shs_administrative_officer_ii` AS shs_administrative_officer_ii,
    r.`shs_school_librarian_iii` AS shs_school_librarian_iii,
    r.`shs_school_librarian_ii` AS shs_school_librarian_ii,
    r.`shs_school_librarian_i` AS shs_school_librarian_i,
    r.`shs_guidance_service_specialist_ii` AS shs_guidance_service_specialist_ii,
    r.`shs_guidance_service_specialist_i` AS shs_guidance_service_specialist_i,
    r.`shs_guidance_counselor_iii` AS shs_guidance_counselor_iii,
    r.`shs_guidance_counselor_ii` AS shs_guidance_counselor_ii,
    r.`shs_guidance_counselor_i` AS shs_guidance_counselor_i,
    r.`shs_accounting_i` AS shs_accounting_i,
    r.`shs_project_development_officer_i` AS shs_project_development_officer_i,
    r.`shs_registrar_i` AS shs_registrar_i,
    r.`shs_cashier_i` AS shs_cashier_i,
    r.`shs_supply_officer_i` AS shs_supply_officer_i,
    r.`shs_administrative_assistant_iii_(senior_bookkeeper)` AS shs_administrative_assistant_iii_senior_bookkeeper,
    r.`shs_administrative_assistant_ii_(disbursing_officer_ii)` AS shs_administrative_assistant_ii_disbursing_officer_ii,
    r.`shs_administrative_assistant_i` AS shs_administrative_assistant_i,
    r.`shs_administrative_aide_vi` AS shs_administrative_aide_vi,
    r.`shs_heavy_equipment_operator_i` AS shs_heavy_equipment_operator_i,
    r.`shs_security_guard_i` AS shs_security_guard_i,
    r.`shs_light_equipment_operator_i` AS shs_light_equipment_operator_i,
    r.`shs_utility_worker_i` AS shs_utility_worker_i,
    r.`kinder_teachers_sef_province` AS kinder_teachers_sef_province,
    r.`kinder_teachers_sef_municipality_city` AS kinder_teachers_sef_municipality_city,
    r.`kinder_teachers_lgu_funding` AS kinder_teachers_lgu_funding,
    r.`kinder_teachers_other_funding` AS kinder_teachers_other_funding,
    r.`es_teachers_sef_province` AS es_teachers_sef_province,
    r.`es_teachers_sef_municipality_city` AS es_teachers_sef_municipality_city,
    r.`es_teachers_lgu_funding` AS es_teachers_lgu_funding,
    r.`es_teachers_other_funding` AS es_teachers_other_funding,
    r.`jhs_teachers_sef_province` AS jhs_teachers_sef_province,
    r.`jhs_teachers_sef_municipality_city` AS jhs_teachers_sef_municipality_city,
    r.`jhs_teachers_lgu_funding` AS jhs_teachers_lgu_funding,
    r.`jhs_teachers_other_funding` AS jhs_teachers_other_funding,
    r.`shs_teachers_sef_province` AS shs_teachers_sef_province,
    r.`shs_teachers_sef_municipality_city` AS shs_teachers_sef_municipality_city,
    r.`shs_teachers_lgu_funding` AS shs_teachers_lgu_funding,
    r.`shs_teachers_other_funding` AS shs_teachers_other_funding,
    r.`es_learning_support_aide_sef_provincial` AS es_learning_support_aide_sef_provincial,
    r.`es_learning_support_aide_sef_municipal_city` AS es_learning_support_aide_sef_municipal_city,
    r.`es_learning_support_aide_lgu_funding` AS es_learning_support_aide_lgu_funding,
    r.`es_learning_support_aide_other_funding` AS es_learning_support_aide_other_funding,
    r.`es_administrative_officer_sef_provincial` AS es_administrative_officer_sef_provincial,
    r.`es_administrative_officer_sef_municipal_city` AS es_administrative_officer_sef_municipal_city,
    r.`es_administrative_officer_lgu_funding` AS es_administrative_officer_lgu_funding,
    r.`es_administrative_officer_other_funding` AS es_administrative_officer_other_funding,
    r.`es_administrative_assistant_sef_provincial` AS es_administrative_assistant_sef_provincial,
    r.`es_administrative_assistant_sef_municipal_city` AS es_administrative_assistant_sef_municipal_city,
    r.`es_administrative_assistant_lgu_funding` AS es_administrative_assistant_lgu_funding,
    r.`es_administrative_assistant_other_funding` AS es_administrative_assistant_other_funding,
    r.`es_administrative_aide_sef_provincial` AS es_administrative_aide_sef_provincial,
    r.`es_administrative_aide_sef_municipal_city` AS es_administrative_aide_sef_municipal_city,
    r.`es_administrative_aide_lgu_funding` AS es_administrative_aide_lgu_funding,
    r.`es_administrative_aide_other_funding` AS es_administrative_aide_other_funding,
    r.`es_project_development_officer_sef_provincial` AS es_project_development_officer_sef_provincial,
    r.`es_project_development_officer_sef_municipal_city` AS es_project_development_officer_sef_municipal_city,
    r.`es_project_development_officer_lgu_funding` AS es_project_development_officer_lgu_funding,
    r.`es_project_development_officer_other_funding` AS es_project_development_officer_other_funding,
    r.`es_school_doctor_sef_provincial` AS es_school_doctor_sef_provincial,
    r.`es_school_doctor_sef_municipal_city` AS es_school_doctor_sef_municipal_city,
    r.`es_school_doctor_lgu_funding` AS es_school_doctor_lgu_funding,
    r.`es_school_doctor_other_funding` AS es_school_doctor_other_funding,
    r.`es_school_dentist_sef_provincial` AS es_school_dentist_sef_provincial,
    r.`es_school_dentist_sef_municipal_city` AS es_school_dentist_sef_municipal_city,
    r.`es_school_dentist_lgu_funding` AS es_school_dentist_lgu_funding,
    r.`es_school_dentist_other_funding` AS es_school_dentist_other_funding,
    r.`es_school_nurse_sef_provincial` AS es_school_nurse_sef_provincial,
    r.`es_school_nurse_sef_municipal_city` AS es_school_nurse_sef_municipal_city,
    r.`es_school_nurse_lgu_funding` AS es_school_nurse_lgu_funding,
    r.`es_school_nurse_other_funding` AS es_school_nurse_other_funding,
    r.`es_librarian_sef_provincial` AS es_librarian_sef_provincial,
    r.`es_librarian_sef_municipal_city` AS es_librarian_sef_municipal_city,
    r.`es_librarian_lgu_funding` AS es_librarian_lgu_funding,
    r.`es_librarian_other_funding` AS es_librarian_other_funding,
    r.`es_library_assistant_sef_provincial` AS es_library_assistant_sef_provincial,
    r.`es_library_assistant_sef_municipal_city` AS es_library_assistant_sef_municipal_city,
    r.`es_library_assistant_lgu_funding` AS es_library_assistant_lgu_funding,
    r.`es_library_assistant_other_funding` AS es_library_assistant_other_funding,
    r.`es_guidance_counselor_sef_provincial` AS es_guidance_counselor_sef_provincial,
    r.`es_guidance_counselor_sef_municipal_city` AS es_guidance_counselor_sef_municipal_city,
    r.`es_guidance_counselor_lgu_funding` AS es_guidance_counselor_lgu_funding,
    r.`es_guidance_counselor_other_funding` AS es_guidance_counselor_other_funding,
    r.`es_guidance_advocate_sef_provincial` AS es_guidance_advocate_sef_provincial,
    r.`es_guidance_advocate_sef_municipal_city` AS es_guidance_advocate_sef_municipal_city,
    r.`es_guidance_advocate_lgu_funding` AS es_guidance_advocate_lgu_funding,
    r.`es_guidance_advocate_other_funding` AS es_guidance_advocate_other_funding,
    r.`es_guidance_assistant_sef_provincial` AS es_guidance_assistant_sef_provincial,
    r.`es_guidance_assistant_sef_municipal_city` AS es_guidance_assistant_sef_municipal_city,
    r.`es_guidance_assistant_lgu_funding` AS es_guidance_assistant_lgu_funding,
    r.`es_guidance_assistant_other_funding` AS es_guidance_assistant_other_funding,
    r.`es_computer_technician_sef_provincial` AS es_computer_technician_sef_provincial,
    r.`es_computer_technician_sef_municipal_city` AS es_computer_technician_sef_municipal_city,
    r.`es_computer_technician_lgu_funding` AS es_computer_technician_lgu_funding,
    r.`es_computer_technician_other_funding` AS es_computer_technician_other_funding,
    r.`jhs_learning_support_aide_sef_provincial` AS jhs_learning_support_aide_sef_provincial,
    r.`jhs_learning_support_aide_sef_municipal_city` AS jhs_learning_support_aide_sef_municipal_city,
    r.`jhs_learning_support_aide_lgu_funding` AS jhs_learning_support_aide_lgu_funding,
    r.`jhs_learning_support_aide_other_funding` AS jhs_learning_support_aide_other_funding,
    r.`jhs_administrative_officer_sef_provincial` AS jhs_administrative_officer_sef_provincial,
    r.`jhs_administrative_officer_sef_municipal_city` AS jhs_administrative_officer_sef_municipal_city,
    r.`jhs_administrative_officer_lgu_funding` AS jhs_administrative_officer_lgu_funding,
    r.`jhs_administrative_officer_other_funding` AS jhs_administrative_officer_other_funding,
    r.`jhs_administrative_assistant_sef_provincial` AS jhs_administrative_assistant_sef_provincial,
    r.`jhs_administrative_assistant_sef_municipal_city` AS jhs_administrative_assistant_sef_municipal_city,
    r.`jhs_administrative_assistant_lgu_funding` AS jhs_administrative_assistant_lgu_funding,
    r.`jhs_administrative_assistant_other_funding` AS jhs_administrative_assistant_other_funding,
    r.`jhs_administrative_aide_sef_provincial` AS jhs_administrative_aide_sef_provincial,
    r.`jhs_administrative_aide_sef_municipal_city` AS jhs_administrative_aide_sef_municipal_city,
    r.`jhs_administrative_aide_lgu_funding` AS jhs_administrative_aide_lgu_funding,
    r.`jhs_administrative_aide_other_funding` AS jhs_administrative_aide_other_funding,
    r.`jhs_project_development_officer_sef_provincial` AS jhs_project_development_officer_sef_provincial,
    r.`jhs_project_development_officer_sef_municipal_city` AS jhs_project_development_officer_sef_municipal_city,
    r.`jhs_project_development_officer_lgu_funding` AS jhs_project_development_officer_lgu_funding,
    r.`jhs_project_development_officer_other_funding` AS jhs_project_development_officer_other_funding,
    r.`jhs_school_doctor_sef_provincial` AS jhs_school_doctor_sef_provincial,
    r.`jhs_school_doctor_sef_municipal_city` AS jhs_school_doctor_sef_municipal_city,
    r.`jhs_school_doctor_lgu_funding` AS jhs_school_doctor_lgu_funding,
    r.`jhs_school_doctor_other_funding` AS jhs_school_doctor_other_funding,
    r.`jhs_school_dentist_sef_provincial` AS jhs_school_dentist_sef_provincial,
    r.`jhs_school_dentist_sef_municipal_city` AS jhs_school_dentist_sef_municipal_city,
    r.`jhs_school_dentist_lgu_funding` AS jhs_school_dentist_lgu_funding,
    r.`jhs_school_dentist_other_funding` AS jhs_school_dentist_other_funding,
    r.`jhs_school_nurse_sef_provincial` AS jhs_school_nurse_sef_provincial,
    r.`jhs_school_nurse_sef_municipal_city` AS jhs_school_nurse_sef_municipal_city,
    r.`jhs_school_nurse_lgu_funding` AS jhs_school_nurse_lgu_funding,
    r.`jhs_school_nurse_other_funding` AS jhs_school_nurse_other_funding,
    r.`jhs_librarian_sef_provincial` AS jhs_librarian_sef_provincial,
    r.`jhs_librarian_sef_municipal_city` AS jhs_librarian_sef_municipal_city,
    r.`jhs_librarian_lgu_funding` AS jhs_librarian_lgu_funding,
    r.`jhs_librarian_other_funding` AS jhs_librarian_other_funding,
    r.`jhs_library_assistant_sef_provincial` AS jhs_library_assistant_sef_provincial,
    r.`jhs_library_assistant_sef_municipal_city` AS jhs_library_assistant_sef_municipal_city,
    r.`jhs_library_assistant_lgu_funding` AS jhs_library_assistant_lgu_funding,
    r.`jhs_library_assistant_other_funding` AS jhs_library_assistant_other_funding,
    r.`jhs_guidance_counselor_sef_provincial` AS jhs_guidance_counselor_sef_provincial,
    r.`jhs_guidance_counselor_sef_municipal_city` AS jhs_guidance_counselor_sef_municipal_city,
    r.`jhs_guidance_counselor_lgu_funding` AS jhs_guidance_counselor_lgu_funding,
    r.`jhs_guidance_counselor_other_funding` AS jhs_guidance_counselor_other_funding,
    r.`jhs_guidance_advocate_sef_provincial` AS jhs_guidance_advocate_sef_provincial,
    r.`jhs_guidance_advocate_sef_municipal_city` AS jhs_guidance_advocate_sef_municipal_city,
    r.`jhs_guidance_advocate_lgu_funding` AS jhs_guidance_advocate_lgu_funding,
    r.`jhs_guidance_advocate_other_funding` AS jhs_guidance_advocate_other_funding,
    r.`jhs_guidance_assistant_sef_provincial` AS jhs_guidance_assistant_sef_provincial,
    r.`jhs_guidance_assistant_sef_municipal_city` AS jhs_guidance_assistant_sef_municipal_city,
    r.`jhs_guidance_assistant_lgu_funding` AS jhs_guidance_assistant_lgu_funding,
    r.`jhs_guidance_assistant_other_funding` AS jhs_guidance_assistant_other_funding,
    r.`jhs_computer_technician_sef_provincial` AS jhs_computer_technician_sef_provincial,
    r.`jhs_computer_technician_sef_municipal_city` AS jhs_computer_technician_sef_municipal_city,
    r.`jhs_computer_technician_lgu_funding` AS jhs_computer_technician_lgu_funding,
    r.`jhs_computer_technician_other_funding` AS jhs_computer_technician_other_funding,
    r.`shs_learning_support_aide_sef_provincial` AS shs_learning_support_aide_sef_provincial,
    r.`shs_learning_support_aide_sef_municipal_city` AS shs_learning_support_aide_sef_municipal_city,
    r.`shs_learning_support_aide_lgu_funding` AS shs_learning_support_aide_lgu_funding,
    r.`shs_learning_support_aide_other_funding` AS shs_learning_support_aide_other_funding,
    r.`shs_administrative_officer_sef_provincial` AS shs_administrative_officer_sef_provincial,
    r.`shs_administrative_officer_sef_municipal_city` AS shs_administrative_officer_sef_municipal_city,
    r.`shs_administrative_officer_lgu_funding` AS shs_administrative_officer_lgu_funding,
    r.`shs_administrative_officer_other_funding` AS shs_administrative_officer_other_funding,
    r.`shs_administrative_assistant_sef_provincial` AS shs_administrative_assistant_sef_provincial,
    r.`shs_administrative_assistant_sef_municipal_city` AS shs_administrative_assistant_sef_municipal_city,
    r.`shs_administrative_assistant_lgu_funding` AS shs_administrative_assistant_lgu_funding,
    r.`shs_administrative_assistant_other_funding` AS shs_administrative_assistant_other_funding,
    r.`shs_administrative_aide_sef_provincial` AS shs_administrative_aide_sef_provincial,
    r.`shs_administrative_aide_sef_municipal_city` AS shs_administrative_aide_sef_municipal_city,
    r.`shs_administrative_aide_lgu_funding` AS shs_administrative_aide_lgu_funding,
    r.`shs_administrative_aide_other_funding` AS shs_administrative_aide_other_funding,
    r.`shs_project_development_officer_sef_provincial` AS shs_project_development_officer_sef_provincial,
    r.`shs_project_development_officer_sef_municipal_city` AS shs_project_development_officer_sef_municipal_city,
    r.`shs_project_development_officer_lgu_funding` AS shs_project_development_officer_lgu_funding,
    r.`shs_project_development_officer_other_funding` AS shs_project_development_officer_other_funding,
    r.`shs_school_doctor_sef_provincial` AS shs_school_doctor_sef_provincial,
    r.`shs_school_doctor_sef_municipal_city` AS shs_school_doctor_sef_municipal_city,
    r.`shs_school_doctor_lgu_funding` AS shs_school_doctor_lgu_funding,
    r.`shs_school_doctor_other_funding` AS shs_school_doctor_other_funding,
    r.`shs_school_dentist_sef_provincial` AS shs_school_dentist_sef_provincial,
    r.`shs_school_dentist_sef_municipal_city` AS shs_school_dentist_sef_municipal_city,
    r.`shs_school_dentist_lgu_funding` AS shs_school_dentist_lgu_funding,
    r.`shs_school_dentist_other_funding` AS shs_school_dentist_other_funding,
    r.`shs_school_nurse_sef_provincial` AS shs_school_nurse_sef_provincial,
    r.`shs_school_nurse_sef_municipal_city` AS shs_school_nurse_sef_municipal_city,
    r.`shs_school_nurse_lgu_funding` AS shs_school_nurse_lgu_funding,
    r.`shs_school_nurse_other_funding` AS shs_school_nurse_other_funding,
    r.`shs_librarian_sef_provincial` AS shs_librarian_sef_provincial,
    r.`shs_librarian_sef_municipal_city` AS shs_librarian_sef_municipal_city,
    r.`shs_librarian_lgu_funding` AS shs_librarian_lgu_funding,
    r.`shs_librarian_other_funding` AS shs_librarian_other_funding,
    r.`shs_library_assistant_sef_provincial` AS shs_library_assistant_sef_provincial,
    r.`shs_library_assistant_sef_municipal_city` AS shs_library_assistant_sef_municipal_city,
    r.`shs_library_assistant_lgu_funding` AS shs_library_assistant_lgu_funding,
    r.`shs_library_assistant_other_funding` AS shs_library_assistant_other_funding,
    r.`shs_guidance_counselor_sef_provincial` AS shs_guidance_counselor_sef_provincial,
    r.`shs_guidance_counselor_sef_municipal_city` AS shs_guidance_counselor_sef_municipal_city,
    r.`shs_guidance_counselor_lgu_funding` AS shs_guidance_counselor_lgu_funding,
    r.`shs_guidance_counselor_other_funding` AS shs_guidance_counselor_other_funding,
    r.`shs_guidance_advocate_sef_provincial` AS shs_guidance_advocate_sef_provincial,
    r.`shs_guidance_advocate_sef_municipal_city` AS shs_guidance_advocate_sef_municipal_city,
    r.`shs_guidance_advocate_lgu_funding` AS shs_guidance_advocate_lgu_funding,
    r.`shs_guidance_advocate_other_funding` AS shs_guidance_advocate_other_funding,
    r.`shs_guidance_assistant_sef_provincial` AS shs_guidance_assistant_sef_provincial,
    r.`shs_guidance_assistant_sef_municipal_city` AS shs_guidance_assistant_sef_municipal_city,
    r.`shs_guidance_assistant_lgu_funding` AS shs_guidance_assistant_lgu_funding,
    r.`shs_guidance_assistant_other_funding` AS shs_guidance_assistant_other_funding,
    r.`shs_computer_technician_sef_provincial` AS shs_computer_technician_sef_provincial,
    r.`shs_computer_technician_sef_municipal_city` AS shs_computer_technician_sef_municipal_city,
    r.`shs_computer_technician_lgu_funding` AS shs_computer_technician_lgu_funding,
    r.`shs_computer_technician_other_funding` AS shs_computer_technician_other_funding,
    COUNT(*) OVER (PARTITION BY r.school_year, r.school_id) AS school_id_rows,
    COALESCE(CAST(e.kinder_male AS BIGINT), 0) + COALESCE(CAST(e.kinder_female AS BIGINT), 0) + COALESCE(CAST(e.g1_male AS BIGINT), 0) + COALESCE(CAST(e.g1_female AS BIGINT), 0) + COALESCE(CAST(e.g2_male AS BIGINT), 0) + COALESCE(CAST(e.g2_female AS BIGINT), 0) + COALESCE(CAST(e.g3_male AS BIGINT), 0) + COALESCE(CAST(e.g3_female AS BIGINT), 0) + COALESCE(CAST(e.g4_male AS BIGINT), 0) + COALESCE(CAST(e.g4_female AS BIGINT), 0) + COALESCE(CAST(e.g5_male AS BIGINT), 0) + COALESCE(CAST(e.g5_female AS BIGINT), 0) + COALESCE(CAST(e.g6_male AS BIGINT), 0) + COALESCE(CAST(e.g6_female AS BIGINT), 0) + COALESCE(CAST(e.esng_male AS BIGINT), 0) + COALESCE(CAST(e.esng_female AS BIGINT), 0) + COALESCE(CAST(e.g7_male AS BIGINT), 0) + COALESCE(CAST(e.g7_female AS BIGINT), 0) + COALESCE(CAST(e.g8_male AS BIGINT), 0) + COALESCE(CAST(e.g8_female AS BIGINT), 0) + COALESCE(CAST(e.g9_male AS BIGINT), 0) + COALESCE(CAST(e.g9_female AS BIGINT), 0) + COALESCE(CAST(e.g10_male AS BIGINT), 0) + COALESCE(CAST(e.g10_female AS BIGINT), 0) + COALESCE(CAST(e.jhsng_male AS BIGINT), 0) + COALESCE(CAST(e.jhsng_female AS BIGINT), 0) + COALESCE(CAST(e.g11_abm_male AS BIGINT), 0) + COALESCE(CAST(e.g11_abm_female AS BIGINT), 0) + COALESCE(CAST(e.g11_arts_male AS BIGINT), 0) + COALESCE(CAST(e.g11_arts_female AS BIGINT), 0) + COALESCE(CAST(e.g11_gas_male AS BIGINT), 0) + COALESCE(CAST(e.g11_gas_female AS BIGINT), 0) + COALESCE(CAST(e.g11_humss_male AS BIGINT), 0) + COALESCE(CAST(e.g11_humss_female AS BIGINT), 0) + COALESCE(CAST(e.g11_maritime_male AS BIGINT), 0) + COALESCE(CAST(e.g11_maritime_female AS BIGINT), 0) + COALESCE(CAST(e.g11_sports_male AS BIGINT), 0) + COALESCE(CAST(e.g11_sports_female AS BIGINT), 0) + COALESCE(CAST(e.g11_stem_male AS BIGINT), 0) + COALESCE(CAST(e.g11_stem_female AS BIGINT), 0) + COALESCE(CAST(e.g11_tvl_male AS BIGINT), 0) + COALESCE(CAST(e.g11_tvl_female AS BIGINT), 0) + COALESCE(CAST(e.g11_unique_male AS BIGINT), 0) + COALESCE(CAST(e.g11_unique_female AS BIGINT), 0) + COALESCE(CAST(e.g12_abm_male AS BIGINT), 0) + COALESCE(CAST(e.g12_abm_female AS BIGINT), 0) + COALESCE(CAST(e.g12_arts_male AS BIGINT), 0) + COALESCE(CAST(e.g12_arts_female AS BIGINT), 0) + COALESCE(CAST(e.g12_gas_male AS BIGINT), 0) + COALESCE(CAST(e.g12_gas_female AS BIGINT), 0) + COALESCE(CAST(e.g12_humss_male AS BIGINT), 0) + COALESCE(CAST(e.g12_humss_female AS BIGINT), 0) + COALESCE(CAST(e.g12_maritime_male AS BIGINT), 0) + COALESCE(CAST(e.g12_maritime_female AS BIGINT), 0) + COALESCE(CAST(e.g12_sports_male AS BIGINT), 0) + COALESCE(CAST(e.g12_sports_female AS BIGINT), 0) + COALESCE(CAST(e.g12_stem_male AS BIGINT), 0) + COALESCE(CAST(e.g12_stem_female AS BIGINT), 0) + COALESCE(CAST(e.g12_tvl_male AS BIGINT), 0) + COALESCE(CAST(e.g12_tvl_female AS BIGINT), 0) + COALESCE(CAST(e.g12_unique_male AS BIGINT), 0) + COALESCE(CAST(e.g12_unique_female AS BIGINT), 0) + COALESCE(CAST(e.g11_sshs_acad_male AS BIGINT), 0) + COALESCE(CAST(e.g11_sshs_acad_female AS BIGINT), 0) + COALESCE(CAST(e.g11_sshs_techpro_male AS BIGINT), 0) + COALESCE(CAST(e.g11_sshs_techpro_female AS BIGINT), 0) AS enrollment_total,
    r.batch_id,
    r.delivery_version,
    r.schema_version,
    r.source_sha256,
    r.source_row_number
  FROM bronze AS r LEFT JOIN enrollment AS e ON e.school_year = r.school_year AND e.school_id = r.school_id
), typed AS (
  SELECT
    n.school_year,
    n.school_id,
    n.sector,
    n.school_management,
    CASE WHEN n.offers_es IN ('True') THEN TRUE WHEN n.offers_es IN ('False') THEN FALSE END AS offers_es,
    CASE WHEN n.offers_jhs IN ('True') THEN TRUE WHEN n.offers_jhs IN ('False') THEN FALSE END AS offers_jhs,
    CASE WHEN n.offers_shs IN ('True') THEN TRUE WHEN n.offers_shs IN ('False') THEN FALSE END AS offers_shs,
    CASE WHEN regexp_like(n.es_master_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_iv AS INT) END AS es_master_teacher_iv,
    CASE WHEN regexp_like(n.es_master_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_iii AS INT) END AS es_master_teacher_iii,
    CASE WHEN regexp_like(n.es_master_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_ii AS INT) END AS es_master_teacher_ii,
    CASE WHEN regexp_like(n.es_master_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_i AS INT) END AS es_master_teacher_i,
    CASE WHEN regexp_like(n.es_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teacher_iii AS INT) END AS es_teacher_iii,
    CASE WHEN regexp_like(n.es_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teacher_ii AS INT) END AS es_teacher_ii,
    CASE WHEN regexp_like(n.es_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teacher_i AS INT) END AS es_teacher_i,
    CASE WHEN regexp_like(n.es_sped_sned_teacher_v, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_v AS INT) END AS es_sped_sned_teacher_v,
    CASE WHEN regexp_like(n.es_sped_sned_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_iv AS INT) END AS es_sped_sned_teacher_iv,
    CASE WHEN regexp_like(n.es_sped_sned_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_iii AS INT) END AS es_sped_sned_teacher_iii,
    CASE WHEN regexp_like(n.es_sped_sned_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_ii AS INT) END AS es_sped_sned_teacher_ii,
    CASE WHEN regexp_like(n.es_sped_sned_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_i AS INT) END AS es_sped_sned_teacher_i,
    CASE WHEN regexp_like(n.jhs_instructor_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_instructor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_instructor_iii AS INT) END AS jhs_instructor_iii,
    CASE WHEN regexp_like(n.jhs_instructor_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_instructor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_instructor_ii AS INT) END AS jhs_instructor_ii,
    CASE WHEN regexp_like(n.jhs_instructor_i, '^[0-9]+$') AND TRY_CAST(n.jhs_instructor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_instructor_i AS INT) END AS jhs_instructor_i,
    CASE WHEN regexp_like(n.jhs_master_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_iv AS INT) END AS jhs_master_teacher_iv,
    CASE WHEN regexp_like(n.jhs_master_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_iii AS INT) END AS jhs_master_teacher_iii,
    CASE WHEN regexp_like(n.jhs_master_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_ii AS INT) END AS jhs_master_teacher_ii,
    CASE WHEN regexp_like(n.jhs_master_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_i AS INT) END AS jhs_master_teacher_i,
    CASE WHEN regexp_like(n.jhs_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teacher_iii AS INT) END AS jhs_teacher_iii,
    CASE WHEN regexp_like(n.jhs_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teacher_ii AS INT) END AS jhs_teacher_ii,
    CASE WHEN regexp_like(n.jhs_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teacher_i AS INT) END AS jhs_teacher_i,
    CASE WHEN regexp_like(n.jhs_special_science_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_special_science_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_special_science_teacher_i AS INT) END AS jhs_special_science_teacher_i,
    CASE WHEN regexp_like(n.jhs_sped_teacher_v, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_v AS INT) END AS jhs_sped_teacher_v,
    CASE WHEN regexp_like(n.jhs_sped_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_iv AS INT) END AS jhs_sped_teacher_iv,
    CASE WHEN regexp_like(n.jhs_sped_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_iii AS INT) END AS jhs_sped_teacher_iii,
    CASE WHEN regexp_like(n.jhs_sped_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_ii AS INT) END AS jhs_sped_teacher_ii,
    CASE WHEN regexp_like(n.jhs_sped_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_i AS INT) END AS jhs_sped_teacher_i,
    CASE WHEN regexp_like(n.shs_master_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_iv AS INT) END AS shs_master_teacher_iv,
    CASE WHEN regexp_like(n.shs_master_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_iii AS INT) END AS shs_master_teacher_iii,
    CASE WHEN regexp_like(n.shs_master_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_ii AS INT) END AS shs_master_teacher_ii,
    CASE WHEN regexp_like(n.shs_master_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_i AS INT) END AS shs_master_teacher_i,
    CASE WHEN regexp_like(n.shs_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.shs_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teacher_iii AS INT) END AS shs_teacher_iii,
    CASE WHEN regexp_like(n.shs_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.shs_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teacher_ii AS INT) END AS shs_teacher_ii,
    CASE WHEN regexp_like(n.shs_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teacher_i AS INT) END AS shs_teacher_i,
    CASE WHEN regexp_like(n.shs_special_science_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_special_science_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_special_science_teacher_i AS INT) END AS shs_special_science_teacher_i,
    CASE WHEN regexp_like(n.es_school_principal_iv, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_iv AS INT) END AS es_school_principal_iv,
    CASE WHEN regexp_like(n.es_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_iii AS INT) END AS es_school_principal_iii,
    CASE WHEN regexp_like(n.es_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_ii AS INT) END AS es_school_principal_ii,
    CASE WHEN regexp_like(n.es_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_i AS INT) END AS es_school_principal_i,
    CASE WHEN regexp_like(n.es_head_teacher_vi, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_vi AS INT) END AS es_head_teacher_vi,
    CASE WHEN regexp_like(n.es_head_teacher_v, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_v AS INT) END AS es_head_teacher_v,
    CASE WHEN regexp_like(n.es_head_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_iv AS INT) END AS es_head_teacher_iv,
    CASE WHEN regexp_like(n.es_head_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_iii AS INT) END AS es_head_teacher_iii,
    CASE WHEN regexp_like(n.es_head_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_ii AS INT) END AS es_head_teacher_ii,
    CASE WHEN regexp_like(n.es_head_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_i AS INT) END AS es_head_teacher_i,
    CASE WHEN regexp_like(n.es_guidance_coordinator_iii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_coordinator_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_coordinator_iii AS INT) END AS es_guidance_coordinator_iii,
    CASE WHEN regexp_like(n.es_guidance_coordinator_ii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_coordinator_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_coordinator_ii AS INT) END AS es_guidance_coordinator_ii,
    CASE WHEN regexp_like(n.es_guidance_coordinator_i, '^[0-9]+$') AND TRY_CAST(n.es_guidance_coordinator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_coordinator_i AS INT) END AS es_guidance_coordinator_i,
    CASE WHEN regexp_like(n.es_guidance_counselor_iii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_iii AS INT) END AS es_guidance_counselor_iii,
    CASE WHEN regexp_like(n.es_guidance_counselor_ii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_ii AS INT) END AS es_guidance_counselor_ii,
    CASE WHEN regexp_like(n.es_guidance_counselor_i, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_i AS INT) END AS es_guidance_counselor_i,
    CASE WHEN regexp_like(n.es_administrative_officer_ii, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_ii AS INT) END AS es_administrative_officer_ii,
    CASE WHEN regexp_like(n.es_project_development_officer_i, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_i AS INT) END AS es_project_development_officer_i,
    CASE WHEN regexp_like(n.es_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_iii_senior_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_iii_senior_bookkeeper AS INT) END AS es_administrative_assistant_iii_senior_bookkeeper,
    CASE WHEN regexp_like(n.es_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_ii_disbursing_officer_ii AS INT) END AS es_administrative_assistant_ii_disbursing_officer_ii,
    CASE WHEN regexp_like(n.es_security_guard, '^[0-9]+$') AND TRY_CAST(n.es_security_guard AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_security_guard AS INT) END AS es_security_guard,
    CASE WHEN regexp_like(n.es_utility_worker_i, '^[0-9]+$') AND TRY_CAST(n.es_utility_worker_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_utility_worker_i AS INT) END AS es_utility_worker_i,
    CASE WHEN regexp_like(n.jhs_vocational_school_administrator_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_vocational_school_administrator_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_vocational_school_administrator_iii AS INT) END AS jhs_vocational_school_administrator_iii,
    CASE WHEN regexp_like(n.jhs_vocational_school_administrator_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_vocational_school_administrator_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_vocational_school_administrator_ii AS INT) END AS jhs_vocational_school_administrator_ii,
    CASE WHEN regexp_like(n.jhs_vocational_school_administrator_i, '^[0-9]+$') AND TRY_CAST(n.jhs_vocational_school_administrator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_vocational_school_administrator_i AS INT) END AS jhs_vocational_school_administrator_i,
    CASE WHEN regexp_like(n.jhs_school_principal_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_iv AS INT) END AS jhs_school_principal_iv,
    CASE WHEN regexp_like(n.jhs_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_iii AS INT) END AS jhs_school_principal_iii,
    CASE WHEN regexp_like(n.jhs_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_ii AS INT) END AS jhs_school_principal_ii,
    CASE WHEN regexp_like(n.jhs_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_i AS INT) END AS jhs_school_principal_i,
    CASE WHEN regexp_like(n.jhs_assistant_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_assistant_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_assistant_school_principal_iii AS INT) END AS jhs_assistant_school_principal_iii,
    CASE WHEN regexp_like(n.jhs_assistant_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_assistant_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_assistant_school_principal_ii AS INT) END AS jhs_assistant_school_principal_ii,
    CASE WHEN regexp_like(n.jhs_assistant_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.jhs_assistant_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_assistant_school_principal_i AS INT) END AS jhs_assistant_school_principal_i,
    CASE WHEN regexp_like(n.jhs_head_teacher_vi, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_vi AS INT) END AS jhs_head_teacher_vi,
    CASE WHEN regexp_like(n.jhs_head_teacher_v, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_v AS INT) END AS jhs_head_teacher_v,
    CASE WHEN regexp_like(n.jhs_head_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_iv AS INT) END AS jhs_head_teacher_iv,
    CASE WHEN regexp_like(n.jhs_head_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_iii AS INT) END AS jhs_head_teacher_iii,
    CASE WHEN regexp_like(n.jhs_head_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_ii AS INT) END AS jhs_head_teacher_ii,
    CASE WHEN regexp_like(n.jhs_head_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_i AS INT) END AS jhs_head_teacher_i,
    CASE WHEN regexp_like(n.jhs_guidance_coordinator_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_coordinator_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_coordinator_iii AS INT) END AS jhs_guidance_coordinator_iii,
    CASE WHEN regexp_like(n.jhs_guidance_coordinator_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_coordinator_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_coordinator_ii AS INT) END AS jhs_guidance_coordinator_ii,
    CASE WHEN regexp_like(n.jhs_guidance_coordinator_i, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_coordinator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_coordinator_i AS INT) END AS jhs_guidance_coordinator_i,
    CASE WHEN regexp_like(n.jhs_guidance_counselor_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_iii AS INT) END AS jhs_guidance_counselor_iii,
    CASE WHEN regexp_like(n.jhs_guidance_counselor_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_ii AS INT) END AS jhs_guidance_counselor_ii,
    CASE WHEN regexp_like(n.jhs_guidance_counselor_i, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_i AS INT) END AS jhs_guidance_counselor_i,
    CASE WHEN regexp_like(n.jhs_administrative_officer_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_iv AS INT) END AS jhs_administrative_officer_iv,
    CASE WHEN regexp_like(n.jhs_administrative_officer_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_ii AS INT) END AS jhs_administrative_officer_ii,
    CASE WHEN regexp_like(n.jhs_project_development_officer_i, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_i AS INT) END AS jhs_project_development_officer_i,
    CASE WHEN regexp_like(n.jhs_school_librarian_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_librarian_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_librarian_iii AS INT) END AS jhs_school_librarian_iii,
    CASE WHEN regexp_like(n.jhs_school_librarian_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_librarian_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_librarian_ii AS INT) END AS jhs_school_librarian_ii,
    CASE WHEN regexp_like(n.jhs_school_librarian_i, '^[0-9]+$') AND TRY_CAST(n.jhs_school_librarian_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_librarian_i AS INT) END AS jhs_school_librarian_i,
    CASE WHEN regexp_like(n.jhs_accountant_i, '^[0-9]+$') AND TRY_CAST(n.jhs_accountant_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_accountant_i AS INT) END AS jhs_accountant_i,
    CASE WHEN regexp_like(n.jhs_cashier_i, '^[0-9]+$') AND TRY_CAST(n.jhs_cashier_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_cashier_i AS INT) END AS jhs_cashier_i,
    CASE WHEN regexp_like(n.jhs_supply_officer_i, '^[0-9]+$') AND TRY_CAST(n.jhs_supply_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_supply_officer_i AS INT) END AS jhs_supply_officer_i,
    CASE WHEN regexp_like(n.jhs_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_iii_senior_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_iii_senior_bookkeeper AS INT) END AS jhs_administrative_assistant_iii_senior_bookkeeper,
    CASE WHEN regexp_like(n.jhs_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.jhs_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_bookkeeper AS INT) END AS jhs_bookkeeper,
    CASE WHEN regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_ii AS INT) END AS jhs_administrative_assistant_ii_disbursing_officer_ii,
    CASE WHEN regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_i, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_i AS INT) END AS jhs_administrative_assistant_ii_disbursing_officer_i,
    CASE WHEN regexp_like(n.jhs_administrative_aide_vi, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_vi AS INT) END AS jhs_administrative_aide_vi,
    CASE WHEN regexp_like(n.jhs_heavy_equipment_operator_i, '^[0-9]+$') AND TRY_CAST(n.jhs_heavy_equipment_operator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_heavy_equipment_operator_i AS INT) END AS jhs_heavy_equipment_operator_i,
    CASE WHEN regexp_like(n.jhs_driver_i, '^[0-9]+$') AND TRY_CAST(n.jhs_driver_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_driver_i AS INT) END AS jhs_driver_i,
    CASE WHEN regexp_like(n.jhs_security_guard_i, '^[0-9]+$') AND TRY_CAST(n.jhs_security_guard_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_security_guard_i AS INT) END AS jhs_security_guard_i,
    CASE WHEN regexp_like(n.jhs_light_equipment_operator, '^[0-9]+$') AND TRY_CAST(n.jhs_light_equipment_operator AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_light_equipment_operator AS INT) END AS jhs_light_equipment_operator,
    CASE WHEN regexp_like(n.jhs_utility_worker_i, '^[0-9]+$') AND TRY_CAST(n.jhs_utility_worker_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_utility_worker_i AS INT) END AS jhs_utility_worker_i,
    CASE WHEN regexp_like(n.shs_school_principal_iv, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_iv AS INT) END AS shs_school_principal_iv,
    CASE WHEN regexp_like(n.shs_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_iii AS INT) END AS shs_school_principal_iii,
    CASE WHEN regexp_like(n.shs_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_ii AS INT) END AS shs_school_principal_ii,
    CASE WHEN regexp_like(n.shs_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_i AS INT) END AS shs_school_principal_i,
    CASE WHEN regexp_like(n.shs_total_school_principal, '^[0-9]+$') AND TRY_CAST(n.shs_total_school_principal AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_total_school_principal AS INT) END AS shs_total_school_principal,
    CASE WHEN regexp_like(n.shs_assistant_principal_iii, '^[0-9]+$') AND TRY_CAST(n.shs_assistant_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_assistant_principal_iii AS INT) END AS shs_assistant_principal_iii,
    CASE WHEN regexp_like(n.shs_assistant_principal_ii, '^[0-9]+$') AND TRY_CAST(n.shs_assistant_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_assistant_principal_ii AS INT) END AS shs_assistant_principal_ii,
    CASE WHEN regexp_like(n.shs_assistant_principal_i, '^[0-9]+$') AND TRY_CAST(n.shs_assistant_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_assistant_principal_i AS INT) END AS shs_assistant_principal_i,
    CASE WHEN regexp_like(n.shs_head_teacher_vi, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_vi AS INT) END AS shs_head_teacher_vi,
    CASE WHEN regexp_like(n.shs_head_teacher_v, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_v AS INT) END AS shs_head_teacher_v,
    CASE WHEN regexp_like(n.shs_head_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_iv AS INT) END AS shs_head_teacher_iv,
    CASE WHEN regexp_like(n.shs_head_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_iii AS INT) END AS shs_head_teacher_iii,
    CASE WHEN regexp_like(n.shs_head_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_ii AS INT) END AS shs_head_teacher_ii,
    CASE WHEN regexp_like(n.shs_head_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_i AS INT) END AS shs_head_teacher_i,
    CASE WHEN regexp_like(n.shs_school_nurse_ii, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_ii AS INT) END AS shs_school_nurse_ii,
    CASE WHEN regexp_like(n.shs_administrative_officer_iv, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_iv AS INT) END AS shs_administrative_officer_iv,
    CASE WHEN regexp_like(n.shs_administrative_officer_ii, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_ii AS INT) END AS shs_administrative_officer_ii,
    CASE WHEN regexp_like(n.shs_school_librarian_iii, '^[0-9]+$') AND TRY_CAST(n.shs_school_librarian_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_librarian_iii AS INT) END AS shs_school_librarian_iii,
    CASE WHEN regexp_like(n.shs_school_librarian_ii, '^[0-9]+$') AND TRY_CAST(n.shs_school_librarian_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_librarian_ii AS INT) END AS shs_school_librarian_ii,
    CASE WHEN regexp_like(n.shs_school_librarian_i, '^[0-9]+$') AND TRY_CAST(n.shs_school_librarian_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_librarian_i AS INT) END AS shs_school_librarian_i,
    CASE WHEN regexp_like(n.shs_guidance_service_specialist_ii, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_service_specialist_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_service_specialist_ii AS INT) END AS shs_guidance_service_specialist_ii,
    CASE WHEN regexp_like(n.shs_guidance_service_specialist_i, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_service_specialist_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_service_specialist_i AS INT) END AS shs_guidance_service_specialist_i,
    CASE WHEN regexp_like(n.shs_guidance_counselor_iii, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_iii AS INT) END AS shs_guidance_counselor_iii,
    CASE WHEN regexp_like(n.shs_guidance_counselor_ii, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_ii AS INT) END AS shs_guidance_counselor_ii,
    CASE WHEN regexp_like(n.shs_guidance_counselor_i, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_i AS INT) END AS shs_guidance_counselor_i,
    CASE WHEN regexp_like(n.shs_accounting_i, '^[0-9]+$') AND TRY_CAST(n.shs_accounting_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_accounting_i AS INT) END AS shs_accounting_i,
    CASE WHEN regexp_like(n.shs_project_development_officer_i, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_i AS INT) END AS shs_project_development_officer_i,
    CASE WHEN regexp_like(n.shs_registrar_i, '^[0-9]+$') AND TRY_CAST(n.shs_registrar_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_registrar_i AS INT) END AS shs_registrar_i,
    CASE WHEN regexp_like(n.shs_cashier_i, '^[0-9]+$') AND TRY_CAST(n.shs_cashier_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_cashier_i AS INT) END AS shs_cashier_i,
    CASE WHEN regexp_like(n.shs_supply_officer_i, '^[0-9]+$') AND TRY_CAST(n.shs_supply_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_supply_officer_i AS INT) END AS shs_supply_officer_i,
    CASE WHEN regexp_like(n.shs_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_iii_senior_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_iii_senior_bookkeeper AS INT) END AS shs_administrative_assistant_iii_senior_bookkeeper,
    CASE WHEN regexp_like(n.shs_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_ii_disbursing_officer_ii AS INT) END AS shs_administrative_assistant_ii_disbursing_officer_ii,
    CASE WHEN regexp_like(n.shs_administrative_assistant_i, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_i AS INT) END AS shs_administrative_assistant_i,
    CASE WHEN regexp_like(n.shs_administrative_aide_vi, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_vi AS INT) END AS shs_administrative_aide_vi,
    CASE WHEN regexp_like(n.shs_heavy_equipment_operator_i, '^[0-9]+$') AND TRY_CAST(n.shs_heavy_equipment_operator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_heavy_equipment_operator_i AS INT) END AS shs_heavy_equipment_operator_i,
    CASE WHEN regexp_like(n.shs_security_guard_i, '^[0-9]+$') AND TRY_CAST(n.shs_security_guard_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_security_guard_i AS INT) END AS shs_security_guard_i,
    CASE WHEN regexp_like(n.shs_light_equipment_operator_i, '^[0-9]+$') AND TRY_CAST(n.shs_light_equipment_operator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_light_equipment_operator_i AS INT) END AS shs_light_equipment_operator_i,
    CASE WHEN regexp_like(n.shs_utility_worker_i, '^[0-9]+$') AND TRY_CAST(n.shs_utility_worker_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_utility_worker_i AS INT) END AS shs_utility_worker_i,
    CASE WHEN regexp_like(n.kinder_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_sef_province AS INT) END AS kinder_teachers_sef_province,
    CASE WHEN regexp_like(n.kinder_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_sef_municipality_city AS INT) END AS kinder_teachers_sef_municipality_city,
    CASE WHEN regexp_like(n.kinder_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_lgu_funding AS INT) END AS kinder_teachers_lgu_funding,
    CASE WHEN regexp_like(n.kinder_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_other_funding AS INT) END AS kinder_teachers_other_funding,
    CASE WHEN regexp_like(n.es_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.es_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_sef_province AS INT) END AS es_teachers_sef_province,
    CASE WHEN regexp_like(n.es_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.es_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_sef_municipality_city AS INT) END AS es_teachers_sef_municipality_city,
    CASE WHEN regexp_like(n.es_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_lgu_funding AS INT) END AS es_teachers_lgu_funding,
    CASE WHEN regexp_like(n.es_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_other_funding AS INT) END AS es_teachers_other_funding,
    CASE WHEN regexp_like(n.jhs_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_sef_province AS INT) END AS jhs_teachers_sef_province,
    CASE WHEN regexp_like(n.jhs_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_sef_municipality_city AS INT) END AS jhs_teachers_sef_municipality_city,
    CASE WHEN regexp_like(n.jhs_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_lgu_funding AS INT) END AS jhs_teachers_lgu_funding,
    CASE WHEN regexp_like(n.jhs_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_other_funding AS INT) END AS jhs_teachers_other_funding,
    CASE WHEN regexp_like(n.shs_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_sef_province AS INT) END AS shs_teachers_sef_province,
    CASE WHEN regexp_like(n.shs_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_sef_municipality_city AS INT) END AS shs_teachers_sef_municipality_city,
    CASE WHEN regexp_like(n.shs_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_lgu_funding AS INT) END AS shs_teachers_lgu_funding,
    CASE WHEN regexp_like(n.shs_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_other_funding AS INT) END AS shs_teachers_other_funding,
    CASE WHEN regexp_like(n.es_learning_support_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_sef_provincial AS INT) END AS es_learning_support_aide_sef_provincial,
    CASE WHEN regexp_like(n.es_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_sef_municipal_city AS INT) END AS es_learning_support_aide_sef_municipal_city,
    CASE WHEN regexp_like(n.es_learning_support_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_lgu_funding AS INT) END AS es_learning_support_aide_lgu_funding,
    CASE WHEN regexp_like(n.es_learning_support_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_other_funding AS INT) END AS es_learning_support_aide_other_funding,
    CASE WHEN regexp_like(n.es_administrative_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_sef_provincial AS INT) END AS es_administrative_officer_sef_provincial,
    CASE WHEN regexp_like(n.es_administrative_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_sef_municipal_city AS INT) END AS es_administrative_officer_sef_municipal_city,
    CASE WHEN regexp_like(n.es_administrative_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_lgu_funding AS INT) END AS es_administrative_officer_lgu_funding,
    CASE WHEN regexp_like(n.es_administrative_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_other_funding AS INT) END AS es_administrative_officer_other_funding,
    CASE WHEN regexp_like(n.es_administrative_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_sef_provincial AS INT) END AS es_administrative_assistant_sef_provincial,
    CASE WHEN regexp_like(n.es_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_sef_municipal_city AS INT) END AS es_administrative_assistant_sef_municipal_city,
    CASE WHEN regexp_like(n.es_administrative_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_lgu_funding AS INT) END AS es_administrative_assistant_lgu_funding,
    CASE WHEN regexp_like(n.es_administrative_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_other_funding AS INT) END AS es_administrative_assistant_other_funding,
    CASE WHEN regexp_like(n.es_administrative_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_sef_provincial AS INT) END AS es_administrative_aide_sef_provincial,
    CASE WHEN regexp_like(n.es_administrative_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_sef_municipal_city AS INT) END AS es_administrative_aide_sef_municipal_city,
    CASE WHEN regexp_like(n.es_administrative_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_lgu_funding AS INT) END AS es_administrative_aide_lgu_funding,
    CASE WHEN regexp_like(n.es_administrative_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_other_funding AS INT) END AS es_administrative_aide_other_funding,
    CASE WHEN regexp_like(n.es_project_development_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_sef_provincial AS INT) END AS es_project_development_officer_sef_provincial,
    CASE WHEN regexp_like(n.es_project_development_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_sef_municipal_city AS INT) END AS es_project_development_officer_sef_municipal_city,
    CASE WHEN regexp_like(n.es_project_development_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_lgu_funding AS INT) END AS es_project_development_officer_lgu_funding,
    CASE WHEN regexp_like(n.es_project_development_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_other_funding AS INT) END AS es_project_development_officer_other_funding,
    CASE WHEN regexp_like(n.es_school_doctor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_sef_provincial AS INT) END AS es_school_doctor_sef_provincial,
    CASE WHEN regexp_like(n.es_school_doctor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_sef_municipal_city AS INT) END AS es_school_doctor_sef_municipal_city,
    CASE WHEN regexp_like(n.es_school_doctor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_lgu_funding AS INT) END AS es_school_doctor_lgu_funding,
    CASE WHEN regexp_like(n.es_school_doctor_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_other_funding AS INT) END AS es_school_doctor_other_funding,
    CASE WHEN regexp_like(n.es_school_dentist_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_sef_provincial AS INT) END AS es_school_dentist_sef_provincial,
    CASE WHEN regexp_like(n.es_school_dentist_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_sef_municipal_city AS INT) END AS es_school_dentist_sef_municipal_city,
    CASE WHEN regexp_like(n.es_school_dentist_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_lgu_funding AS INT) END AS es_school_dentist_lgu_funding,
    CASE WHEN regexp_like(n.es_school_dentist_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_other_funding AS INT) END AS es_school_dentist_other_funding,
    CASE WHEN regexp_like(n.es_school_nurse_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_sef_provincial AS INT) END AS es_school_nurse_sef_provincial,
    CASE WHEN regexp_like(n.es_school_nurse_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_sef_municipal_city AS INT) END AS es_school_nurse_sef_municipal_city,
    CASE WHEN regexp_like(n.es_school_nurse_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_lgu_funding AS INT) END AS es_school_nurse_lgu_funding,
    CASE WHEN regexp_like(n.es_school_nurse_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_other_funding AS INT) END AS es_school_nurse_other_funding,
    CASE WHEN regexp_like(n.es_librarian_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_librarian_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_sef_provincial AS INT) END AS es_librarian_sef_provincial,
    CASE WHEN regexp_like(n.es_librarian_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_librarian_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_sef_municipal_city AS INT) END AS es_librarian_sef_municipal_city,
    CASE WHEN regexp_like(n.es_librarian_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_librarian_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_lgu_funding AS INT) END AS es_librarian_lgu_funding,
    CASE WHEN regexp_like(n.es_librarian_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_librarian_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_other_funding AS INT) END AS es_librarian_other_funding,
    CASE WHEN regexp_like(n.es_library_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_sef_provincial AS INT) END AS es_library_assistant_sef_provincial,
    CASE WHEN regexp_like(n.es_library_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_sef_municipal_city AS INT) END AS es_library_assistant_sef_municipal_city,
    CASE WHEN regexp_like(n.es_library_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_lgu_funding AS INT) END AS es_library_assistant_lgu_funding,
    CASE WHEN regexp_like(n.es_library_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_other_funding AS INT) END AS es_library_assistant_other_funding,
    CASE WHEN regexp_like(n.es_guidance_counselor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_sef_provincial AS INT) END AS es_guidance_counselor_sef_provincial,
    CASE WHEN regexp_like(n.es_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_sef_municipal_city AS INT) END AS es_guidance_counselor_sef_municipal_city,
    CASE WHEN regexp_like(n.es_guidance_counselor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_lgu_funding AS INT) END AS es_guidance_counselor_lgu_funding,
    CASE WHEN regexp_like(n.es_guidance_counselor_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_other_funding AS INT) END AS es_guidance_counselor_other_funding,
    CASE WHEN regexp_like(n.es_guidance_advocate_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_sef_provincial AS INT) END AS es_guidance_advocate_sef_provincial,
    CASE WHEN regexp_like(n.es_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_sef_municipal_city AS INT) END AS es_guidance_advocate_sef_municipal_city,
    CASE WHEN regexp_like(n.es_guidance_advocate_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_lgu_funding AS INT) END AS es_guidance_advocate_lgu_funding,
    CASE WHEN regexp_like(n.es_guidance_advocate_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_other_funding AS INT) END AS es_guidance_advocate_other_funding,
    CASE WHEN regexp_like(n.es_guidance_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_sef_provincial AS INT) END AS es_guidance_assistant_sef_provincial,
    CASE WHEN regexp_like(n.es_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_sef_municipal_city AS INT) END AS es_guidance_assistant_sef_municipal_city,
    CASE WHEN regexp_like(n.es_guidance_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_lgu_funding AS INT) END AS es_guidance_assistant_lgu_funding,
    CASE WHEN regexp_like(n.es_guidance_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_other_funding AS INT) END AS es_guidance_assistant_other_funding,
    CASE WHEN regexp_like(n.es_computer_technician_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_sef_provincial AS INT) END AS es_computer_technician_sef_provincial,
    CASE WHEN regexp_like(n.es_computer_technician_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_sef_municipal_city AS INT) END AS es_computer_technician_sef_municipal_city,
    CASE WHEN regexp_like(n.es_computer_technician_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_lgu_funding AS INT) END AS es_computer_technician_lgu_funding,
    CASE WHEN regexp_like(n.es_computer_technician_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_other_funding AS INT) END AS es_computer_technician_other_funding,
    CASE WHEN regexp_like(n.jhs_learning_support_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_sef_provincial AS INT) END AS jhs_learning_support_aide_sef_provincial,
    CASE WHEN regexp_like(n.jhs_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_sef_municipal_city AS INT) END AS jhs_learning_support_aide_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_learning_support_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_lgu_funding AS INT) END AS jhs_learning_support_aide_lgu_funding,
    CASE WHEN regexp_like(n.jhs_learning_support_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_other_funding AS INT) END AS jhs_learning_support_aide_other_funding,
    CASE WHEN regexp_like(n.jhs_administrative_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_sef_provincial AS INT) END AS jhs_administrative_officer_sef_provincial,
    CASE WHEN regexp_like(n.jhs_administrative_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_sef_municipal_city AS INT) END AS jhs_administrative_officer_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_administrative_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_lgu_funding AS INT) END AS jhs_administrative_officer_lgu_funding,
    CASE WHEN regexp_like(n.jhs_administrative_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_other_funding AS INT) END AS jhs_administrative_officer_other_funding,
    CASE WHEN regexp_like(n.jhs_administrative_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_sef_provincial AS INT) END AS jhs_administrative_assistant_sef_provincial,
    CASE WHEN regexp_like(n.jhs_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_sef_municipal_city AS INT) END AS jhs_administrative_assistant_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_administrative_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_lgu_funding AS INT) END AS jhs_administrative_assistant_lgu_funding,
    CASE WHEN regexp_like(n.jhs_administrative_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_other_funding AS INT) END AS jhs_administrative_assistant_other_funding,
    CASE WHEN regexp_like(n.jhs_administrative_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_sef_provincial AS INT) END AS jhs_administrative_aide_sef_provincial,
    CASE WHEN regexp_like(n.jhs_administrative_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_sef_municipal_city AS INT) END AS jhs_administrative_aide_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_administrative_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_lgu_funding AS INT) END AS jhs_administrative_aide_lgu_funding,
    CASE WHEN regexp_like(n.jhs_administrative_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_other_funding AS INT) END AS jhs_administrative_aide_other_funding,
    CASE WHEN regexp_like(n.jhs_project_development_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_sef_provincial AS INT) END AS jhs_project_development_officer_sef_provincial,
    CASE WHEN regexp_like(n.jhs_project_development_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_sef_municipal_city AS INT) END AS jhs_project_development_officer_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_project_development_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_lgu_funding AS INT) END AS jhs_project_development_officer_lgu_funding,
    CASE WHEN regexp_like(n.jhs_project_development_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_other_funding AS INT) END AS jhs_project_development_officer_other_funding,
    CASE WHEN regexp_like(n.jhs_school_doctor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_sef_provincial AS INT) END AS jhs_school_doctor_sef_provincial,
    CASE WHEN regexp_like(n.jhs_school_doctor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_sef_municipal_city AS INT) END AS jhs_school_doctor_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_school_doctor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_lgu_funding AS INT) END AS jhs_school_doctor_lgu_funding,
    CASE WHEN regexp_like(n.jhs_school_doctor_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_other_funding AS INT) END AS jhs_school_doctor_other_funding,
    CASE WHEN regexp_like(n.jhs_school_dentist_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_sef_provincial AS INT) END AS jhs_school_dentist_sef_provincial,
    CASE WHEN regexp_like(n.jhs_school_dentist_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_sef_municipal_city AS INT) END AS jhs_school_dentist_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_school_dentist_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_lgu_funding AS INT) END AS jhs_school_dentist_lgu_funding,
    CASE WHEN regexp_like(n.jhs_school_dentist_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_other_funding AS INT) END AS jhs_school_dentist_other_funding,
    CASE WHEN regexp_like(n.jhs_school_nurse_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_sef_provincial AS INT) END AS jhs_school_nurse_sef_provincial,
    CASE WHEN regexp_like(n.jhs_school_nurse_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_sef_municipal_city AS INT) END AS jhs_school_nurse_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_school_nurse_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_lgu_funding AS INT) END AS jhs_school_nurse_lgu_funding,
    CASE WHEN regexp_like(n.jhs_school_nurse_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_other_funding AS INT) END AS jhs_school_nurse_other_funding,
    CASE WHEN regexp_like(n.jhs_librarian_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_sef_provincial AS INT) END AS jhs_librarian_sef_provincial,
    CASE WHEN regexp_like(n.jhs_librarian_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_sef_municipal_city AS INT) END AS jhs_librarian_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_librarian_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_lgu_funding AS INT) END AS jhs_librarian_lgu_funding,
    CASE WHEN regexp_like(n.jhs_librarian_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_other_funding AS INT) END AS jhs_librarian_other_funding,
    CASE WHEN regexp_like(n.jhs_library_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_sef_provincial AS INT) END AS jhs_library_assistant_sef_provincial,
    CASE WHEN regexp_like(n.jhs_library_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_sef_municipal_city AS INT) END AS jhs_library_assistant_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_library_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_lgu_funding AS INT) END AS jhs_library_assistant_lgu_funding,
    CASE WHEN regexp_like(n.jhs_library_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_other_funding AS INT) END AS jhs_library_assistant_other_funding,
    CASE WHEN regexp_like(n.jhs_guidance_counselor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_sef_provincial AS INT) END AS jhs_guidance_counselor_sef_provincial,
    CASE WHEN regexp_like(n.jhs_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_sef_municipal_city AS INT) END AS jhs_guidance_counselor_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_guidance_counselor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_lgu_funding AS INT) END AS jhs_guidance_counselor_lgu_funding,
    CASE WHEN regexp_like(n.jhs_guidance_counselor_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_other_funding AS INT) END AS jhs_guidance_counselor_other_funding,
    CASE WHEN regexp_like(n.jhs_guidance_advocate_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_sef_provincial AS INT) END AS jhs_guidance_advocate_sef_provincial,
    CASE WHEN regexp_like(n.jhs_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_sef_municipal_city AS INT) END AS jhs_guidance_advocate_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_guidance_advocate_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_lgu_funding AS INT) END AS jhs_guidance_advocate_lgu_funding,
    CASE WHEN regexp_like(n.jhs_guidance_advocate_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_other_funding AS INT) END AS jhs_guidance_advocate_other_funding,
    CASE WHEN regexp_like(n.jhs_guidance_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_sef_provincial AS INT) END AS jhs_guidance_assistant_sef_provincial,
    CASE WHEN regexp_like(n.jhs_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_sef_municipal_city AS INT) END AS jhs_guidance_assistant_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_guidance_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_lgu_funding AS INT) END AS jhs_guidance_assistant_lgu_funding,
    CASE WHEN regexp_like(n.jhs_guidance_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_other_funding AS INT) END AS jhs_guidance_assistant_other_funding,
    CASE WHEN regexp_like(n.jhs_computer_technician_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_sef_provincial AS INT) END AS jhs_computer_technician_sef_provincial,
    CASE WHEN regexp_like(n.jhs_computer_technician_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_sef_municipal_city AS INT) END AS jhs_computer_technician_sef_municipal_city,
    CASE WHEN regexp_like(n.jhs_computer_technician_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_lgu_funding AS INT) END AS jhs_computer_technician_lgu_funding,
    CASE WHEN regexp_like(n.jhs_computer_technician_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_other_funding AS INT) END AS jhs_computer_technician_other_funding,
    CASE WHEN regexp_like(n.shs_learning_support_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_sef_provincial AS INT) END AS shs_learning_support_aide_sef_provincial,
    CASE WHEN regexp_like(n.shs_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_sef_municipal_city AS INT) END AS shs_learning_support_aide_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_learning_support_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_lgu_funding AS INT) END AS shs_learning_support_aide_lgu_funding,
    CASE WHEN regexp_like(n.shs_learning_support_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_other_funding AS INT) END AS shs_learning_support_aide_other_funding,
    CASE WHEN regexp_like(n.shs_administrative_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_sef_provincial AS INT) END AS shs_administrative_officer_sef_provincial,
    CASE WHEN regexp_like(n.shs_administrative_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_sef_municipal_city AS INT) END AS shs_administrative_officer_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_administrative_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_lgu_funding AS INT) END AS shs_administrative_officer_lgu_funding,
    CASE WHEN regexp_like(n.shs_administrative_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_other_funding AS INT) END AS shs_administrative_officer_other_funding,
    CASE WHEN regexp_like(n.shs_administrative_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_sef_provincial AS INT) END AS shs_administrative_assistant_sef_provincial,
    CASE WHEN regexp_like(n.shs_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_sef_municipal_city AS INT) END AS shs_administrative_assistant_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_administrative_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_lgu_funding AS INT) END AS shs_administrative_assistant_lgu_funding,
    CASE WHEN regexp_like(n.shs_administrative_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_other_funding AS INT) END AS shs_administrative_assistant_other_funding,
    CASE WHEN regexp_like(n.shs_administrative_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_sef_provincial AS INT) END AS shs_administrative_aide_sef_provincial,
    CASE WHEN regexp_like(n.shs_administrative_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_sef_municipal_city AS INT) END AS shs_administrative_aide_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_administrative_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_lgu_funding AS INT) END AS shs_administrative_aide_lgu_funding,
    CASE WHEN regexp_like(n.shs_administrative_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_other_funding AS INT) END AS shs_administrative_aide_other_funding,
    CASE WHEN regexp_like(n.shs_project_development_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_sef_provincial AS INT) END AS shs_project_development_officer_sef_provincial,
    CASE WHEN regexp_like(n.shs_project_development_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_sef_municipal_city AS INT) END AS shs_project_development_officer_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_project_development_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_lgu_funding AS INT) END AS shs_project_development_officer_lgu_funding,
    CASE WHEN regexp_like(n.shs_project_development_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_other_funding AS INT) END AS shs_project_development_officer_other_funding,
    CASE WHEN regexp_like(n.shs_school_doctor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_sef_provincial AS INT) END AS shs_school_doctor_sef_provincial,
    CASE WHEN regexp_like(n.shs_school_doctor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_sef_municipal_city AS INT) END AS shs_school_doctor_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_school_doctor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_lgu_funding AS INT) END AS shs_school_doctor_lgu_funding,
    CASE WHEN regexp_like(n.shs_school_doctor_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_other_funding AS INT) END AS shs_school_doctor_other_funding,
    CASE WHEN regexp_like(n.shs_school_dentist_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_sef_provincial AS INT) END AS shs_school_dentist_sef_provincial,
    CASE WHEN regexp_like(n.shs_school_dentist_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_sef_municipal_city AS INT) END AS shs_school_dentist_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_school_dentist_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_lgu_funding AS INT) END AS shs_school_dentist_lgu_funding,
    CASE WHEN regexp_like(n.shs_school_dentist_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_other_funding AS INT) END AS shs_school_dentist_other_funding,
    CASE WHEN regexp_like(n.shs_school_nurse_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_sef_provincial AS INT) END AS shs_school_nurse_sef_provincial,
    CASE WHEN regexp_like(n.shs_school_nurse_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_sef_municipal_city AS INT) END AS shs_school_nurse_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_school_nurse_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_lgu_funding AS INT) END AS shs_school_nurse_lgu_funding,
    CASE WHEN regexp_like(n.shs_school_nurse_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_other_funding AS INT) END AS shs_school_nurse_other_funding,
    CASE WHEN regexp_like(n.shs_librarian_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_sef_provincial AS INT) END AS shs_librarian_sef_provincial,
    CASE WHEN regexp_like(n.shs_librarian_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_sef_municipal_city AS INT) END AS shs_librarian_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_librarian_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_lgu_funding AS INT) END AS shs_librarian_lgu_funding,
    CASE WHEN regexp_like(n.shs_librarian_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_other_funding AS INT) END AS shs_librarian_other_funding,
    CASE WHEN regexp_like(n.shs_library_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_sef_provincial AS INT) END AS shs_library_assistant_sef_provincial,
    CASE WHEN regexp_like(n.shs_library_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_sef_municipal_city AS INT) END AS shs_library_assistant_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_library_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_lgu_funding AS INT) END AS shs_library_assistant_lgu_funding,
    CASE WHEN regexp_like(n.shs_library_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_other_funding AS INT) END AS shs_library_assistant_other_funding,
    CASE WHEN regexp_like(n.shs_guidance_counselor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_sef_provincial AS INT) END AS shs_guidance_counselor_sef_provincial,
    CASE WHEN regexp_like(n.shs_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_sef_municipal_city AS INT) END AS shs_guidance_counselor_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_guidance_counselor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_lgu_funding AS INT) END AS shs_guidance_counselor_lgu_funding,
    CASE WHEN regexp_like(n.shs_guidance_counselor_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_other_funding AS INT) END AS shs_guidance_counselor_other_funding,
    CASE WHEN regexp_like(n.shs_guidance_advocate_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_sef_provincial AS INT) END AS shs_guidance_advocate_sef_provincial,
    CASE WHEN regexp_like(n.shs_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_sef_municipal_city AS INT) END AS shs_guidance_advocate_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_guidance_advocate_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_lgu_funding AS INT) END AS shs_guidance_advocate_lgu_funding,
    CASE WHEN regexp_like(n.shs_guidance_advocate_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_other_funding AS INT) END AS shs_guidance_advocate_other_funding,
    CASE WHEN regexp_like(n.shs_guidance_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_sef_provincial AS INT) END AS shs_guidance_assistant_sef_provincial,
    CASE WHEN regexp_like(n.shs_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_sef_municipal_city AS INT) END AS shs_guidance_assistant_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_guidance_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_lgu_funding AS INT) END AS shs_guidance_assistant_lgu_funding,
    CASE WHEN regexp_like(n.shs_guidance_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_other_funding AS INT) END AS shs_guidance_assistant_other_funding,
    CASE WHEN regexp_like(n.shs_computer_technician_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_sef_provincial AS INT) END AS shs_computer_technician_sef_provincial,
    CASE WHEN regexp_like(n.shs_computer_technician_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_sef_municipal_city AS INT) END AS shs_computer_technician_sef_municipal_city,
    CASE WHEN regexp_like(n.shs_computer_technician_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_lgu_funding AS INT) END AS shs_computer_technician_lgu_funding,
    CASE WHEN regexp_like(n.shs_computer_technician_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_other_funding AS INT) END AS shs_computer_technician_other_funding,
    n.school_id_rows,
    n.enrollment_total,
    n.batch_id,
    n.delivery_version,
    n.schema_version,
    n.source_sha256,
    n.source_row_number,
    concat_ws(',',
      CASE WHEN n.school_id IS NULL OR n.school_id = '' THEN 'school_id_blank' END,
      CASE WHEN n.school_id <> '' AND NOT regexp_like(n.school_id, '^[0-9]{6}$') THEN 'school_id_malformed' END,
      CASE WHEN n.school_id <> '' AND n.school_id_rows > 1 THEN 'school_id_duplicated' END,
      CASE WHEN regexp_like(n.es_master_teacher_iv, '^-[0-9]+$')
        OR regexp_like(n.es_master_teacher_iii, '^-[0-9]+$')
        OR regexp_like(n.es_master_teacher_ii, '^-[0-9]+$')
        OR regexp_like(n.es_master_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.es_teacher_iii, '^-[0-9]+$')
        OR regexp_like(n.es_teacher_ii, '^-[0-9]+$')
        OR regexp_like(n.es_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.es_sped_sned_teacher_v, '^-[0-9]+$')
        OR regexp_like(n.es_sped_sned_teacher_iv, '^-[0-9]+$')
        OR regexp_like(n.es_sped_sned_teacher_iii, '^-[0-9]+$')
        OR regexp_like(n.es_sped_sned_teacher_ii, '^-[0-9]+$')
        OR regexp_like(n.es_sped_sned_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_instructor_iii, '^-[0-9]+$')
        OR regexp_like(n.jhs_instructor_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_instructor_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_master_teacher_iv, '^-[0-9]+$')
        OR regexp_like(n.jhs_master_teacher_iii, '^-[0-9]+$')
        OR regexp_like(n.jhs_master_teacher_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_master_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_teacher_iii, '^-[0-9]+$')
        OR regexp_like(n.jhs_teacher_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_special_science_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_sped_teacher_v, '^-[0-9]+$')
        OR regexp_like(n.jhs_sped_teacher_iv, '^-[0-9]+$')
        OR regexp_like(n.jhs_sped_teacher_iii, '^-[0-9]+$')
        OR regexp_like(n.jhs_sped_teacher_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_sped_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.shs_master_teacher_iv, '^-[0-9]+$')
        OR regexp_like(n.shs_master_teacher_iii, '^-[0-9]+$')
        OR regexp_like(n.shs_master_teacher_ii, '^-[0-9]+$')
        OR regexp_like(n.shs_master_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.shs_teacher_iii, '^-[0-9]+$')
        OR regexp_like(n.shs_teacher_ii, '^-[0-9]+$')
        OR regexp_like(n.shs_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.shs_special_science_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.es_school_principal_iv, '^-[0-9]+$')
        OR regexp_like(n.es_school_principal_iii, '^-[0-9]+$')
        OR regexp_like(n.es_school_principal_ii, '^-[0-9]+$')
        OR regexp_like(n.es_school_principal_i, '^-[0-9]+$')
        OR regexp_like(n.es_head_teacher_vi, '^-[0-9]+$')
        OR regexp_like(n.es_head_teacher_v, '^-[0-9]+$')
        OR regexp_like(n.es_head_teacher_iv, '^-[0-9]+$')
        OR regexp_like(n.es_head_teacher_iii, '^-[0-9]+$')
        OR regexp_like(n.es_head_teacher_ii, '^-[0-9]+$')
        OR regexp_like(n.es_head_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_coordinator_iii, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_coordinator_ii, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_coordinator_i, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_counselor_iii, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_counselor_ii, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_counselor_i, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_officer_ii, '^-[0-9]+$')
        OR regexp_like(n.es_project_development_officer_i, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_assistant_iii_senior_bookkeeper, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_assistant_ii_disbursing_officer_ii, '^-[0-9]+$')
        OR regexp_like(n.es_security_guard, '^-[0-9]+$')
        OR regexp_like(n.es_utility_worker_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_vocational_school_administrator_iii, '^-[0-9]+$')
        OR regexp_like(n.jhs_vocational_school_administrator_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_vocational_school_administrator_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_principal_iv, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_principal_iii, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_principal_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_principal_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_assistant_school_principal_iii, '^-[0-9]+$')
        OR regexp_like(n.jhs_assistant_school_principal_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_assistant_school_principal_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_head_teacher_vi, '^-[0-9]+$')
        OR regexp_like(n.jhs_head_teacher_v, '^-[0-9]+$')
        OR regexp_like(n.jhs_head_teacher_iv, '^-[0-9]+$')
        OR regexp_like(n.jhs_head_teacher_iii, '^-[0-9]+$')
        OR regexp_like(n.jhs_head_teacher_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_head_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_coordinator_iii, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_coordinator_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_coordinator_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_counselor_iii, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_counselor_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_counselor_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_officer_iv, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_officer_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_project_development_officer_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_librarian_iii, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_librarian_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_librarian_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_accountant_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_cashier_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_supply_officer_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_assistant_iii_senior_bookkeeper, '^-[0-9]+$')
        OR regexp_like(n.jhs_bookkeeper, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_ii, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_aide_vi, '^-[0-9]+$')
        OR regexp_like(n.jhs_heavy_equipment_operator_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_driver_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_security_guard_i, '^-[0-9]+$')
        OR regexp_like(n.jhs_light_equipment_operator, '^-[0-9]+$')
        OR regexp_like(n.jhs_utility_worker_i, '^-[0-9]+$')
        OR regexp_like(n.shs_school_principal_iv, '^-[0-9]+$')
        OR regexp_like(n.shs_school_principal_iii, '^-[0-9]+$')
        OR regexp_like(n.shs_school_principal_ii, '^-[0-9]+$')
        OR regexp_like(n.shs_school_principal_i, '^-[0-9]+$')
        OR regexp_like(n.shs_total_school_principal, '^-[0-9]+$')
        OR regexp_like(n.shs_assistant_principal_iii, '^-[0-9]+$')
        OR regexp_like(n.shs_assistant_principal_ii, '^-[0-9]+$')
        OR regexp_like(n.shs_assistant_principal_i, '^-[0-9]+$')
        OR regexp_like(n.shs_head_teacher_vi, '^-[0-9]+$')
        OR regexp_like(n.shs_head_teacher_v, '^-[0-9]+$')
        OR regexp_like(n.shs_head_teacher_iv, '^-[0-9]+$')
        OR regexp_like(n.shs_head_teacher_iii, '^-[0-9]+$')
        OR regexp_like(n.shs_head_teacher_ii, '^-[0-9]+$')
        OR regexp_like(n.shs_head_teacher_i, '^-[0-9]+$')
        OR regexp_like(n.shs_school_nurse_ii, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_officer_iv, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_officer_ii, '^-[0-9]+$')
        OR regexp_like(n.shs_school_librarian_iii, '^-[0-9]+$')
        OR regexp_like(n.shs_school_librarian_ii, '^-[0-9]+$')
        OR regexp_like(n.shs_school_librarian_i, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_service_specialist_ii, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_service_specialist_i, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_counselor_iii, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_counselor_ii, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_counselor_i, '^-[0-9]+$')
        OR regexp_like(n.shs_accounting_i, '^-[0-9]+$')
        OR regexp_like(n.shs_project_development_officer_i, '^-[0-9]+$')
        OR regexp_like(n.shs_registrar_i, '^-[0-9]+$')
        OR regexp_like(n.shs_cashier_i, '^-[0-9]+$')
        OR regexp_like(n.shs_supply_officer_i, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_assistant_iii_senior_bookkeeper, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_assistant_ii_disbursing_officer_ii, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_assistant_i, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_aide_vi, '^-[0-9]+$')
        OR regexp_like(n.shs_heavy_equipment_operator_i, '^-[0-9]+$')
        OR regexp_like(n.shs_security_guard_i, '^-[0-9]+$')
        OR regexp_like(n.shs_light_equipment_operator_i, '^-[0-9]+$')
        OR regexp_like(n.shs_utility_worker_i, '^-[0-9]+$')
        OR regexp_like(n.kinder_teachers_sef_province, '^-[0-9]+$')
        OR regexp_like(n.kinder_teachers_sef_municipality_city, '^-[0-9]+$')
        OR regexp_like(n.kinder_teachers_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.kinder_teachers_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_teachers_sef_province, '^-[0-9]+$')
        OR regexp_like(n.es_teachers_sef_municipality_city, '^-[0-9]+$')
        OR regexp_like(n.es_teachers_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_teachers_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_teachers_sef_province, '^-[0-9]+$')
        OR regexp_like(n.jhs_teachers_sef_municipality_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_teachers_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_teachers_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_teachers_sef_province, '^-[0-9]+$')
        OR regexp_like(n.shs_teachers_sef_municipality_city, '^-[0-9]+$')
        OR regexp_like(n.shs_teachers_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_teachers_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_learning_support_aide_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_learning_support_aide_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_learning_support_aide_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_learning_support_aide_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_officer_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_officer_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_officer_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_officer_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_assistant_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_assistant_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_assistant_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_assistant_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_aide_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_aide_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_aide_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_administrative_aide_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_project_development_officer_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_project_development_officer_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_project_development_officer_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_project_development_officer_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_school_doctor_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_school_doctor_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_school_doctor_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_school_doctor_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_school_dentist_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_school_dentist_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_school_dentist_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_school_dentist_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_school_nurse_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_school_nurse_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_school_nurse_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_school_nurse_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_librarian_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_librarian_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_librarian_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_librarian_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_library_assistant_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_library_assistant_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_library_assistant_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_library_assistant_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_counselor_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_counselor_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_counselor_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_counselor_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_advocate_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_advocate_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_advocate_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_advocate_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_assistant_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_assistant_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_assistant_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_guidance_assistant_other_funding, '^-[0-9]+$')
        OR regexp_like(n.es_computer_technician_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.es_computer_technician_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.es_computer_technician_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.es_computer_technician_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_learning_support_aide_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_learning_support_aide_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_learning_support_aide_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_learning_support_aide_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_officer_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_officer_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_officer_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_officer_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_assistant_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_assistant_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_assistant_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_assistant_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_aide_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_aide_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_aide_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_administrative_aide_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_project_development_officer_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_project_development_officer_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_project_development_officer_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_project_development_officer_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_doctor_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_doctor_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_doctor_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_doctor_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_dentist_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_dentist_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_dentist_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_dentist_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_nurse_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_nurse_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_nurse_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_school_nurse_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_librarian_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_librarian_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_librarian_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_librarian_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_library_assistant_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_library_assistant_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_library_assistant_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_library_assistant_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_counselor_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_counselor_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_counselor_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_counselor_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_advocate_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_advocate_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_advocate_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_advocate_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_assistant_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_assistant_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_assistant_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_guidance_assistant_other_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_computer_technician_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.jhs_computer_technician_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.jhs_computer_technician_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.jhs_computer_technician_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_learning_support_aide_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_learning_support_aide_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_learning_support_aide_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_learning_support_aide_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_officer_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_officer_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_officer_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_officer_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_assistant_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_assistant_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_assistant_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_assistant_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_aide_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_aide_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_aide_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_administrative_aide_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_project_development_officer_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_project_development_officer_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_project_development_officer_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_project_development_officer_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_school_doctor_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_school_doctor_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_school_doctor_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_school_doctor_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_school_dentist_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_school_dentist_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_school_dentist_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_school_dentist_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_school_nurse_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_school_nurse_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_school_nurse_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_school_nurse_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_librarian_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_librarian_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_librarian_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_librarian_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_library_assistant_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_library_assistant_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_library_assistant_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_library_assistant_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_counselor_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_counselor_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_counselor_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_counselor_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_advocate_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_advocate_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_advocate_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_advocate_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_assistant_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_assistant_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_assistant_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_guidance_assistant_other_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_computer_technician_sef_provincial, '^-[0-9]+$')
        OR regexp_like(n.shs_computer_technician_sef_municipal_city, '^-[0-9]+$')
        OR regexp_like(n.shs_computer_technician_lgu_funding, '^-[0-9]+$')
        OR regexp_like(n.shs_computer_technician_other_funding, '^-[0-9]+$') THEN 'measure_negative' END,
      CASE WHEN n.es_master_teacher_iv <> '' AND NOT regexp_like(n.es_master_teacher_iv, '^-?[0-9]+$')
        OR n.es_master_teacher_iii <> '' AND NOT regexp_like(n.es_master_teacher_iii, '^-?[0-9]+$')
        OR n.es_master_teacher_ii <> '' AND NOT regexp_like(n.es_master_teacher_ii, '^-?[0-9]+$')
        OR n.es_master_teacher_i <> '' AND NOT regexp_like(n.es_master_teacher_i, '^-?[0-9]+$')
        OR n.es_teacher_iii <> '' AND NOT regexp_like(n.es_teacher_iii, '^-?[0-9]+$')
        OR n.es_teacher_ii <> '' AND NOT regexp_like(n.es_teacher_ii, '^-?[0-9]+$')
        OR n.es_teacher_i <> '' AND NOT regexp_like(n.es_teacher_i, '^-?[0-9]+$')
        OR n.es_sped_sned_teacher_v <> '' AND NOT regexp_like(n.es_sped_sned_teacher_v, '^-?[0-9]+$')
        OR n.es_sped_sned_teacher_iv <> '' AND NOT regexp_like(n.es_sped_sned_teacher_iv, '^-?[0-9]+$')
        OR n.es_sped_sned_teacher_iii <> '' AND NOT regexp_like(n.es_sped_sned_teacher_iii, '^-?[0-9]+$')
        OR n.es_sped_sned_teacher_ii <> '' AND NOT regexp_like(n.es_sped_sned_teacher_ii, '^-?[0-9]+$')
        OR n.es_sped_sned_teacher_i <> '' AND NOT regexp_like(n.es_sped_sned_teacher_i, '^-?[0-9]+$')
        OR n.jhs_instructor_iii <> '' AND NOT regexp_like(n.jhs_instructor_iii, '^-?[0-9]+$')
        OR n.jhs_instructor_ii <> '' AND NOT regexp_like(n.jhs_instructor_ii, '^-?[0-9]+$')
        OR n.jhs_instructor_i <> '' AND NOT regexp_like(n.jhs_instructor_i, '^-?[0-9]+$')
        OR n.jhs_master_teacher_iv <> '' AND NOT regexp_like(n.jhs_master_teacher_iv, '^-?[0-9]+$')
        OR n.jhs_master_teacher_iii <> '' AND NOT regexp_like(n.jhs_master_teacher_iii, '^-?[0-9]+$')
        OR n.jhs_master_teacher_ii <> '' AND NOT regexp_like(n.jhs_master_teacher_ii, '^-?[0-9]+$')
        OR n.jhs_master_teacher_i <> '' AND NOT regexp_like(n.jhs_master_teacher_i, '^-?[0-9]+$')
        OR n.jhs_teacher_iii <> '' AND NOT regexp_like(n.jhs_teacher_iii, '^-?[0-9]+$')
        OR n.jhs_teacher_ii <> '' AND NOT regexp_like(n.jhs_teacher_ii, '^-?[0-9]+$')
        OR n.jhs_teacher_i <> '' AND NOT regexp_like(n.jhs_teacher_i, '^-?[0-9]+$')
        OR n.jhs_special_science_teacher_i <> '' AND NOT regexp_like(n.jhs_special_science_teacher_i, '^-?[0-9]+$')
        OR n.jhs_sped_teacher_v <> '' AND NOT regexp_like(n.jhs_sped_teacher_v, '^-?[0-9]+$')
        OR n.jhs_sped_teacher_iv <> '' AND NOT regexp_like(n.jhs_sped_teacher_iv, '^-?[0-9]+$')
        OR n.jhs_sped_teacher_iii <> '' AND NOT regexp_like(n.jhs_sped_teacher_iii, '^-?[0-9]+$')
        OR n.jhs_sped_teacher_ii <> '' AND NOT regexp_like(n.jhs_sped_teacher_ii, '^-?[0-9]+$')
        OR n.jhs_sped_teacher_i <> '' AND NOT regexp_like(n.jhs_sped_teacher_i, '^-?[0-9]+$')
        OR n.shs_master_teacher_iv <> '' AND NOT regexp_like(n.shs_master_teacher_iv, '^-?[0-9]+$')
        OR n.shs_master_teacher_iii <> '' AND NOT regexp_like(n.shs_master_teacher_iii, '^-?[0-9]+$')
        OR n.shs_master_teacher_ii <> '' AND NOT regexp_like(n.shs_master_teacher_ii, '^-?[0-9]+$')
        OR n.shs_master_teacher_i <> '' AND NOT regexp_like(n.shs_master_teacher_i, '^-?[0-9]+$')
        OR n.shs_teacher_iii <> '' AND NOT regexp_like(n.shs_teacher_iii, '^-?[0-9]+$')
        OR n.shs_teacher_ii <> '' AND NOT regexp_like(n.shs_teacher_ii, '^-?[0-9]+$')
        OR n.shs_teacher_i <> '' AND NOT regexp_like(n.shs_teacher_i, '^-?[0-9]+$')
        OR n.shs_special_science_teacher_i <> '' AND NOT regexp_like(n.shs_special_science_teacher_i, '^-?[0-9]+$')
        OR n.es_school_principal_iv <> '' AND NOT regexp_like(n.es_school_principal_iv, '^-?[0-9]+$')
        OR n.es_school_principal_iii <> '' AND NOT regexp_like(n.es_school_principal_iii, '^-?[0-9]+$')
        OR n.es_school_principal_ii <> '' AND NOT regexp_like(n.es_school_principal_ii, '^-?[0-9]+$')
        OR n.es_school_principal_i <> '' AND NOT regexp_like(n.es_school_principal_i, '^-?[0-9]+$')
        OR n.es_head_teacher_vi <> '' AND NOT regexp_like(n.es_head_teacher_vi, '^-?[0-9]+$')
        OR n.es_head_teacher_v <> '' AND NOT regexp_like(n.es_head_teacher_v, '^-?[0-9]+$')
        OR n.es_head_teacher_iv <> '' AND NOT regexp_like(n.es_head_teacher_iv, '^-?[0-9]+$')
        OR n.es_head_teacher_iii <> '' AND NOT regexp_like(n.es_head_teacher_iii, '^-?[0-9]+$')
        OR n.es_head_teacher_ii <> '' AND NOT regexp_like(n.es_head_teacher_ii, '^-?[0-9]+$')
        OR n.es_head_teacher_i <> '' AND NOT regexp_like(n.es_head_teacher_i, '^-?[0-9]+$')
        OR n.es_guidance_coordinator_iii <> '' AND NOT regexp_like(n.es_guidance_coordinator_iii, '^-?[0-9]+$')
        OR n.es_guidance_coordinator_ii <> '' AND NOT regexp_like(n.es_guidance_coordinator_ii, '^-?[0-9]+$')
        OR n.es_guidance_coordinator_i <> '' AND NOT regexp_like(n.es_guidance_coordinator_i, '^-?[0-9]+$')
        OR n.es_guidance_counselor_iii <> '' AND NOT regexp_like(n.es_guidance_counselor_iii, '^-?[0-9]+$')
        OR n.es_guidance_counselor_ii <> '' AND NOT regexp_like(n.es_guidance_counselor_ii, '^-?[0-9]+$')
        OR n.es_guidance_counselor_i <> '' AND NOT regexp_like(n.es_guidance_counselor_i, '^-?[0-9]+$')
        OR n.es_administrative_officer_ii <> '' AND NOT regexp_like(n.es_administrative_officer_ii, '^-?[0-9]+$')
        OR n.es_project_development_officer_i <> '' AND NOT regexp_like(n.es_project_development_officer_i, '^-?[0-9]+$')
        OR n.es_administrative_assistant_iii_senior_bookkeeper <> '' AND NOT regexp_like(n.es_administrative_assistant_iii_senior_bookkeeper, '^-?[0-9]+$')
        OR n.es_administrative_assistant_ii_disbursing_officer_ii <> '' AND NOT regexp_like(n.es_administrative_assistant_ii_disbursing_officer_ii, '^-?[0-9]+$')
        OR n.es_security_guard <> '' AND NOT regexp_like(n.es_security_guard, '^-?[0-9]+$')
        OR n.es_utility_worker_i <> '' AND NOT regexp_like(n.es_utility_worker_i, '^-?[0-9]+$')
        OR n.jhs_vocational_school_administrator_iii <> '' AND NOT regexp_like(n.jhs_vocational_school_administrator_iii, '^-?[0-9]+$')
        OR n.jhs_vocational_school_administrator_ii <> '' AND NOT regexp_like(n.jhs_vocational_school_administrator_ii, '^-?[0-9]+$')
        OR n.jhs_vocational_school_administrator_i <> '' AND NOT regexp_like(n.jhs_vocational_school_administrator_i, '^-?[0-9]+$')
        OR n.jhs_school_principal_iv <> '' AND NOT regexp_like(n.jhs_school_principal_iv, '^-?[0-9]+$')
        OR n.jhs_school_principal_iii <> '' AND NOT regexp_like(n.jhs_school_principal_iii, '^-?[0-9]+$')
        OR n.jhs_school_principal_ii <> '' AND NOT regexp_like(n.jhs_school_principal_ii, '^-?[0-9]+$')
        OR n.jhs_school_principal_i <> '' AND NOT regexp_like(n.jhs_school_principal_i, '^-?[0-9]+$')
        OR n.jhs_assistant_school_principal_iii <> '' AND NOT regexp_like(n.jhs_assistant_school_principal_iii, '^-?[0-9]+$')
        OR n.jhs_assistant_school_principal_ii <> '' AND NOT regexp_like(n.jhs_assistant_school_principal_ii, '^-?[0-9]+$')
        OR n.jhs_assistant_school_principal_i <> '' AND NOT regexp_like(n.jhs_assistant_school_principal_i, '^-?[0-9]+$')
        OR n.jhs_head_teacher_vi <> '' AND NOT regexp_like(n.jhs_head_teacher_vi, '^-?[0-9]+$')
        OR n.jhs_head_teacher_v <> '' AND NOT regexp_like(n.jhs_head_teacher_v, '^-?[0-9]+$')
        OR n.jhs_head_teacher_iv <> '' AND NOT regexp_like(n.jhs_head_teacher_iv, '^-?[0-9]+$')
        OR n.jhs_head_teacher_iii <> '' AND NOT regexp_like(n.jhs_head_teacher_iii, '^-?[0-9]+$')
        OR n.jhs_head_teacher_ii <> '' AND NOT regexp_like(n.jhs_head_teacher_ii, '^-?[0-9]+$')
        OR n.jhs_head_teacher_i <> '' AND NOT regexp_like(n.jhs_head_teacher_i, '^-?[0-9]+$')
        OR n.jhs_guidance_coordinator_iii <> '' AND NOT regexp_like(n.jhs_guidance_coordinator_iii, '^-?[0-9]+$')
        OR n.jhs_guidance_coordinator_ii <> '' AND NOT regexp_like(n.jhs_guidance_coordinator_ii, '^-?[0-9]+$')
        OR n.jhs_guidance_coordinator_i <> '' AND NOT regexp_like(n.jhs_guidance_coordinator_i, '^-?[0-9]+$')
        OR n.jhs_guidance_counselor_iii <> '' AND NOT regexp_like(n.jhs_guidance_counselor_iii, '^-?[0-9]+$')
        OR n.jhs_guidance_counselor_ii <> '' AND NOT regexp_like(n.jhs_guidance_counselor_ii, '^-?[0-9]+$')
        OR n.jhs_guidance_counselor_i <> '' AND NOT regexp_like(n.jhs_guidance_counselor_i, '^-?[0-9]+$')
        OR n.jhs_administrative_officer_iv <> '' AND NOT regexp_like(n.jhs_administrative_officer_iv, '^-?[0-9]+$')
        OR n.jhs_administrative_officer_ii <> '' AND NOT regexp_like(n.jhs_administrative_officer_ii, '^-?[0-9]+$')
        OR n.jhs_project_development_officer_i <> '' AND NOT regexp_like(n.jhs_project_development_officer_i, '^-?[0-9]+$')
        OR n.jhs_school_librarian_iii <> '' AND NOT regexp_like(n.jhs_school_librarian_iii, '^-?[0-9]+$')
        OR n.jhs_school_librarian_ii <> '' AND NOT regexp_like(n.jhs_school_librarian_ii, '^-?[0-9]+$')
        OR n.jhs_school_librarian_i <> '' AND NOT regexp_like(n.jhs_school_librarian_i, '^-?[0-9]+$')
        OR n.jhs_accountant_i <> '' AND NOT regexp_like(n.jhs_accountant_i, '^-?[0-9]+$')
        OR n.jhs_cashier_i <> '' AND NOT regexp_like(n.jhs_cashier_i, '^-?[0-9]+$')
        OR n.jhs_supply_officer_i <> '' AND NOT regexp_like(n.jhs_supply_officer_i, '^-?[0-9]+$')
        OR n.jhs_administrative_assistant_iii_senior_bookkeeper <> '' AND NOT regexp_like(n.jhs_administrative_assistant_iii_senior_bookkeeper, '^-?[0-9]+$')
        OR n.jhs_bookkeeper <> '' AND NOT regexp_like(n.jhs_bookkeeper, '^-?[0-9]+$')
        OR n.jhs_administrative_assistant_ii_disbursing_officer_ii <> '' AND NOT regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_ii, '^-?[0-9]+$')
        OR n.jhs_administrative_assistant_ii_disbursing_officer_i <> '' AND NOT regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_i, '^-?[0-9]+$')
        OR n.jhs_administrative_aide_vi <> '' AND NOT regexp_like(n.jhs_administrative_aide_vi, '^-?[0-9]+$')
        OR n.jhs_heavy_equipment_operator_i <> '' AND NOT regexp_like(n.jhs_heavy_equipment_operator_i, '^-?[0-9]+$')
        OR n.jhs_driver_i <> '' AND NOT regexp_like(n.jhs_driver_i, '^-?[0-9]+$')
        OR n.jhs_security_guard_i <> '' AND NOT regexp_like(n.jhs_security_guard_i, '^-?[0-9]+$')
        OR n.jhs_light_equipment_operator <> '' AND NOT regexp_like(n.jhs_light_equipment_operator, '^-?[0-9]+$')
        OR n.jhs_utility_worker_i <> '' AND NOT regexp_like(n.jhs_utility_worker_i, '^-?[0-9]+$')
        OR n.shs_school_principal_iv <> '' AND NOT regexp_like(n.shs_school_principal_iv, '^-?[0-9]+$')
        OR n.shs_school_principal_iii <> '' AND NOT regexp_like(n.shs_school_principal_iii, '^-?[0-9]+$')
        OR n.shs_school_principal_ii <> '' AND NOT regexp_like(n.shs_school_principal_ii, '^-?[0-9]+$')
        OR n.shs_school_principal_i <> '' AND NOT regexp_like(n.shs_school_principal_i, '^-?[0-9]+$')
        OR n.shs_total_school_principal <> '' AND NOT regexp_like(n.shs_total_school_principal, '^-?[0-9]+$')
        OR n.shs_assistant_principal_iii <> '' AND NOT regexp_like(n.shs_assistant_principal_iii, '^-?[0-9]+$')
        OR n.shs_assistant_principal_ii <> '' AND NOT regexp_like(n.shs_assistant_principal_ii, '^-?[0-9]+$')
        OR n.shs_assistant_principal_i <> '' AND NOT regexp_like(n.shs_assistant_principal_i, '^-?[0-9]+$')
        OR n.shs_head_teacher_vi <> '' AND NOT regexp_like(n.shs_head_teacher_vi, '^-?[0-9]+$')
        OR n.shs_head_teacher_v <> '' AND NOT regexp_like(n.shs_head_teacher_v, '^-?[0-9]+$')
        OR n.shs_head_teacher_iv <> '' AND NOT regexp_like(n.shs_head_teacher_iv, '^-?[0-9]+$')
        OR n.shs_head_teacher_iii <> '' AND NOT regexp_like(n.shs_head_teacher_iii, '^-?[0-9]+$')
        OR n.shs_head_teacher_ii <> '' AND NOT regexp_like(n.shs_head_teacher_ii, '^-?[0-9]+$')
        OR n.shs_head_teacher_i <> '' AND NOT regexp_like(n.shs_head_teacher_i, '^-?[0-9]+$')
        OR n.shs_school_nurse_ii <> '' AND NOT regexp_like(n.shs_school_nurse_ii, '^-?[0-9]+$')
        OR n.shs_administrative_officer_iv <> '' AND NOT regexp_like(n.shs_administrative_officer_iv, '^-?[0-9]+$')
        OR n.shs_administrative_officer_ii <> '' AND NOT regexp_like(n.shs_administrative_officer_ii, '^-?[0-9]+$')
        OR n.shs_school_librarian_iii <> '' AND NOT regexp_like(n.shs_school_librarian_iii, '^-?[0-9]+$')
        OR n.shs_school_librarian_ii <> '' AND NOT regexp_like(n.shs_school_librarian_ii, '^-?[0-9]+$')
        OR n.shs_school_librarian_i <> '' AND NOT regexp_like(n.shs_school_librarian_i, '^-?[0-9]+$')
        OR n.shs_guidance_service_specialist_ii <> '' AND NOT regexp_like(n.shs_guidance_service_specialist_ii, '^-?[0-9]+$')
        OR n.shs_guidance_service_specialist_i <> '' AND NOT regexp_like(n.shs_guidance_service_specialist_i, '^-?[0-9]+$')
        OR n.shs_guidance_counselor_iii <> '' AND NOT regexp_like(n.shs_guidance_counselor_iii, '^-?[0-9]+$')
        OR n.shs_guidance_counselor_ii <> '' AND NOT regexp_like(n.shs_guidance_counselor_ii, '^-?[0-9]+$')
        OR n.shs_guidance_counselor_i <> '' AND NOT regexp_like(n.shs_guidance_counselor_i, '^-?[0-9]+$')
        OR n.shs_accounting_i <> '' AND NOT regexp_like(n.shs_accounting_i, '^-?[0-9]+$')
        OR n.shs_project_development_officer_i <> '' AND NOT regexp_like(n.shs_project_development_officer_i, '^-?[0-9]+$')
        OR n.shs_registrar_i <> '' AND NOT regexp_like(n.shs_registrar_i, '^-?[0-9]+$')
        OR n.shs_cashier_i <> '' AND NOT regexp_like(n.shs_cashier_i, '^-?[0-9]+$')
        OR n.shs_supply_officer_i <> '' AND NOT regexp_like(n.shs_supply_officer_i, '^-?[0-9]+$')
        OR n.shs_administrative_assistant_iii_senior_bookkeeper <> '' AND NOT regexp_like(n.shs_administrative_assistant_iii_senior_bookkeeper, '^-?[0-9]+$')
        OR n.shs_administrative_assistant_ii_disbursing_officer_ii <> '' AND NOT regexp_like(n.shs_administrative_assistant_ii_disbursing_officer_ii, '^-?[0-9]+$')
        OR n.shs_administrative_assistant_i <> '' AND NOT regexp_like(n.shs_administrative_assistant_i, '^-?[0-9]+$')
        OR n.shs_administrative_aide_vi <> '' AND NOT regexp_like(n.shs_administrative_aide_vi, '^-?[0-9]+$')
        OR n.shs_heavy_equipment_operator_i <> '' AND NOT regexp_like(n.shs_heavy_equipment_operator_i, '^-?[0-9]+$')
        OR n.shs_security_guard_i <> '' AND NOT regexp_like(n.shs_security_guard_i, '^-?[0-9]+$')
        OR n.shs_light_equipment_operator_i <> '' AND NOT regexp_like(n.shs_light_equipment_operator_i, '^-?[0-9]+$')
        OR n.shs_utility_worker_i <> '' AND NOT regexp_like(n.shs_utility_worker_i, '^-?[0-9]+$')
        OR n.kinder_teachers_sef_province <> '' AND NOT regexp_like(n.kinder_teachers_sef_province, '^-?[0-9]+$')
        OR n.kinder_teachers_sef_municipality_city <> '' AND NOT regexp_like(n.kinder_teachers_sef_municipality_city, '^-?[0-9]+$')
        OR n.kinder_teachers_lgu_funding <> '' AND NOT regexp_like(n.kinder_teachers_lgu_funding, '^-?[0-9]+$')
        OR n.kinder_teachers_other_funding <> '' AND NOT regexp_like(n.kinder_teachers_other_funding, '^-?[0-9]+$')
        OR n.es_teachers_sef_province <> '' AND NOT regexp_like(n.es_teachers_sef_province, '^-?[0-9]+$')
        OR n.es_teachers_sef_municipality_city <> '' AND NOT regexp_like(n.es_teachers_sef_municipality_city, '^-?[0-9]+$')
        OR n.es_teachers_lgu_funding <> '' AND NOT regexp_like(n.es_teachers_lgu_funding, '^-?[0-9]+$')
        OR n.es_teachers_other_funding <> '' AND NOT regexp_like(n.es_teachers_other_funding, '^-?[0-9]+$')
        OR n.jhs_teachers_sef_province <> '' AND NOT regexp_like(n.jhs_teachers_sef_province, '^-?[0-9]+$')
        OR n.jhs_teachers_sef_municipality_city <> '' AND NOT regexp_like(n.jhs_teachers_sef_municipality_city, '^-?[0-9]+$')
        OR n.jhs_teachers_lgu_funding <> '' AND NOT regexp_like(n.jhs_teachers_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_teachers_other_funding <> '' AND NOT regexp_like(n.jhs_teachers_other_funding, '^-?[0-9]+$')
        OR n.shs_teachers_sef_province <> '' AND NOT regexp_like(n.shs_teachers_sef_province, '^-?[0-9]+$')
        OR n.shs_teachers_sef_municipality_city <> '' AND NOT regexp_like(n.shs_teachers_sef_municipality_city, '^-?[0-9]+$')
        OR n.shs_teachers_lgu_funding <> '' AND NOT regexp_like(n.shs_teachers_lgu_funding, '^-?[0-9]+$')
        OR n.shs_teachers_other_funding <> '' AND NOT regexp_like(n.shs_teachers_other_funding, '^-?[0-9]+$')
        OR n.es_learning_support_aide_sef_provincial <> '' AND NOT regexp_like(n.es_learning_support_aide_sef_provincial, '^-?[0-9]+$')
        OR n.es_learning_support_aide_sef_municipal_city <> '' AND NOT regexp_like(n.es_learning_support_aide_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_learning_support_aide_lgu_funding <> '' AND NOT regexp_like(n.es_learning_support_aide_lgu_funding, '^-?[0-9]+$')
        OR n.es_learning_support_aide_other_funding <> '' AND NOT regexp_like(n.es_learning_support_aide_other_funding, '^-?[0-9]+$')
        OR n.es_administrative_officer_sef_provincial <> '' AND NOT regexp_like(n.es_administrative_officer_sef_provincial, '^-?[0-9]+$')
        OR n.es_administrative_officer_sef_municipal_city <> '' AND NOT regexp_like(n.es_administrative_officer_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_administrative_officer_lgu_funding <> '' AND NOT regexp_like(n.es_administrative_officer_lgu_funding, '^-?[0-9]+$')
        OR n.es_administrative_officer_other_funding <> '' AND NOT regexp_like(n.es_administrative_officer_other_funding, '^-?[0-9]+$')
        OR n.es_administrative_assistant_sef_provincial <> '' AND NOT regexp_like(n.es_administrative_assistant_sef_provincial, '^-?[0-9]+$')
        OR n.es_administrative_assistant_sef_municipal_city <> '' AND NOT regexp_like(n.es_administrative_assistant_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_administrative_assistant_lgu_funding <> '' AND NOT regexp_like(n.es_administrative_assistant_lgu_funding, '^-?[0-9]+$')
        OR n.es_administrative_assistant_other_funding <> '' AND NOT regexp_like(n.es_administrative_assistant_other_funding, '^-?[0-9]+$')
        OR n.es_administrative_aide_sef_provincial <> '' AND NOT regexp_like(n.es_administrative_aide_sef_provincial, '^-?[0-9]+$')
        OR n.es_administrative_aide_sef_municipal_city <> '' AND NOT regexp_like(n.es_administrative_aide_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_administrative_aide_lgu_funding <> '' AND NOT regexp_like(n.es_administrative_aide_lgu_funding, '^-?[0-9]+$')
        OR n.es_administrative_aide_other_funding <> '' AND NOT regexp_like(n.es_administrative_aide_other_funding, '^-?[0-9]+$')
        OR n.es_project_development_officer_sef_provincial <> '' AND NOT regexp_like(n.es_project_development_officer_sef_provincial, '^-?[0-9]+$')
        OR n.es_project_development_officer_sef_municipal_city <> '' AND NOT regexp_like(n.es_project_development_officer_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_project_development_officer_lgu_funding <> '' AND NOT regexp_like(n.es_project_development_officer_lgu_funding, '^-?[0-9]+$')
        OR n.es_project_development_officer_other_funding <> '' AND NOT regexp_like(n.es_project_development_officer_other_funding, '^-?[0-9]+$')
        OR n.es_school_doctor_sef_provincial <> '' AND NOT regexp_like(n.es_school_doctor_sef_provincial, '^-?[0-9]+$')
        OR n.es_school_doctor_sef_municipal_city <> '' AND NOT regexp_like(n.es_school_doctor_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_school_doctor_lgu_funding <> '' AND NOT regexp_like(n.es_school_doctor_lgu_funding, '^-?[0-9]+$')
        OR n.es_school_doctor_other_funding <> '' AND NOT regexp_like(n.es_school_doctor_other_funding, '^-?[0-9]+$')
        OR n.es_school_dentist_sef_provincial <> '' AND NOT regexp_like(n.es_school_dentist_sef_provincial, '^-?[0-9]+$')
        OR n.es_school_dentist_sef_municipal_city <> '' AND NOT regexp_like(n.es_school_dentist_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_school_dentist_lgu_funding <> '' AND NOT regexp_like(n.es_school_dentist_lgu_funding, '^-?[0-9]+$')
        OR n.es_school_dentist_other_funding <> '' AND NOT regexp_like(n.es_school_dentist_other_funding, '^-?[0-9]+$')
        OR n.es_school_nurse_sef_provincial <> '' AND NOT regexp_like(n.es_school_nurse_sef_provincial, '^-?[0-9]+$')
        OR n.es_school_nurse_sef_municipal_city <> '' AND NOT regexp_like(n.es_school_nurse_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_school_nurse_lgu_funding <> '' AND NOT regexp_like(n.es_school_nurse_lgu_funding, '^-?[0-9]+$')
        OR n.es_school_nurse_other_funding <> '' AND NOT regexp_like(n.es_school_nurse_other_funding, '^-?[0-9]+$')
        OR n.es_librarian_sef_provincial <> '' AND NOT regexp_like(n.es_librarian_sef_provincial, '^-?[0-9]+$')
        OR n.es_librarian_sef_municipal_city <> '' AND NOT regexp_like(n.es_librarian_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_librarian_lgu_funding <> '' AND NOT regexp_like(n.es_librarian_lgu_funding, '^-?[0-9]+$')
        OR n.es_librarian_other_funding <> '' AND NOT regexp_like(n.es_librarian_other_funding, '^-?[0-9]+$')
        OR n.es_library_assistant_sef_provincial <> '' AND NOT regexp_like(n.es_library_assistant_sef_provincial, '^-?[0-9]+$')
        OR n.es_library_assistant_sef_municipal_city <> '' AND NOT regexp_like(n.es_library_assistant_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_library_assistant_lgu_funding <> '' AND NOT regexp_like(n.es_library_assistant_lgu_funding, '^-?[0-9]+$')
        OR n.es_library_assistant_other_funding <> '' AND NOT regexp_like(n.es_library_assistant_other_funding, '^-?[0-9]+$')
        OR n.es_guidance_counselor_sef_provincial <> '' AND NOT regexp_like(n.es_guidance_counselor_sef_provincial, '^-?[0-9]+$')
        OR n.es_guidance_counselor_sef_municipal_city <> '' AND NOT regexp_like(n.es_guidance_counselor_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_guidance_counselor_lgu_funding <> '' AND NOT regexp_like(n.es_guidance_counselor_lgu_funding, '^-?[0-9]+$')
        OR n.es_guidance_counselor_other_funding <> '' AND NOT regexp_like(n.es_guidance_counselor_other_funding, '^-?[0-9]+$')
        OR n.es_guidance_advocate_sef_provincial <> '' AND NOT regexp_like(n.es_guidance_advocate_sef_provincial, '^-?[0-9]+$')
        OR n.es_guidance_advocate_sef_municipal_city <> '' AND NOT regexp_like(n.es_guidance_advocate_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_guidance_advocate_lgu_funding <> '' AND NOT regexp_like(n.es_guidance_advocate_lgu_funding, '^-?[0-9]+$')
        OR n.es_guidance_advocate_other_funding <> '' AND NOT regexp_like(n.es_guidance_advocate_other_funding, '^-?[0-9]+$')
        OR n.es_guidance_assistant_sef_provincial <> '' AND NOT regexp_like(n.es_guidance_assistant_sef_provincial, '^-?[0-9]+$')
        OR n.es_guidance_assistant_sef_municipal_city <> '' AND NOT regexp_like(n.es_guidance_assistant_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_guidance_assistant_lgu_funding <> '' AND NOT regexp_like(n.es_guidance_assistant_lgu_funding, '^-?[0-9]+$')
        OR n.es_guidance_assistant_other_funding <> '' AND NOT regexp_like(n.es_guidance_assistant_other_funding, '^-?[0-9]+$')
        OR n.es_computer_technician_sef_provincial <> '' AND NOT regexp_like(n.es_computer_technician_sef_provincial, '^-?[0-9]+$')
        OR n.es_computer_technician_sef_municipal_city <> '' AND NOT regexp_like(n.es_computer_technician_sef_municipal_city, '^-?[0-9]+$')
        OR n.es_computer_technician_lgu_funding <> '' AND NOT regexp_like(n.es_computer_technician_lgu_funding, '^-?[0-9]+$')
        OR n.es_computer_technician_other_funding <> '' AND NOT regexp_like(n.es_computer_technician_other_funding, '^-?[0-9]+$')
        OR n.jhs_learning_support_aide_sef_provincial <> '' AND NOT regexp_like(n.jhs_learning_support_aide_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_learning_support_aide_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_learning_support_aide_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_learning_support_aide_lgu_funding <> '' AND NOT regexp_like(n.jhs_learning_support_aide_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_learning_support_aide_other_funding <> '' AND NOT regexp_like(n.jhs_learning_support_aide_other_funding, '^-?[0-9]+$')
        OR n.jhs_administrative_officer_sef_provincial <> '' AND NOT regexp_like(n.jhs_administrative_officer_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_administrative_officer_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_administrative_officer_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_administrative_officer_lgu_funding <> '' AND NOT regexp_like(n.jhs_administrative_officer_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_administrative_officer_other_funding <> '' AND NOT regexp_like(n.jhs_administrative_officer_other_funding, '^-?[0-9]+$')
        OR n.jhs_administrative_assistant_sef_provincial <> '' AND NOT regexp_like(n.jhs_administrative_assistant_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_administrative_assistant_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_administrative_assistant_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_administrative_assistant_lgu_funding <> '' AND NOT regexp_like(n.jhs_administrative_assistant_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_administrative_assistant_other_funding <> '' AND NOT regexp_like(n.jhs_administrative_assistant_other_funding, '^-?[0-9]+$')
        OR n.jhs_administrative_aide_sef_provincial <> '' AND NOT regexp_like(n.jhs_administrative_aide_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_administrative_aide_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_administrative_aide_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_administrative_aide_lgu_funding <> '' AND NOT regexp_like(n.jhs_administrative_aide_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_administrative_aide_other_funding <> '' AND NOT regexp_like(n.jhs_administrative_aide_other_funding, '^-?[0-9]+$')
        OR n.jhs_project_development_officer_sef_provincial <> '' AND NOT regexp_like(n.jhs_project_development_officer_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_project_development_officer_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_project_development_officer_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_project_development_officer_lgu_funding <> '' AND NOT regexp_like(n.jhs_project_development_officer_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_project_development_officer_other_funding <> '' AND NOT regexp_like(n.jhs_project_development_officer_other_funding, '^-?[0-9]+$')
        OR n.jhs_school_doctor_sef_provincial <> '' AND NOT regexp_like(n.jhs_school_doctor_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_school_doctor_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_school_doctor_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_school_doctor_lgu_funding <> '' AND NOT regexp_like(n.jhs_school_doctor_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_school_doctor_other_funding <> '' AND NOT regexp_like(n.jhs_school_doctor_other_funding, '^-?[0-9]+$')
        OR n.jhs_school_dentist_sef_provincial <> '' AND NOT regexp_like(n.jhs_school_dentist_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_school_dentist_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_school_dentist_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_school_dentist_lgu_funding <> '' AND NOT regexp_like(n.jhs_school_dentist_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_school_dentist_other_funding <> '' AND NOT regexp_like(n.jhs_school_dentist_other_funding, '^-?[0-9]+$')
        OR n.jhs_school_nurse_sef_provincial <> '' AND NOT regexp_like(n.jhs_school_nurse_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_school_nurse_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_school_nurse_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_school_nurse_lgu_funding <> '' AND NOT regexp_like(n.jhs_school_nurse_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_school_nurse_other_funding <> '' AND NOT regexp_like(n.jhs_school_nurse_other_funding, '^-?[0-9]+$')
        OR n.jhs_librarian_sef_provincial <> '' AND NOT regexp_like(n.jhs_librarian_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_librarian_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_librarian_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_librarian_lgu_funding <> '' AND NOT regexp_like(n.jhs_librarian_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_librarian_other_funding <> '' AND NOT regexp_like(n.jhs_librarian_other_funding, '^-?[0-9]+$')
        OR n.jhs_library_assistant_sef_provincial <> '' AND NOT regexp_like(n.jhs_library_assistant_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_library_assistant_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_library_assistant_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_library_assistant_lgu_funding <> '' AND NOT regexp_like(n.jhs_library_assistant_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_library_assistant_other_funding <> '' AND NOT regexp_like(n.jhs_library_assistant_other_funding, '^-?[0-9]+$')
        OR n.jhs_guidance_counselor_sef_provincial <> '' AND NOT regexp_like(n.jhs_guidance_counselor_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_guidance_counselor_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_guidance_counselor_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_guidance_counselor_lgu_funding <> '' AND NOT regexp_like(n.jhs_guidance_counselor_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_guidance_counselor_other_funding <> '' AND NOT regexp_like(n.jhs_guidance_counselor_other_funding, '^-?[0-9]+$')
        OR n.jhs_guidance_advocate_sef_provincial <> '' AND NOT regexp_like(n.jhs_guidance_advocate_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_guidance_advocate_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_guidance_advocate_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_guidance_advocate_lgu_funding <> '' AND NOT regexp_like(n.jhs_guidance_advocate_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_guidance_advocate_other_funding <> '' AND NOT regexp_like(n.jhs_guidance_advocate_other_funding, '^-?[0-9]+$')
        OR n.jhs_guidance_assistant_sef_provincial <> '' AND NOT regexp_like(n.jhs_guidance_assistant_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_guidance_assistant_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_guidance_assistant_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_guidance_assistant_lgu_funding <> '' AND NOT regexp_like(n.jhs_guidance_assistant_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_guidance_assistant_other_funding <> '' AND NOT regexp_like(n.jhs_guidance_assistant_other_funding, '^-?[0-9]+$')
        OR n.jhs_computer_technician_sef_provincial <> '' AND NOT regexp_like(n.jhs_computer_technician_sef_provincial, '^-?[0-9]+$')
        OR n.jhs_computer_technician_sef_municipal_city <> '' AND NOT regexp_like(n.jhs_computer_technician_sef_municipal_city, '^-?[0-9]+$')
        OR n.jhs_computer_technician_lgu_funding <> '' AND NOT regexp_like(n.jhs_computer_technician_lgu_funding, '^-?[0-9]+$')
        OR n.jhs_computer_technician_other_funding <> '' AND NOT regexp_like(n.jhs_computer_technician_other_funding, '^-?[0-9]+$')
        OR n.shs_learning_support_aide_sef_provincial <> '' AND NOT regexp_like(n.shs_learning_support_aide_sef_provincial, '^-?[0-9]+$')
        OR n.shs_learning_support_aide_sef_municipal_city <> '' AND NOT regexp_like(n.shs_learning_support_aide_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_learning_support_aide_lgu_funding <> '' AND NOT regexp_like(n.shs_learning_support_aide_lgu_funding, '^-?[0-9]+$')
        OR n.shs_learning_support_aide_other_funding <> '' AND NOT regexp_like(n.shs_learning_support_aide_other_funding, '^-?[0-9]+$')
        OR n.shs_administrative_officer_sef_provincial <> '' AND NOT regexp_like(n.shs_administrative_officer_sef_provincial, '^-?[0-9]+$')
        OR n.shs_administrative_officer_sef_municipal_city <> '' AND NOT regexp_like(n.shs_administrative_officer_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_administrative_officer_lgu_funding <> '' AND NOT regexp_like(n.shs_administrative_officer_lgu_funding, '^-?[0-9]+$')
        OR n.shs_administrative_officer_other_funding <> '' AND NOT regexp_like(n.shs_administrative_officer_other_funding, '^-?[0-9]+$')
        OR n.shs_administrative_assistant_sef_provincial <> '' AND NOT regexp_like(n.shs_administrative_assistant_sef_provincial, '^-?[0-9]+$')
        OR n.shs_administrative_assistant_sef_municipal_city <> '' AND NOT regexp_like(n.shs_administrative_assistant_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_administrative_assistant_lgu_funding <> '' AND NOT regexp_like(n.shs_administrative_assistant_lgu_funding, '^-?[0-9]+$')
        OR n.shs_administrative_assistant_other_funding <> '' AND NOT regexp_like(n.shs_administrative_assistant_other_funding, '^-?[0-9]+$')
        OR n.shs_administrative_aide_sef_provincial <> '' AND NOT regexp_like(n.shs_administrative_aide_sef_provincial, '^-?[0-9]+$')
        OR n.shs_administrative_aide_sef_municipal_city <> '' AND NOT regexp_like(n.shs_administrative_aide_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_administrative_aide_lgu_funding <> '' AND NOT regexp_like(n.shs_administrative_aide_lgu_funding, '^-?[0-9]+$')
        OR n.shs_administrative_aide_other_funding <> '' AND NOT regexp_like(n.shs_administrative_aide_other_funding, '^-?[0-9]+$')
        OR n.shs_project_development_officer_sef_provincial <> '' AND NOT regexp_like(n.shs_project_development_officer_sef_provincial, '^-?[0-9]+$')
        OR n.shs_project_development_officer_sef_municipal_city <> '' AND NOT regexp_like(n.shs_project_development_officer_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_project_development_officer_lgu_funding <> '' AND NOT regexp_like(n.shs_project_development_officer_lgu_funding, '^-?[0-9]+$')
        OR n.shs_project_development_officer_other_funding <> '' AND NOT regexp_like(n.shs_project_development_officer_other_funding, '^-?[0-9]+$')
        OR n.shs_school_doctor_sef_provincial <> '' AND NOT regexp_like(n.shs_school_doctor_sef_provincial, '^-?[0-9]+$')
        OR n.shs_school_doctor_sef_municipal_city <> '' AND NOT regexp_like(n.shs_school_doctor_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_school_doctor_lgu_funding <> '' AND NOT regexp_like(n.shs_school_doctor_lgu_funding, '^-?[0-9]+$')
        OR n.shs_school_doctor_other_funding <> '' AND NOT regexp_like(n.shs_school_doctor_other_funding, '^-?[0-9]+$')
        OR n.shs_school_dentist_sef_provincial <> '' AND NOT regexp_like(n.shs_school_dentist_sef_provincial, '^-?[0-9]+$')
        OR n.shs_school_dentist_sef_municipal_city <> '' AND NOT regexp_like(n.shs_school_dentist_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_school_dentist_lgu_funding <> '' AND NOT regexp_like(n.shs_school_dentist_lgu_funding, '^-?[0-9]+$')
        OR n.shs_school_dentist_other_funding <> '' AND NOT regexp_like(n.shs_school_dentist_other_funding, '^-?[0-9]+$')
        OR n.shs_school_nurse_sef_provincial <> '' AND NOT regexp_like(n.shs_school_nurse_sef_provincial, '^-?[0-9]+$')
        OR n.shs_school_nurse_sef_municipal_city <> '' AND NOT regexp_like(n.shs_school_nurse_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_school_nurse_lgu_funding <> '' AND NOT regexp_like(n.shs_school_nurse_lgu_funding, '^-?[0-9]+$')
        OR n.shs_school_nurse_other_funding <> '' AND NOT regexp_like(n.shs_school_nurse_other_funding, '^-?[0-9]+$')
        OR n.shs_librarian_sef_provincial <> '' AND NOT regexp_like(n.shs_librarian_sef_provincial, '^-?[0-9]+$')
        OR n.shs_librarian_sef_municipal_city <> '' AND NOT regexp_like(n.shs_librarian_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_librarian_lgu_funding <> '' AND NOT regexp_like(n.shs_librarian_lgu_funding, '^-?[0-9]+$')
        OR n.shs_librarian_other_funding <> '' AND NOT regexp_like(n.shs_librarian_other_funding, '^-?[0-9]+$')
        OR n.shs_library_assistant_sef_provincial <> '' AND NOT regexp_like(n.shs_library_assistant_sef_provincial, '^-?[0-9]+$')
        OR n.shs_library_assistant_sef_municipal_city <> '' AND NOT regexp_like(n.shs_library_assistant_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_library_assistant_lgu_funding <> '' AND NOT regexp_like(n.shs_library_assistant_lgu_funding, '^-?[0-9]+$')
        OR n.shs_library_assistant_other_funding <> '' AND NOT regexp_like(n.shs_library_assistant_other_funding, '^-?[0-9]+$')
        OR n.shs_guidance_counselor_sef_provincial <> '' AND NOT regexp_like(n.shs_guidance_counselor_sef_provincial, '^-?[0-9]+$')
        OR n.shs_guidance_counselor_sef_municipal_city <> '' AND NOT regexp_like(n.shs_guidance_counselor_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_guidance_counselor_lgu_funding <> '' AND NOT regexp_like(n.shs_guidance_counselor_lgu_funding, '^-?[0-9]+$')
        OR n.shs_guidance_counselor_other_funding <> '' AND NOT regexp_like(n.shs_guidance_counselor_other_funding, '^-?[0-9]+$')
        OR n.shs_guidance_advocate_sef_provincial <> '' AND NOT regexp_like(n.shs_guidance_advocate_sef_provincial, '^-?[0-9]+$')
        OR n.shs_guidance_advocate_sef_municipal_city <> '' AND NOT regexp_like(n.shs_guidance_advocate_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_guidance_advocate_lgu_funding <> '' AND NOT regexp_like(n.shs_guidance_advocate_lgu_funding, '^-?[0-9]+$')
        OR n.shs_guidance_advocate_other_funding <> '' AND NOT regexp_like(n.shs_guidance_advocate_other_funding, '^-?[0-9]+$')
        OR n.shs_guidance_assistant_sef_provincial <> '' AND NOT regexp_like(n.shs_guidance_assistant_sef_provincial, '^-?[0-9]+$')
        OR n.shs_guidance_assistant_sef_municipal_city <> '' AND NOT regexp_like(n.shs_guidance_assistant_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_guidance_assistant_lgu_funding <> '' AND NOT regexp_like(n.shs_guidance_assistant_lgu_funding, '^-?[0-9]+$')
        OR n.shs_guidance_assistant_other_funding <> '' AND NOT regexp_like(n.shs_guidance_assistant_other_funding, '^-?[0-9]+$')
        OR n.shs_computer_technician_sef_provincial <> '' AND NOT regexp_like(n.shs_computer_technician_sef_provincial, '^-?[0-9]+$')
        OR n.shs_computer_technician_sef_municipal_city <> '' AND NOT regexp_like(n.shs_computer_technician_sef_municipal_city, '^-?[0-9]+$')
        OR n.shs_computer_technician_lgu_funding <> '' AND NOT regexp_like(n.shs_computer_technician_lgu_funding, '^-?[0-9]+$')
        OR n.shs_computer_technician_other_funding <> '' AND NOT regexp_like(n.shs_computer_technician_other_funding, '^-?[0-9]+$') THEN 'measure_uncastable' END,
      CASE WHEN regexp_like(n.es_master_teacher_iv, '^[0-9]+$') AND (TRY_CAST(n.es_master_teacher_iv AS BIGINT) IS NULL OR TRY_CAST(n.es_master_teacher_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.es_master_teacher_iii, '^[0-9]+$') AND (TRY_CAST(n.es_master_teacher_iii AS BIGINT) IS NULL OR TRY_CAST(n.es_master_teacher_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_master_teacher_ii, '^[0-9]+$') AND (TRY_CAST(n.es_master_teacher_ii AS BIGINT) IS NULL OR TRY_CAST(n.es_master_teacher_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_master_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.es_master_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.es_master_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.es_teacher_iii, '^[0-9]+$') AND (TRY_CAST(n.es_teacher_iii AS BIGINT) IS NULL OR TRY_CAST(n.es_teacher_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_teacher_ii, '^[0-9]+$') AND (TRY_CAST(n.es_teacher_ii AS BIGINT) IS NULL OR TRY_CAST(n.es_teacher_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.es_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.es_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.es_sped_sned_teacher_v, '^[0-9]+$') AND (TRY_CAST(n.es_sped_sned_teacher_v AS BIGINT) IS NULL OR TRY_CAST(n.es_sped_sned_teacher_v AS BIGINT) > 2147483647)
        OR regexp_like(n.es_sped_sned_teacher_iv, '^[0-9]+$') AND (TRY_CAST(n.es_sped_sned_teacher_iv AS BIGINT) IS NULL OR TRY_CAST(n.es_sped_sned_teacher_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.es_sped_sned_teacher_iii, '^[0-9]+$') AND (TRY_CAST(n.es_sped_sned_teacher_iii AS BIGINT) IS NULL OR TRY_CAST(n.es_sped_sned_teacher_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_sped_sned_teacher_ii, '^[0-9]+$') AND (TRY_CAST(n.es_sped_sned_teacher_ii AS BIGINT) IS NULL OR TRY_CAST(n.es_sped_sned_teacher_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_sped_sned_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.es_sped_sned_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.es_sped_sned_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_instructor_iii, '^[0-9]+$') AND (TRY_CAST(n.jhs_instructor_iii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_instructor_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_instructor_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_instructor_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_instructor_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_instructor_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_instructor_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_instructor_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_master_teacher_iv, '^[0-9]+$') AND (TRY_CAST(n.jhs_master_teacher_iv AS BIGINT) IS NULL OR TRY_CAST(n.jhs_master_teacher_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_master_teacher_iii, '^[0-9]+$') AND (TRY_CAST(n.jhs_master_teacher_iii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_master_teacher_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_master_teacher_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_master_teacher_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_master_teacher_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_master_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_master_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_master_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_teacher_iii, '^[0-9]+$') AND (TRY_CAST(n.jhs_teacher_iii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_teacher_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_teacher_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_teacher_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_teacher_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_special_science_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_special_science_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_special_science_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_sped_teacher_v, '^[0-9]+$') AND (TRY_CAST(n.jhs_sped_teacher_v AS BIGINT) IS NULL OR TRY_CAST(n.jhs_sped_teacher_v AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_sped_teacher_iv, '^[0-9]+$') AND (TRY_CAST(n.jhs_sped_teacher_iv AS BIGINT) IS NULL OR TRY_CAST(n.jhs_sped_teacher_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_sped_teacher_iii, '^[0-9]+$') AND (TRY_CAST(n.jhs_sped_teacher_iii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_sped_teacher_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_sped_teacher_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_sped_teacher_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_sped_teacher_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_sped_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_sped_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_sped_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_master_teacher_iv, '^[0-9]+$') AND (TRY_CAST(n.shs_master_teacher_iv AS BIGINT) IS NULL OR TRY_CAST(n.shs_master_teacher_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_master_teacher_iii, '^[0-9]+$') AND (TRY_CAST(n.shs_master_teacher_iii AS BIGINT) IS NULL OR TRY_CAST(n.shs_master_teacher_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_master_teacher_ii, '^[0-9]+$') AND (TRY_CAST(n.shs_master_teacher_ii AS BIGINT) IS NULL OR TRY_CAST(n.shs_master_teacher_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_master_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.shs_master_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_master_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_teacher_iii, '^[0-9]+$') AND (TRY_CAST(n.shs_teacher_iii AS BIGINT) IS NULL OR TRY_CAST(n.shs_teacher_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_teacher_ii, '^[0-9]+$') AND (TRY_CAST(n.shs_teacher_ii AS BIGINT) IS NULL OR TRY_CAST(n.shs_teacher_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.shs_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_special_science_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.shs_special_science_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_special_science_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_principal_iv, '^[0-9]+$') AND (TRY_CAST(n.es_school_principal_iv AS BIGINT) IS NULL OR TRY_CAST(n.es_school_principal_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_principal_iii, '^[0-9]+$') AND (TRY_CAST(n.es_school_principal_iii AS BIGINT) IS NULL OR TRY_CAST(n.es_school_principal_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_principal_ii, '^[0-9]+$') AND (TRY_CAST(n.es_school_principal_ii AS BIGINT) IS NULL OR TRY_CAST(n.es_school_principal_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_principal_i, '^[0-9]+$') AND (TRY_CAST(n.es_school_principal_i AS BIGINT) IS NULL OR TRY_CAST(n.es_school_principal_i AS BIGINT) > 2147483647)
        OR regexp_like(n.es_head_teacher_vi, '^[0-9]+$') AND (TRY_CAST(n.es_head_teacher_vi AS BIGINT) IS NULL OR TRY_CAST(n.es_head_teacher_vi AS BIGINT) > 2147483647)
        OR regexp_like(n.es_head_teacher_v, '^[0-9]+$') AND (TRY_CAST(n.es_head_teacher_v AS BIGINT) IS NULL OR TRY_CAST(n.es_head_teacher_v AS BIGINT) > 2147483647)
        OR regexp_like(n.es_head_teacher_iv, '^[0-9]+$') AND (TRY_CAST(n.es_head_teacher_iv AS BIGINT) IS NULL OR TRY_CAST(n.es_head_teacher_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.es_head_teacher_iii, '^[0-9]+$') AND (TRY_CAST(n.es_head_teacher_iii AS BIGINT) IS NULL OR TRY_CAST(n.es_head_teacher_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_head_teacher_ii, '^[0-9]+$') AND (TRY_CAST(n.es_head_teacher_ii AS BIGINT) IS NULL OR TRY_CAST(n.es_head_teacher_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_head_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.es_head_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.es_head_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_coordinator_iii, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_coordinator_iii AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_coordinator_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_coordinator_ii, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_coordinator_ii AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_coordinator_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_coordinator_i, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_coordinator_i AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_coordinator_i AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_counselor_iii, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_counselor_iii AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_counselor_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_counselor_ii, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_counselor_ii AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_counselor_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_counselor_i, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_counselor_i AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_counselor_i AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_officer_ii, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_officer_ii AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_officer_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_project_development_officer_i, '^[0-9]+$') AND (TRY_CAST(n.es_project_development_officer_i AS BIGINT) IS NULL OR TRY_CAST(n.es_project_development_officer_i AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_assistant_iii_senior_bookkeeper AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_assistant_iii_senior_bookkeeper AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.es_security_guard, '^[0-9]+$') AND (TRY_CAST(n.es_security_guard AS BIGINT) IS NULL OR TRY_CAST(n.es_security_guard AS BIGINT) > 2147483647)
        OR regexp_like(n.es_utility_worker_i, '^[0-9]+$') AND (TRY_CAST(n.es_utility_worker_i AS BIGINT) IS NULL OR TRY_CAST(n.es_utility_worker_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_vocational_school_administrator_iii, '^[0-9]+$') AND (TRY_CAST(n.jhs_vocational_school_administrator_iii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_vocational_school_administrator_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_vocational_school_administrator_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_vocational_school_administrator_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_vocational_school_administrator_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_vocational_school_administrator_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_vocational_school_administrator_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_vocational_school_administrator_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_principal_iv, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_principal_iv AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_principal_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_principal_iii, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_principal_iii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_principal_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_principal_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_principal_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_principal_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_principal_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_principal_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_principal_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_assistant_school_principal_iii, '^[0-9]+$') AND (TRY_CAST(n.jhs_assistant_school_principal_iii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_assistant_school_principal_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_assistant_school_principal_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_assistant_school_principal_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_assistant_school_principal_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_assistant_school_principal_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_assistant_school_principal_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_assistant_school_principal_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_head_teacher_vi, '^[0-9]+$') AND (TRY_CAST(n.jhs_head_teacher_vi AS BIGINT) IS NULL OR TRY_CAST(n.jhs_head_teacher_vi AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_head_teacher_v, '^[0-9]+$') AND (TRY_CAST(n.jhs_head_teacher_v AS BIGINT) IS NULL OR TRY_CAST(n.jhs_head_teacher_v AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_head_teacher_iv, '^[0-9]+$') AND (TRY_CAST(n.jhs_head_teacher_iv AS BIGINT) IS NULL OR TRY_CAST(n.jhs_head_teacher_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_head_teacher_iii, '^[0-9]+$') AND (TRY_CAST(n.jhs_head_teacher_iii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_head_teacher_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_head_teacher_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_head_teacher_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_head_teacher_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_head_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_head_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_head_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_coordinator_iii, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_coordinator_iii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_coordinator_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_coordinator_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_coordinator_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_coordinator_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_coordinator_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_coordinator_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_coordinator_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_counselor_iii, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_counselor_iii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_counselor_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_counselor_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_counselor_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_counselor_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_counselor_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_counselor_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_counselor_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_officer_iv, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_officer_iv AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_officer_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_officer_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_officer_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_officer_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_project_development_officer_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_project_development_officer_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_project_development_officer_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_librarian_iii, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_librarian_iii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_librarian_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_librarian_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_librarian_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_librarian_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_librarian_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_librarian_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_librarian_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_accountant_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_accountant_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_accountant_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_cashier_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_cashier_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_cashier_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_supply_officer_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_supply_officer_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_supply_officer_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_assistant_iii_senior_bookkeeper AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_assistant_iii_senior_bookkeeper AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_bookkeeper, '^[0-9]+$') AND (TRY_CAST(n.jhs_bookkeeper AS BIGINT) IS NULL OR TRY_CAST(n.jhs_bookkeeper AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_aide_vi, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_aide_vi AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_aide_vi AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_heavy_equipment_operator_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_heavy_equipment_operator_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_heavy_equipment_operator_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_driver_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_driver_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_driver_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_security_guard_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_security_guard_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_security_guard_i AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_light_equipment_operator, '^[0-9]+$') AND (TRY_CAST(n.jhs_light_equipment_operator AS BIGINT) IS NULL OR TRY_CAST(n.jhs_light_equipment_operator AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_utility_worker_i, '^[0-9]+$') AND (TRY_CAST(n.jhs_utility_worker_i AS BIGINT) IS NULL OR TRY_CAST(n.jhs_utility_worker_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_principal_iv, '^[0-9]+$') AND (TRY_CAST(n.shs_school_principal_iv AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_principal_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_principal_iii, '^[0-9]+$') AND (TRY_CAST(n.shs_school_principal_iii AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_principal_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_principal_ii, '^[0-9]+$') AND (TRY_CAST(n.shs_school_principal_ii AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_principal_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_principal_i, '^[0-9]+$') AND (TRY_CAST(n.shs_school_principal_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_principal_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_total_school_principal, '^[0-9]+$') AND (TRY_CAST(n.shs_total_school_principal AS BIGINT) IS NULL OR TRY_CAST(n.shs_total_school_principal AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_assistant_principal_iii, '^[0-9]+$') AND (TRY_CAST(n.shs_assistant_principal_iii AS BIGINT) IS NULL OR TRY_CAST(n.shs_assistant_principal_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_assistant_principal_ii, '^[0-9]+$') AND (TRY_CAST(n.shs_assistant_principal_ii AS BIGINT) IS NULL OR TRY_CAST(n.shs_assistant_principal_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_assistant_principal_i, '^[0-9]+$') AND (TRY_CAST(n.shs_assistant_principal_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_assistant_principal_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_head_teacher_vi, '^[0-9]+$') AND (TRY_CAST(n.shs_head_teacher_vi AS BIGINT) IS NULL OR TRY_CAST(n.shs_head_teacher_vi AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_head_teacher_v, '^[0-9]+$') AND (TRY_CAST(n.shs_head_teacher_v AS BIGINT) IS NULL OR TRY_CAST(n.shs_head_teacher_v AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_head_teacher_iv, '^[0-9]+$') AND (TRY_CAST(n.shs_head_teacher_iv AS BIGINT) IS NULL OR TRY_CAST(n.shs_head_teacher_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_head_teacher_iii, '^[0-9]+$') AND (TRY_CAST(n.shs_head_teacher_iii AS BIGINT) IS NULL OR TRY_CAST(n.shs_head_teacher_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_head_teacher_ii, '^[0-9]+$') AND (TRY_CAST(n.shs_head_teacher_ii AS BIGINT) IS NULL OR TRY_CAST(n.shs_head_teacher_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_head_teacher_i, '^[0-9]+$') AND (TRY_CAST(n.shs_head_teacher_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_head_teacher_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_nurse_ii, '^[0-9]+$') AND (TRY_CAST(n.shs_school_nurse_ii AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_nurse_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_officer_iv, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_officer_iv AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_officer_iv AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_officer_ii, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_officer_ii AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_officer_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_librarian_iii, '^[0-9]+$') AND (TRY_CAST(n.shs_school_librarian_iii AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_librarian_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_librarian_ii, '^[0-9]+$') AND (TRY_CAST(n.shs_school_librarian_ii AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_librarian_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_librarian_i, '^[0-9]+$') AND (TRY_CAST(n.shs_school_librarian_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_librarian_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_service_specialist_ii, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_service_specialist_ii AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_service_specialist_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_service_specialist_i, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_service_specialist_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_service_specialist_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_counselor_iii, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_counselor_iii AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_counselor_iii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_counselor_ii, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_counselor_ii AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_counselor_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_counselor_i, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_counselor_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_counselor_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_accounting_i, '^[0-9]+$') AND (TRY_CAST(n.shs_accounting_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_accounting_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_project_development_officer_i, '^[0-9]+$') AND (TRY_CAST(n.shs_project_development_officer_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_project_development_officer_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_registrar_i, '^[0-9]+$') AND (TRY_CAST(n.shs_registrar_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_registrar_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_cashier_i, '^[0-9]+$') AND (TRY_CAST(n.shs_cashier_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_cashier_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_supply_officer_i, '^[0-9]+$') AND (TRY_CAST(n.shs_supply_officer_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_supply_officer_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_assistant_iii_senior_bookkeeper AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_assistant_iii_senior_bookkeeper AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_assistant_i, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_assistant_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_assistant_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_aide_vi, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_aide_vi AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_aide_vi AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_heavy_equipment_operator_i, '^[0-9]+$') AND (TRY_CAST(n.shs_heavy_equipment_operator_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_heavy_equipment_operator_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_security_guard_i, '^[0-9]+$') AND (TRY_CAST(n.shs_security_guard_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_security_guard_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_light_equipment_operator_i, '^[0-9]+$') AND (TRY_CAST(n.shs_light_equipment_operator_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_light_equipment_operator_i AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_utility_worker_i, '^[0-9]+$') AND (TRY_CAST(n.shs_utility_worker_i AS BIGINT) IS NULL OR TRY_CAST(n.shs_utility_worker_i AS BIGINT) > 2147483647)
        OR regexp_like(n.kinder_teachers_sef_province, '^[0-9]+$') AND (TRY_CAST(n.kinder_teachers_sef_province AS BIGINT) IS NULL OR TRY_CAST(n.kinder_teachers_sef_province AS BIGINT) > 2147483647)
        OR regexp_like(n.kinder_teachers_sef_municipality_city, '^[0-9]+$') AND (TRY_CAST(n.kinder_teachers_sef_municipality_city AS BIGINT) IS NULL OR TRY_CAST(n.kinder_teachers_sef_municipality_city AS BIGINT) > 2147483647)
        OR regexp_like(n.kinder_teachers_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.kinder_teachers_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.kinder_teachers_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.kinder_teachers_other_funding, '^[0-9]+$') AND (TRY_CAST(n.kinder_teachers_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.kinder_teachers_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_teachers_sef_province, '^[0-9]+$') AND (TRY_CAST(n.es_teachers_sef_province AS BIGINT) IS NULL OR TRY_CAST(n.es_teachers_sef_province AS BIGINT) > 2147483647)
        OR regexp_like(n.es_teachers_sef_municipality_city, '^[0-9]+$') AND (TRY_CAST(n.es_teachers_sef_municipality_city AS BIGINT) IS NULL OR TRY_CAST(n.es_teachers_sef_municipality_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_teachers_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_teachers_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_teachers_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_teachers_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_teachers_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_teachers_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_teachers_sef_province, '^[0-9]+$') AND (TRY_CAST(n.jhs_teachers_sef_province AS BIGINT) IS NULL OR TRY_CAST(n.jhs_teachers_sef_province AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_teachers_sef_municipality_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_teachers_sef_municipality_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_teachers_sef_municipality_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_teachers_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_teachers_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_teachers_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_teachers_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_teachers_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_teachers_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_teachers_sef_province, '^[0-9]+$') AND (TRY_CAST(n.shs_teachers_sef_province AS BIGINT) IS NULL OR TRY_CAST(n.shs_teachers_sef_province AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_teachers_sef_municipality_city, '^[0-9]+$') AND (TRY_CAST(n.shs_teachers_sef_municipality_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_teachers_sef_municipality_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_teachers_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_teachers_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_teachers_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_teachers_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_teachers_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_teachers_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_learning_support_aide_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_learning_support_aide_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_learning_support_aide_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_learning_support_aide_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_learning_support_aide_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_learning_support_aide_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_learning_support_aide_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_learning_support_aide_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_learning_support_aide_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_learning_support_aide_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_learning_support_aide_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_officer_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_officer_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_officer_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_officer_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_officer_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_officer_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_officer_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_officer_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_officer_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_officer_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_officer_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_officer_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_assistant_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_assistant_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_assistant_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_assistant_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_assistant_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_assistant_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_assistant_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_assistant_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_assistant_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_assistant_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_assistant_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_aide_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_aide_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_aide_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_aide_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_aide_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_aide_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_aide_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_aide_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_aide_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_administrative_aide_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_administrative_aide_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_administrative_aide_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_project_development_officer_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_project_development_officer_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_project_development_officer_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_project_development_officer_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_project_development_officer_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_project_development_officer_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_project_development_officer_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_project_development_officer_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_project_development_officer_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_project_development_officer_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_project_development_officer_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_project_development_officer_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_doctor_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_school_doctor_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_school_doctor_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_doctor_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_school_doctor_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_school_doctor_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_doctor_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_school_doctor_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_school_doctor_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_doctor_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_school_doctor_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_school_doctor_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_dentist_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_school_dentist_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_school_dentist_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_dentist_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_school_dentist_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_school_dentist_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_dentist_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_school_dentist_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_school_dentist_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_dentist_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_school_dentist_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_school_dentist_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_nurse_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_school_nurse_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_school_nurse_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_nurse_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_school_nurse_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_school_nurse_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_nurse_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_school_nurse_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_school_nurse_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_school_nurse_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_school_nurse_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_school_nurse_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_librarian_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_librarian_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_librarian_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_librarian_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_librarian_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_librarian_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_librarian_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_librarian_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_librarian_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_librarian_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_librarian_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_librarian_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_library_assistant_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_library_assistant_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_library_assistant_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_library_assistant_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_library_assistant_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_library_assistant_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_library_assistant_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_library_assistant_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_library_assistant_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_library_assistant_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_library_assistant_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_library_assistant_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_counselor_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_counselor_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_counselor_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_counselor_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_counselor_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_counselor_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_counselor_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_counselor_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_counselor_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_counselor_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_counselor_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_advocate_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_advocate_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_advocate_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_advocate_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_advocate_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_advocate_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_advocate_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_advocate_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_advocate_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_advocate_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_advocate_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_assistant_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_assistant_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_assistant_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_assistant_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_assistant_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_assistant_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_assistant_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_assistant_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_guidance_assistant_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_guidance_assistant_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_guidance_assistant_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_computer_technician_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.es_computer_technician_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.es_computer_technician_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.es_computer_technician_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.es_computer_technician_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.es_computer_technician_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.es_computer_technician_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.es_computer_technician_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_computer_technician_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.es_computer_technician_other_funding, '^[0-9]+$') AND (TRY_CAST(n.es_computer_technician_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.es_computer_technician_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_learning_support_aide_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_learning_support_aide_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_learning_support_aide_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_learning_support_aide_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_learning_support_aide_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_learning_support_aide_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_learning_support_aide_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_learning_support_aide_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_learning_support_aide_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_learning_support_aide_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_learning_support_aide_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_officer_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_officer_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_officer_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_officer_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_officer_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_officer_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_officer_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_officer_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_officer_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_officer_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_officer_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_officer_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_assistant_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_assistant_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_assistant_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_assistant_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_assistant_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_assistant_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_assistant_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_assistant_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_assistant_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_assistant_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_assistant_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_aide_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_aide_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_aide_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_aide_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_aide_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_aide_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_aide_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_aide_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_aide_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_administrative_aide_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_administrative_aide_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_administrative_aide_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_project_development_officer_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_project_development_officer_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_project_development_officer_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_project_development_officer_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_project_development_officer_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_project_development_officer_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_project_development_officer_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_project_development_officer_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_project_development_officer_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_project_development_officer_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_project_development_officer_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_project_development_officer_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_doctor_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_doctor_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_doctor_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_doctor_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_doctor_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_doctor_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_doctor_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_doctor_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_doctor_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_doctor_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_doctor_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_doctor_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_dentist_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_dentist_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_dentist_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_dentist_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_dentist_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_dentist_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_dentist_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_dentist_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_dentist_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_dentist_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_dentist_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_dentist_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_nurse_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_nurse_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_nurse_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_nurse_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_nurse_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_nurse_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_nurse_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_nurse_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_nurse_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_school_nurse_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_school_nurse_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_school_nurse_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_librarian_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_librarian_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_librarian_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_librarian_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_librarian_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_librarian_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_librarian_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_librarian_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_librarian_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_librarian_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_librarian_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_librarian_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_library_assistant_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_library_assistant_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_library_assistant_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_library_assistant_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_library_assistant_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_library_assistant_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_library_assistant_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_library_assistant_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_library_assistant_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_library_assistant_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_library_assistant_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_library_assistant_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_counselor_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_counselor_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_counselor_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_counselor_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_counselor_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_counselor_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_counselor_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_counselor_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_counselor_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_counselor_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_counselor_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_advocate_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_advocate_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_advocate_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_advocate_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_advocate_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_advocate_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_advocate_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_advocate_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_advocate_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_advocate_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_advocate_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_assistant_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_assistant_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_assistant_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_assistant_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_assistant_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_assistant_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_assistant_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_assistant_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_guidance_assistant_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_guidance_assistant_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_guidance_assistant_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_computer_technician_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.jhs_computer_technician_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.jhs_computer_technician_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_computer_technician_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.jhs_computer_technician_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.jhs_computer_technician_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_computer_technician_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_computer_technician_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_computer_technician_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.jhs_computer_technician_other_funding, '^[0-9]+$') AND (TRY_CAST(n.jhs_computer_technician_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.jhs_computer_technician_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_learning_support_aide_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_learning_support_aide_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_learning_support_aide_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_learning_support_aide_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_learning_support_aide_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_learning_support_aide_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_learning_support_aide_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_learning_support_aide_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_learning_support_aide_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_learning_support_aide_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_learning_support_aide_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_officer_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_officer_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_officer_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_officer_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_officer_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_officer_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_officer_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_officer_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_officer_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_officer_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_officer_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_officer_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_assistant_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_assistant_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_assistant_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_assistant_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_assistant_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_assistant_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_assistant_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_assistant_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_assistant_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_assistant_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_assistant_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_aide_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_aide_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_aide_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_aide_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_aide_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_aide_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_aide_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_aide_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_aide_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_administrative_aide_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_administrative_aide_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_administrative_aide_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_project_development_officer_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_project_development_officer_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_project_development_officer_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_project_development_officer_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_project_development_officer_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_project_development_officer_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_project_development_officer_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_project_development_officer_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_project_development_officer_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_project_development_officer_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_project_development_officer_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_project_development_officer_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_doctor_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_school_doctor_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_doctor_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_doctor_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_school_doctor_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_doctor_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_doctor_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_school_doctor_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_doctor_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_doctor_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_school_doctor_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_doctor_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_dentist_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_school_dentist_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_dentist_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_dentist_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_school_dentist_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_dentist_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_dentist_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_school_dentist_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_dentist_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_dentist_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_school_dentist_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_dentist_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_nurse_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_school_nurse_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_nurse_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_nurse_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_school_nurse_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_nurse_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_nurse_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_school_nurse_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_nurse_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_school_nurse_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_school_nurse_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_school_nurse_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_librarian_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_librarian_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_librarian_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_librarian_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_librarian_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_librarian_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_librarian_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_librarian_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_librarian_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_librarian_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_librarian_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_librarian_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_library_assistant_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_library_assistant_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_library_assistant_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_library_assistant_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_library_assistant_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_library_assistant_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_library_assistant_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_library_assistant_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_library_assistant_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_library_assistant_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_library_assistant_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_library_assistant_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_counselor_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_counselor_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_counselor_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_counselor_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_counselor_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_counselor_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_counselor_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_counselor_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_counselor_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_counselor_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_counselor_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_advocate_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_advocate_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_advocate_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_advocate_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_advocate_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_advocate_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_advocate_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_advocate_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_advocate_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_advocate_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_advocate_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_assistant_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_assistant_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_assistant_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_assistant_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_assistant_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_assistant_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_assistant_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_assistant_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_guidance_assistant_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_guidance_assistant_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_guidance_assistant_other_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_computer_technician_sef_provincial, '^[0-9]+$') AND (TRY_CAST(n.shs_computer_technician_sef_provincial AS BIGINT) IS NULL OR TRY_CAST(n.shs_computer_technician_sef_provincial AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_computer_technician_sef_municipal_city, '^[0-9]+$') AND (TRY_CAST(n.shs_computer_technician_sef_municipal_city AS BIGINT) IS NULL OR TRY_CAST(n.shs_computer_technician_sef_municipal_city AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_computer_technician_lgu_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_computer_technician_lgu_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_computer_technician_lgu_funding AS BIGINT) > 2147483647)
        OR regexp_like(n.shs_computer_technician_other_funding, '^[0-9]+$') AND (TRY_CAST(n.shs_computer_technician_other_funding AS BIGINT) IS NULL OR TRY_CAST(n.shs_computer_technician_other_funding AS BIGINT) > 2147483647) THEN 'measure_above_int_max' END,
      CASE WHEN n.sector <> 'Public' AND (n.es_master_teacher_iv <> ''
        OR n.es_master_teacher_iii <> ''
        OR n.es_master_teacher_ii <> ''
        OR n.es_master_teacher_i <> ''
        OR n.es_teacher_iii <> ''
        OR n.es_teacher_ii <> ''
        OR n.es_teacher_i <> ''
        OR n.es_sped_sned_teacher_v <> ''
        OR n.es_sped_sned_teacher_iv <> ''
        OR n.es_sped_sned_teacher_iii <> ''
        OR n.es_sped_sned_teacher_ii <> ''
        OR n.es_sped_sned_teacher_i <> ''
        OR n.jhs_instructor_iii <> ''
        OR n.jhs_instructor_ii <> ''
        OR n.jhs_instructor_i <> ''
        OR n.jhs_master_teacher_iv <> ''
        OR n.jhs_master_teacher_iii <> ''
        OR n.jhs_master_teacher_ii <> ''
        OR n.jhs_master_teacher_i <> ''
        OR n.jhs_teacher_iii <> ''
        OR n.jhs_teacher_ii <> ''
        OR n.jhs_teacher_i <> ''
        OR n.jhs_special_science_teacher_i <> ''
        OR n.jhs_sped_teacher_v <> ''
        OR n.jhs_sped_teacher_iv <> ''
        OR n.jhs_sped_teacher_iii <> ''
        OR n.jhs_sped_teacher_ii <> ''
        OR n.jhs_sped_teacher_i <> ''
        OR n.shs_master_teacher_iv <> ''
        OR n.shs_master_teacher_iii <> ''
        OR n.shs_master_teacher_ii <> ''
        OR n.shs_master_teacher_i <> ''
        OR n.shs_teacher_iii <> ''
        OR n.shs_teacher_ii <> ''
        OR n.shs_teacher_i <> ''
        OR n.shs_special_science_teacher_i <> ''
        OR n.es_school_principal_iv <> ''
        OR n.es_school_principal_iii <> ''
        OR n.es_school_principal_ii <> ''
        OR n.es_school_principal_i <> ''
        OR n.es_head_teacher_vi <> ''
        OR n.es_head_teacher_v <> ''
        OR n.es_head_teacher_iv <> ''
        OR n.es_head_teacher_iii <> ''
        OR n.es_head_teacher_ii <> ''
        OR n.es_head_teacher_i <> ''
        OR n.es_guidance_coordinator_iii <> ''
        OR n.es_guidance_coordinator_ii <> ''
        OR n.es_guidance_coordinator_i <> ''
        OR n.es_guidance_counselor_iii <> ''
        OR n.es_guidance_counselor_ii <> ''
        OR n.es_guidance_counselor_i <> ''
        OR n.es_administrative_officer_ii <> ''
        OR n.es_project_development_officer_i <> ''
        OR n.es_administrative_assistant_iii_senior_bookkeeper <> ''
        OR n.es_administrative_assistant_ii_disbursing_officer_ii <> ''
        OR n.es_security_guard <> ''
        OR n.es_utility_worker_i <> ''
        OR n.jhs_vocational_school_administrator_iii <> ''
        OR n.jhs_vocational_school_administrator_ii <> ''
        OR n.jhs_vocational_school_administrator_i <> ''
        OR n.jhs_school_principal_iv <> ''
        OR n.jhs_school_principal_iii <> ''
        OR n.jhs_school_principal_ii <> ''
        OR n.jhs_school_principal_i <> ''
        OR n.jhs_assistant_school_principal_iii <> ''
        OR n.jhs_assistant_school_principal_ii <> ''
        OR n.jhs_assistant_school_principal_i <> ''
        OR n.jhs_head_teacher_vi <> ''
        OR n.jhs_head_teacher_v <> ''
        OR n.jhs_head_teacher_iv <> ''
        OR n.jhs_head_teacher_iii <> ''
        OR n.jhs_head_teacher_ii <> ''
        OR n.jhs_head_teacher_i <> ''
        OR n.jhs_guidance_coordinator_iii <> ''
        OR n.jhs_guidance_coordinator_ii <> ''
        OR n.jhs_guidance_coordinator_i <> ''
        OR n.jhs_guidance_counselor_iii <> ''
        OR n.jhs_guidance_counselor_ii <> ''
        OR n.jhs_guidance_counselor_i <> ''
        OR n.jhs_administrative_officer_iv <> ''
        OR n.jhs_administrative_officer_ii <> ''
        OR n.jhs_project_development_officer_i <> ''
        OR n.jhs_school_librarian_iii <> ''
        OR n.jhs_school_librarian_ii <> ''
        OR n.jhs_school_librarian_i <> ''
        OR n.jhs_accountant_i <> ''
        OR n.jhs_cashier_i <> ''
        OR n.jhs_supply_officer_i <> ''
        OR n.jhs_administrative_assistant_iii_senior_bookkeeper <> ''
        OR n.jhs_bookkeeper <> ''
        OR n.jhs_administrative_assistant_ii_disbursing_officer_ii <> ''
        OR n.jhs_administrative_assistant_ii_disbursing_officer_i <> ''
        OR n.jhs_administrative_aide_vi <> ''
        OR n.jhs_heavy_equipment_operator_i <> ''
        OR n.jhs_driver_i <> ''
        OR n.jhs_security_guard_i <> ''
        OR n.jhs_light_equipment_operator <> ''
        OR n.jhs_utility_worker_i <> ''
        OR n.shs_school_principal_iv <> ''
        OR n.shs_school_principal_iii <> ''
        OR n.shs_school_principal_ii <> ''
        OR n.shs_school_principal_i <> ''
        OR n.shs_total_school_principal <> ''
        OR n.shs_assistant_principal_iii <> ''
        OR n.shs_assistant_principal_ii <> ''
        OR n.shs_assistant_principal_i <> ''
        OR n.shs_head_teacher_vi <> ''
        OR n.shs_head_teacher_v <> ''
        OR n.shs_head_teacher_iv <> ''
        OR n.shs_head_teacher_iii <> ''
        OR n.shs_head_teacher_ii <> ''
        OR n.shs_head_teacher_i <> ''
        OR n.shs_school_nurse_ii <> ''
        OR n.shs_administrative_officer_iv <> ''
        OR n.shs_administrative_officer_ii <> ''
        OR n.shs_school_librarian_iii <> ''
        OR n.shs_school_librarian_ii <> ''
        OR n.shs_school_librarian_i <> ''
        OR n.shs_guidance_service_specialist_ii <> ''
        OR n.shs_guidance_service_specialist_i <> ''
        OR n.shs_guidance_counselor_iii <> ''
        OR n.shs_guidance_counselor_ii <> ''
        OR n.shs_guidance_counselor_i <> ''
        OR n.shs_accounting_i <> ''
        OR n.shs_project_development_officer_i <> ''
        OR n.shs_registrar_i <> ''
        OR n.shs_cashier_i <> ''
        OR n.shs_supply_officer_i <> ''
        OR n.shs_administrative_assistant_iii_senior_bookkeeper <> ''
        OR n.shs_administrative_assistant_ii_disbursing_officer_ii <> ''
        OR n.shs_administrative_assistant_i <> ''
        OR n.shs_administrative_aide_vi <> ''
        OR n.shs_heavy_equipment_operator_i <> ''
        OR n.shs_security_guard_i <> ''
        OR n.shs_light_equipment_operator_i <> ''
        OR n.shs_utility_worker_i <> ''
        OR n.kinder_teachers_sef_province <> ''
        OR n.kinder_teachers_sef_municipality_city <> ''
        OR n.kinder_teachers_lgu_funding <> ''
        OR n.kinder_teachers_other_funding <> ''
        OR n.es_teachers_sef_province <> ''
        OR n.es_teachers_sef_municipality_city <> ''
        OR n.es_teachers_lgu_funding <> ''
        OR n.es_teachers_other_funding <> ''
        OR n.jhs_teachers_sef_province <> ''
        OR n.jhs_teachers_sef_municipality_city <> ''
        OR n.jhs_teachers_lgu_funding <> ''
        OR n.jhs_teachers_other_funding <> ''
        OR n.shs_teachers_sef_province <> ''
        OR n.shs_teachers_sef_municipality_city <> ''
        OR n.shs_teachers_lgu_funding <> ''
        OR n.shs_teachers_other_funding <> ''
        OR n.es_learning_support_aide_sef_provincial <> ''
        OR n.es_learning_support_aide_sef_municipal_city <> ''
        OR n.es_learning_support_aide_lgu_funding <> ''
        OR n.es_learning_support_aide_other_funding <> ''
        OR n.es_administrative_officer_sef_provincial <> ''
        OR n.es_administrative_officer_sef_municipal_city <> ''
        OR n.es_administrative_officer_lgu_funding <> ''
        OR n.es_administrative_officer_other_funding <> ''
        OR n.es_administrative_assistant_sef_provincial <> ''
        OR n.es_administrative_assistant_sef_municipal_city <> ''
        OR n.es_administrative_assistant_lgu_funding <> ''
        OR n.es_administrative_assistant_other_funding <> ''
        OR n.es_administrative_aide_sef_provincial <> ''
        OR n.es_administrative_aide_sef_municipal_city <> ''
        OR n.es_administrative_aide_lgu_funding <> ''
        OR n.es_administrative_aide_other_funding <> ''
        OR n.es_project_development_officer_sef_provincial <> ''
        OR n.es_project_development_officer_sef_municipal_city <> ''
        OR n.es_project_development_officer_lgu_funding <> ''
        OR n.es_project_development_officer_other_funding <> ''
        OR n.es_school_doctor_sef_provincial <> ''
        OR n.es_school_doctor_sef_municipal_city <> ''
        OR n.es_school_doctor_lgu_funding <> ''
        OR n.es_school_doctor_other_funding <> ''
        OR n.es_school_dentist_sef_provincial <> ''
        OR n.es_school_dentist_sef_municipal_city <> ''
        OR n.es_school_dentist_lgu_funding <> ''
        OR n.es_school_dentist_other_funding <> ''
        OR n.es_school_nurse_sef_provincial <> ''
        OR n.es_school_nurse_sef_municipal_city <> ''
        OR n.es_school_nurse_lgu_funding <> ''
        OR n.es_school_nurse_other_funding <> ''
        OR n.es_librarian_sef_provincial <> ''
        OR n.es_librarian_sef_municipal_city <> ''
        OR n.es_librarian_lgu_funding <> ''
        OR n.es_librarian_other_funding <> ''
        OR n.es_library_assistant_sef_provincial <> ''
        OR n.es_library_assistant_sef_municipal_city <> ''
        OR n.es_library_assistant_lgu_funding <> ''
        OR n.es_library_assistant_other_funding <> ''
        OR n.es_guidance_counselor_sef_provincial <> ''
        OR n.es_guidance_counselor_sef_municipal_city <> ''
        OR n.es_guidance_counselor_lgu_funding <> ''
        OR n.es_guidance_counselor_other_funding <> ''
        OR n.es_guidance_advocate_sef_provincial <> ''
        OR n.es_guidance_advocate_sef_municipal_city <> ''
        OR n.es_guidance_advocate_lgu_funding <> ''
        OR n.es_guidance_advocate_other_funding <> ''
        OR n.es_guidance_assistant_sef_provincial <> ''
        OR n.es_guidance_assistant_sef_municipal_city <> ''
        OR n.es_guidance_assistant_lgu_funding <> ''
        OR n.es_guidance_assistant_other_funding <> ''
        OR n.es_computer_technician_sef_provincial <> ''
        OR n.es_computer_technician_sef_municipal_city <> ''
        OR n.es_computer_technician_lgu_funding <> ''
        OR n.es_computer_technician_other_funding <> ''
        OR n.jhs_learning_support_aide_sef_provincial <> ''
        OR n.jhs_learning_support_aide_sef_municipal_city <> ''
        OR n.jhs_learning_support_aide_lgu_funding <> ''
        OR n.jhs_learning_support_aide_other_funding <> ''
        OR n.jhs_administrative_officer_sef_provincial <> ''
        OR n.jhs_administrative_officer_sef_municipal_city <> ''
        OR n.jhs_administrative_officer_lgu_funding <> ''
        OR n.jhs_administrative_officer_other_funding <> ''
        OR n.jhs_administrative_assistant_sef_provincial <> ''
        OR n.jhs_administrative_assistant_sef_municipal_city <> ''
        OR n.jhs_administrative_assistant_lgu_funding <> ''
        OR n.jhs_administrative_assistant_other_funding <> ''
        OR n.jhs_administrative_aide_sef_provincial <> ''
        OR n.jhs_administrative_aide_sef_municipal_city <> ''
        OR n.jhs_administrative_aide_lgu_funding <> ''
        OR n.jhs_administrative_aide_other_funding <> ''
        OR n.jhs_project_development_officer_sef_provincial <> ''
        OR n.jhs_project_development_officer_sef_municipal_city <> ''
        OR n.jhs_project_development_officer_lgu_funding <> ''
        OR n.jhs_project_development_officer_other_funding <> ''
        OR n.jhs_school_doctor_sef_provincial <> ''
        OR n.jhs_school_doctor_sef_municipal_city <> ''
        OR n.jhs_school_doctor_lgu_funding <> ''
        OR n.jhs_school_doctor_other_funding <> ''
        OR n.jhs_school_dentist_sef_provincial <> ''
        OR n.jhs_school_dentist_sef_municipal_city <> ''
        OR n.jhs_school_dentist_lgu_funding <> ''
        OR n.jhs_school_dentist_other_funding <> ''
        OR n.jhs_school_nurse_sef_provincial <> ''
        OR n.jhs_school_nurse_sef_municipal_city <> ''
        OR n.jhs_school_nurse_lgu_funding <> ''
        OR n.jhs_school_nurse_other_funding <> ''
        OR n.jhs_librarian_sef_provincial <> ''
        OR n.jhs_librarian_sef_municipal_city <> ''
        OR n.jhs_librarian_lgu_funding <> ''
        OR n.jhs_librarian_other_funding <> ''
        OR n.jhs_library_assistant_sef_provincial <> ''
        OR n.jhs_library_assistant_sef_municipal_city <> ''
        OR n.jhs_library_assistant_lgu_funding <> ''
        OR n.jhs_library_assistant_other_funding <> ''
        OR n.jhs_guidance_counselor_sef_provincial <> ''
        OR n.jhs_guidance_counselor_sef_municipal_city <> ''
        OR n.jhs_guidance_counselor_lgu_funding <> ''
        OR n.jhs_guidance_counselor_other_funding <> ''
        OR n.jhs_guidance_advocate_sef_provincial <> ''
        OR n.jhs_guidance_advocate_sef_municipal_city <> ''
        OR n.jhs_guidance_advocate_lgu_funding <> ''
        OR n.jhs_guidance_advocate_other_funding <> ''
        OR n.jhs_guidance_assistant_sef_provincial <> ''
        OR n.jhs_guidance_assistant_sef_municipal_city <> ''
        OR n.jhs_guidance_assistant_lgu_funding <> ''
        OR n.jhs_guidance_assistant_other_funding <> ''
        OR n.jhs_computer_technician_sef_provincial <> ''
        OR n.jhs_computer_technician_sef_municipal_city <> ''
        OR n.jhs_computer_technician_lgu_funding <> ''
        OR n.jhs_computer_technician_other_funding <> ''
        OR n.shs_learning_support_aide_sef_provincial <> ''
        OR n.shs_learning_support_aide_sef_municipal_city <> ''
        OR n.shs_learning_support_aide_lgu_funding <> ''
        OR n.shs_learning_support_aide_other_funding <> ''
        OR n.shs_administrative_officer_sef_provincial <> ''
        OR n.shs_administrative_officer_sef_municipal_city <> ''
        OR n.shs_administrative_officer_lgu_funding <> ''
        OR n.shs_administrative_officer_other_funding <> ''
        OR n.shs_administrative_assistant_sef_provincial <> ''
        OR n.shs_administrative_assistant_sef_municipal_city <> ''
        OR n.shs_administrative_assistant_lgu_funding <> ''
        OR n.shs_administrative_assistant_other_funding <> ''
        OR n.shs_administrative_aide_sef_provincial <> ''
        OR n.shs_administrative_aide_sef_municipal_city <> ''
        OR n.shs_administrative_aide_lgu_funding <> ''
        OR n.shs_administrative_aide_other_funding <> ''
        OR n.shs_project_development_officer_sef_provincial <> ''
        OR n.shs_project_development_officer_sef_municipal_city <> ''
        OR n.shs_project_development_officer_lgu_funding <> ''
        OR n.shs_project_development_officer_other_funding <> ''
        OR n.shs_school_doctor_sef_provincial <> ''
        OR n.shs_school_doctor_sef_municipal_city <> ''
        OR n.shs_school_doctor_lgu_funding <> ''
        OR n.shs_school_doctor_other_funding <> ''
        OR n.shs_school_dentist_sef_provincial <> ''
        OR n.shs_school_dentist_sef_municipal_city <> ''
        OR n.shs_school_dentist_lgu_funding <> ''
        OR n.shs_school_dentist_other_funding <> ''
        OR n.shs_school_nurse_sef_provincial <> ''
        OR n.shs_school_nurse_sef_municipal_city <> ''
        OR n.shs_school_nurse_lgu_funding <> ''
        OR n.shs_school_nurse_other_funding <> ''
        OR n.shs_librarian_sef_provincial <> ''
        OR n.shs_librarian_sef_municipal_city <> ''
        OR n.shs_librarian_lgu_funding <> ''
        OR n.shs_librarian_other_funding <> ''
        OR n.shs_library_assistant_sef_provincial <> ''
        OR n.shs_library_assistant_sef_municipal_city <> ''
        OR n.shs_library_assistant_lgu_funding <> ''
        OR n.shs_library_assistant_other_funding <> ''
        OR n.shs_guidance_counselor_sef_provincial <> ''
        OR n.shs_guidance_counselor_sef_municipal_city <> ''
        OR n.shs_guidance_counselor_lgu_funding <> ''
        OR n.shs_guidance_counselor_other_funding <> ''
        OR n.shs_guidance_advocate_sef_provincial <> ''
        OR n.shs_guidance_advocate_sef_municipal_city <> ''
        OR n.shs_guidance_advocate_lgu_funding <> ''
        OR n.shs_guidance_advocate_other_funding <> ''
        OR n.shs_guidance_assistant_sef_provincial <> ''
        OR n.shs_guidance_assistant_sef_municipal_city <> ''
        OR n.shs_guidance_assistant_lgu_funding <> ''
        OR n.shs_guidance_assistant_other_funding <> ''
        OR n.shs_computer_technician_sef_provincial <> ''
        OR n.shs_computer_technician_sef_municipal_city <> ''
        OR n.shs_computer_technician_lgu_funding <> ''
        OR n.shs_computer_technician_other_funding <> '') THEN 'measure_outside_public_scope' END,
      CASE WHEN (n.offers_es IN ('False') AND (n.es_master_teacher_iv <> ''
          OR n.es_master_teacher_iii <> ''
          OR n.es_master_teacher_ii <> ''
          OR n.es_master_teacher_i <> ''
          OR n.es_teacher_iii <> ''
          OR n.es_teacher_ii <> ''
          OR n.es_teacher_i <> ''
          OR n.es_sped_sned_teacher_v <> ''
          OR n.es_sped_sned_teacher_iv <> ''
          OR n.es_sped_sned_teacher_iii <> ''
          OR n.es_sped_sned_teacher_ii <> ''
          OR n.es_sped_sned_teacher_i <> ''
          OR n.es_school_principal_iv <> ''
          OR n.es_school_principal_iii <> ''
          OR n.es_school_principal_ii <> ''
          OR n.es_school_principal_i <> ''
          OR n.es_head_teacher_vi <> ''
          OR n.es_head_teacher_v <> ''
          OR n.es_head_teacher_iv <> ''
          OR n.es_head_teacher_iii <> ''
          OR n.es_head_teacher_ii <> ''
          OR n.es_head_teacher_i <> ''
          OR n.es_guidance_coordinator_iii <> ''
          OR n.es_guidance_coordinator_ii <> ''
          OR n.es_guidance_coordinator_i <> ''
          OR n.es_guidance_counselor_iii <> ''
          OR n.es_guidance_counselor_ii <> ''
          OR n.es_guidance_counselor_i <> ''
          OR n.es_administrative_officer_ii <> ''
          OR n.es_project_development_officer_i <> ''
          OR n.es_administrative_assistant_iii_senior_bookkeeper <> ''
          OR n.es_administrative_assistant_ii_disbursing_officer_ii <> ''
          OR n.es_security_guard <> ''
          OR n.es_utility_worker_i <> ''
          OR n.es_teachers_sef_province <> ''
          OR n.es_teachers_sef_municipality_city <> ''
          OR n.es_teachers_lgu_funding <> ''
          OR n.es_teachers_other_funding <> ''
          OR n.es_learning_support_aide_sef_provincial <> ''
          OR n.es_learning_support_aide_sef_municipal_city <> ''
          OR n.es_learning_support_aide_lgu_funding <> ''
          OR n.es_learning_support_aide_other_funding <> ''
          OR n.es_administrative_officer_sef_provincial <> ''
          OR n.es_administrative_officer_sef_municipal_city <> ''
          OR n.es_administrative_officer_lgu_funding <> ''
          OR n.es_administrative_officer_other_funding <> ''
          OR n.es_administrative_assistant_sef_provincial <> ''
          OR n.es_administrative_assistant_sef_municipal_city <> ''
          OR n.es_administrative_assistant_lgu_funding <> ''
          OR n.es_administrative_assistant_other_funding <> ''
          OR n.es_administrative_aide_sef_provincial <> ''
          OR n.es_administrative_aide_sef_municipal_city <> ''
          OR n.es_administrative_aide_lgu_funding <> ''
          OR n.es_administrative_aide_other_funding <> ''
          OR n.es_project_development_officer_sef_provincial <> ''
          OR n.es_project_development_officer_sef_municipal_city <> ''
          OR n.es_project_development_officer_lgu_funding <> ''
          OR n.es_project_development_officer_other_funding <> ''
          OR n.es_school_doctor_sef_provincial <> ''
          OR n.es_school_doctor_sef_municipal_city <> ''
          OR n.es_school_doctor_lgu_funding <> ''
          OR n.es_school_doctor_other_funding <> ''
          OR n.es_school_dentist_sef_provincial <> ''
          OR n.es_school_dentist_sef_municipal_city <> ''
          OR n.es_school_dentist_lgu_funding <> ''
          OR n.es_school_dentist_other_funding <> ''
          OR n.es_school_nurse_sef_provincial <> ''
          OR n.es_school_nurse_sef_municipal_city <> ''
          OR n.es_school_nurse_lgu_funding <> ''
          OR n.es_school_nurse_other_funding <> ''
          OR n.es_librarian_sef_provincial <> ''
          OR n.es_librarian_sef_municipal_city <> ''
          OR n.es_librarian_lgu_funding <> ''
          OR n.es_librarian_other_funding <> ''
          OR n.es_library_assistant_sef_provincial <> ''
          OR n.es_library_assistant_sef_municipal_city <> ''
          OR n.es_library_assistant_lgu_funding <> ''
          OR n.es_library_assistant_other_funding <> ''
          OR n.es_guidance_counselor_sef_provincial <> ''
          OR n.es_guidance_counselor_sef_municipal_city <> ''
          OR n.es_guidance_counselor_lgu_funding <> ''
          OR n.es_guidance_counselor_other_funding <> ''
          OR n.es_guidance_advocate_sef_provincial <> ''
          OR n.es_guidance_advocate_sef_municipal_city <> ''
          OR n.es_guidance_advocate_lgu_funding <> ''
          OR n.es_guidance_advocate_other_funding <> ''
          OR n.es_guidance_assistant_sef_provincial <> ''
          OR n.es_guidance_assistant_sef_municipal_city <> ''
          OR n.es_guidance_assistant_lgu_funding <> ''
          OR n.es_guidance_assistant_other_funding <> ''
          OR n.es_computer_technician_sef_provincial <> ''
          OR n.es_computer_technician_sef_municipal_city <> ''
          OR n.es_computer_technician_lgu_funding <> ''
          OR n.es_computer_technician_other_funding <> ''))
        OR (n.offers_jhs IN ('False') AND (n.jhs_instructor_iii <> ''
          OR n.jhs_instructor_ii <> ''
          OR n.jhs_instructor_i <> ''
          OR n.jhs_master_teacher_iv <> ''
          OR n.jhs_master_teacher_iii <> ''
          OR n.jhs_master_teacher_ii <> ''
          OR n.jhs_master_teacher_i <> ''
          OR n.jhs_teacher_iii <> ''
          OR n.jhs_teacher_ii <> ''
          OR n.jhs_teacher_i <> ''
          OR n.jhs_special_science_teacher_i <> ''
          OR n.jhs_sped_teacher_v <> ''
          OR n.jhs_sped_teacher_iv <> ''
          OR n.jhs_sped_teacher_iii <> ''
          OR n.jhs_sped_teacher_ii <> ''
          OR n.jhs_sped_teacher_i <> ''
          OR n.jhs_vocational_school_administrator_iii <> ''
          OR n.jhs_vocational_school_administrator_ii <> ''
          OR n.jhs_vocational_school_administrator_i <> ''
          OR n.jhs_school_principal_iv <> ''
          OR n.jhs_school_principal_iii <> ''
          OR n.jhs_school_principal_ii <> ''
          OR n.jhs_school_principal_i <> ''
          OR n.jhs_assistant_school_principal_iii <> ''
          OR n.jhs_assistant_school_principal_ii <> ''
          OR n.jhs_assistant_school_principal_i <> ''
          OR n.jhs_head_teacher_vi <> ''
          OR n.jhs_head_teacher_v <> ''
          OR n.jhs_head_teacher_iv <> ''
          OR n.jhs_head_teacher_iii <> ''
          OR n.jhs_head_teacher_ii <> ''
          OR n.jhs_head_teacher_i <> ''
          OR n.jhs_guidance_coordinator_iii <> ''
          OR n.jhs_guidance_coordinator_ii <> ''
          OR n.jhs_guidance_coordinator_i <> ''
          OR n.jhs_guidance_counselor_iii <> ''
          OR n.jhs_guidance_counselor_ii <> ''
          OR n.jhs_guidance_counselor_i <> ''
          OR n.jhs_administrative_officer_iv <> ''
          OR n.jhs_administrative_officer_ii <> ''
          OR n.jhs_project_development_officer_i <> ''
          OR n.jhs_school_librarian_iii <> ''
          OR n.jhs_school_librarian_ii <> ''
          OR n.jhs_school_librarian_i <> ''
          OR n.jhs_accountant_i <> ''
          OR n.jhs_cashier_i <> ''
          OR n.jhs_supply_officer_i <> ''
          OR n.jhs_administrative_assistant_iii_senior_bookkeeper <> ''
          OR n.jhs_bookkeeper <> ''
          OR n.jhs_administrative_assistant_ii_disbursing_officer_ii <> ''
          OR n.jhs_administrative_assistant_ii_disbursing_officer_i <> ''
          OR n.jhs_administrative_aide_vi <> ''
          OR n.jhs_heavy_equipment_operator_i <> ''
          OR n.jhs_driver_i <> ''
          OR n.jhs_security_guard_i <> ''
          OR n.jhs_light_equipment_operator <> ''
          OR n.jhs_utility_worker_i <> ''
          OR n.jhs_teachers_sef_province <> ''
          OR n.jhs_teachers_sef_municipality_city <> ''
          OR n.jhs_teachers_lgu_funding <> ''
          OR n.jhs_teachers_other_funding <> ''
          OR n.jhs_learning_support_aide_sef_provincial <> ''
          OR n.jhs_learning_support_aide_sef_municipal_city <> ''
          OR n.jhs_learning_support_aide_lgu_funding <> ''
          OR n.jhs_learning_support_aide_other_funding <> ''
          OR n.jhs_administrative_officer_sef_provincial <> ''
          OR n.jhs_administrative_officer_sef_municipal_city <> ''
          OR n.jhs_administrative_officer_lgu_funding <> ''
          OR n.jhs_administrative_officer_other_funding <> ''
          OR n.jhs_administrative_assistant_sef_provincial <> ''
          OR n.jhs_administrative_assistant_sef_municipal_city <> ''
          OR n.jhs_administrative_assistant_lgu_funding <> ''
          OR n.jhs_administrative_assistant_other_funding <> ''
          OR n.jhs_administrative_aide_sef_provincial <> ''
          OR n.jhs_administrative_aide_sef_municipal_city <> ''
          OR n.jhs_administrative_aide_lgu_funding <> ''
          OR n.jhs_administrative_aide_other_funding <> ''
          OR n.jhs_project_development_officer_sef_provincial <> ''
          OR n.jhs_project_development_officer_sef_municipal_city <> ''
          OR n.jhs_project_development_officer_lgu_funding <> ''
          OR n.jhs_project_development_officer_other_funding <> ''
          OR n.jhs_school_doctor_sef_provincial <> ''
          OR n.jhs_school_doctor_sef_municipal_city <> ''
          OR n.jhs_school_doctor_lgu_funding <> ''
          OR n.jhs_school_doctor_other_funding <> ''
          OR n.jhs_school_dentist_sef_provincial <> ''
          OR n.jhs_school_dentist_sef_municipal_city <> ''
          OR n.jhs_school_dentist_lgu_funding <> ''
          OR n.jhs_school_dentist_other_funding <> ''
          OR n.jhs_school_nurse_sef_provincial <> ''
          OR n.jhs_school_nurse_sef_municipal_city <> ''
          OR n.jhs_school_nurse_lgu_funding <> ''
          OR n.jhs_school_nurse_other_funding <> ''
          OR n.jhs_librarian_sef_provincial <> ''
          OR n.jhs_librarian_sef_municipal_city <> ''
          OR n.jhs_librarian_lgu_funding <> ''
          OR n.jhs_librarian_other_funding <> ''
          OR n.jhs_library_assistant_sef_provincial <> ''
          OR n.jhs_library_assistant_sef_municipal_city <> ''
          OR n.jhs_library_assistant_lgu_funding <> ''
          OR n.jhs_library_assistant_other_funding <> ''
          OR n.jhs_guidance_counselor_sef_provincial <> ''
          OR n.jhs_guidance_counselor_sef_municipal_city <> ''
          OR n.jhs_guidance_counselor_lgu_funding <> ''
          OR n.jhs_guidance_counselor_other_funding <> ''
          OR n.jhs_guidance_advocate_sef_provincial <> ''
          OR n.jhs_guidance_advocate_sef_municipal_city <> ''
          OR n.jhs_guidance_advocate_lgu_funding <> ''
          OR n.jhs_guidance_advocate_other_funding <> ''
          OR n.jhs_guidance_assistant_sef_provincial <> ''
          OR n.jhs_guidance_assistant_sef_municipal_city <> ''
          OR n.jhs_guidance_assistant_lgu_funding <> ''
          OR n.jhs_guidance_assistant_other_funding <> ''
          OR n.jhs_computer_technician_sef_provincial <> ''
          OR n.jhs_computer_technician_sef_municipal_city <> ''
          OR n.jhs_computer_technician_lgu_funding <> ''
          OR n.jhs_computer_technician_other_funding <> ''))
        OR (n.offers_shs IN ('False') AND (n.shs_master_teacher_iv <> ''
          OR n.shs_master_teacher_iii <> ''
          OR n.shs_master_teacher_ii <> ''
          OR n.shs_master_teacher_i <> ''
          OR n.shs_teacher_iii <> ''
          OR n.shs_teacher_ii <> ''
          OR n.shs_teacher_i <> ''
          OR n.shs_special_science_teacher_i <> ''
          OR n.shs_school_principal_iv <> ''
          OR n.shs_school_principal_iii <> ''
          OR n.shs_school_principal_ii <> ''
          OR n.shs_school_principal_i <> ''
          OR n.shs_total_school_principal <> ''
          OR n.shs_assistant_principal_iii <> ''
          OR n.shs_assistant_principal_ii <> ''
          OR n.shs_assistant_principal_i <> ''
          OR n.shs_head_teacher_vi <> ''
          OR n.shs_head_teacher_v <> ''
          OR n.shs_head_teacher_iv <> ''
          OR n.shs_head_teacher_iii <> ''
          OR n.shs_head_teacher_ii <> ''
          OR n.shs_head_teacher_i <> ''
          OR n.shs_school_nurse_ii <> ''
          OR n.shs_administrative_officer_iv <> ''
          OR n.shs_administrative_officer_ii <> ''
          OR n.shs_school_librarian_iii <> ''
          OR n.shs_school_librarian_ii <> ''
          OR n.shs_school_librarian_i <> ''
          OR n.shs_guidance_service_specialist_ii <> ''
          OR n.shs_guidance_service_specialist_i <> ''
          OR n.shs_guidance_counselor_iii <> ''
          OR n.shs_guidance_counselor_ii <> ''
          OR n.shs_guidance_counselor_i <> ''
          OR n.shs_accounting_i <> ''
          OR n.shs_project_development_officer_i <> ''
          OR n.shs_registrar_i <> ''
          OR n.shs_cashier_i <> ''
          OR n.shs_supply_officer_i <> ''
          OR n.shs_administrative_assistant_iii_senior_bookkeeper <> ''
          OR n.shs_administrative_assistant_ii_disbursing_officer_ii <> ''
          OR n.shs_administrative_assistant_i <> ''
          OR n.shs_administrative_aide_vi <> ''
          OR n.shs_heavy_equipment_operator_i <> ''
          OR n.shs_security_guard_i <> ''
          OR n.shs_light_equipment_operator_i <> ''
          OR n.shs_utility_worker_i <> ''
          OR n.shs_teachers_sef_province <> ''
          OR n.shs_teachers_sef_municipality_city <> ''
          OR n.shs_teachers_lgu_funding <> ''
          OR n.shs_teachers_other_funding <> ''
          OR n.shs_learning_support_aide_sef_provincial <> ''
          OR n.shs_learning_support_aide_sef_municipal_city <> ''
          OR n.shs_learning_support_aide_lgu_funding <> ''
          OR n.shs_learning_support_aide_other_funding <> ''
          OR n.shs_administrative_officer_sef_provincial <> ''
          OR n.shs_administrative_officer_sef_municipal_city <> ''
          OR n.shs_administrative_officer_lgu_funding <> ''
          OR n.shs_administrative_officer_other_funding <> ''
          OR n.shs_administrative_assistant_sef_provincial <> ''
          OR n.shs_administrative_assistant_sef_municipal_city <> ''
          OR n.shs_administrative_assistant_lgu_funding <> ''
          OR n.shs_administrative_assistant_other_funding <> ''
          OR n.shs_administrative_aide_sef_provincial <> ''
          OR n.shs_administrative_aide_sef_municipal_city <> ''
          OR n.shs_administrative_aide_lgu_funding <> ''
          OR n.shs_administrative_aide_other_funding <> ''
          OR n.shs_project_development_officer_sef_provincial <> ''
          OR n.shs_project_development_officer_sef_municipal_city <> ''
          OR n.shs_project_development_officer_lgu_funding <> ''
          OR n.shs_project_development_officer_other_funding <> ''
          OR n.shs_school_doctor_sef_provincial <> ''
          OR n.shs_school_doctor_sef_municipal_city <> ''
          OR n.shs_school_doctor_lgu_funding <> ''
          OR n.shs_school_doctor_other_funding <> ''
          OR n.shs_school_dentist_sef_provincial <> ''
          OR n.shs_school_dentist_sef_municipal_city <> ''
          OR n.shs_school_dentist_lgu_funding <> ''
          OR n.shs_school_dentist_other_funding <> ''
          OR n.shs_school_nurse_sef_provincial <> ''
          OR n.shs_school_nurse_sef_municipal_city <> ''
          OR n.shs_school_nurse_lgu_funding <> ''
          OR n.shs_school_nurse_other_funding <> ''
          OR n.shs_librarian_sef_provincial <> ''
          OR n.shs_librarian_sef_municipal_city <> ''
          OR n.shs_librarian_lgu_funding <> ''
          OR n.shs_librarian_other_funding <> ''
          OR n.shs_library_assistant_sef_provincial <> ''
          OR n.shs_library_assistant_sef_municipal_city <> ''
          OR n.shs_library_assistant_lgu_funding <> ''
          OR n.shs_library_assistant_other_funding <> ''
          OR n.shs_guidance_counselor_sef_provincial <> ''
          OR n.shs_guidance_counselor_sef_municipal_city <> ''
          OR n.shs_guidance_counselor_lgu_funding <> ''
          OR n.shs_guidance_counselor_other_funding <> ''
          OR n.shs_guidance_advocate_sef_provincial <> ''
          OR n.shs_guidance_advocate_sef_municipal_city <> ''
          OR n.shs_guidance_advocate_lgu_funding <> ''
          OR n.shs_guidance_advocate_other_funding <> ''
          OR n.shs_guidance_assistant_sef_provincial <> ''
          OR n.shs_guidance_assistant_sef_municipal_city <> ''
          OR n.shs_guidance_assistant_lgu_funding <> ''
          OR n.shs_guidance_assistant_other_funding <> ''
          OR n.shs_computer_technician_sef_provincial <> ''
          OR n.shs_computer_technician_sef_municipal_city <> ''
          OR n.shs_computer_technician_lgu_funding <> ''
          OR n.shs_computer_technician_other_funding <> '')) THEN 'measure_outside_offered_level' END,
      CASE WHEN n.enrollment_total IS NULL THEN 'enrollment_not_found' END,
      CASE WHEN n.enrollment_total IS NOT NULL AND (CASE WHEN regexp_like(n.es_master_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_master_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_master_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_master_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teacher_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teacher_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_sped_sned_teacher_v, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_v AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_sped_sned_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_sped_sned_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_sped_sned_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_sped_sned_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_instructor_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_instructor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_instructor_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_instructor_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_instructor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_instructor_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_instructor_i, '^[0-9]+$') AND TRY_CAST(n.jhs_instructor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_instructor_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_master_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_master_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_master_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_master_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teacher_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teacher_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_special_science_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_special_science_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_special_science_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_sped_teacher_v, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_v AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_sped_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_sped_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_sped_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_sped_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_master_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_master_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_master_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_master_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.shs_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teacher_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.shs_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teacher_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_special_science_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_special_science_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_special_science_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_principal_iv, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_head_teacher_vi, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_vi AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_head_teacher_v, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_v AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_head_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_head_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_head_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_head_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_coordinator_iii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_coordinator_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_coordinator_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_coordinator_ii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_coordinator_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_coordinator_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_coordinator_i, '^[0-9]+$') AND TRY_CAST(n.es_guidance_coordinator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_coordinator_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_counselor_iii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_counselor_ii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_counselor_i, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_officer_ii, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_project_development_officer_i, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_iii_senior_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_iii_senior_bookkeeper AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_ii_disbursing_officer_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_security_guard, '^[0-9]+$') AND TRY_CAST(n.es_security_guard AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_security_guard AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_utility_worker_i, '^[0-9]+$') AND TRY_CAST(n.es_utility_worker_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_utility_worker_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_vocational_school_administrator_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_vocational_school_administrator_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_vocational_school_administrator_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_vocational_school_administrator_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_vocational_school_administrator_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_vocational_school_administrator_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_vocational_school_administrator_i, '^[0-9]+$') AND TRY_CAST(n.jhs_vocational_school_administrator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_vocational_school_administrator_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_principal_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_assistant_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_assistant_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_assistant_school_principal_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_assistant_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_assistant_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_assistant_school_principal_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_assistant_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.jhs_assistant_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_assistant_school_principal_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_head_teacher_vi, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_vi AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_head_teacher_v, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_v AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_head_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_head_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_head_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_head_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_coordinator_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_coordinator_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_coordinator_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_coordinator_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_coordinator_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_coordinator_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_coordinator_i, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_coordinator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_coordinator_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_counselor_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_counselor_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_counselor_i, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_officer_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_officer_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_project_development_officer_i, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_librarian_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_librarian_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_librarian_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_librarian_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_librarian_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_librarian_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_librarian_i, '^[0-9]+$') AND TRY_CAST(n.jhs_school_librarian_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_librarian_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_accountant_i, '^[0-9]+$') AND TRY_CAST(n.jhs_accountant_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_accountant_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_cashier_i, '^[0-9]+$') AND TRY_CAST(n.jhs_cashier_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_cashier_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_supply_officer_i, '^[0-9]+$') AND TRY_CAST(n.jhs_supply_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_supply_officer_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_iii_senior_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_iii_senior_bookkeeper AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.jhs_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_bookkeeper AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_i, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_aide_vi, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_vi AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_heavy_equipment_operator_i, '^[0-9]+$') AND TRY_CAST(n.jhs_heavy_equipment_operator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_heavy_equipment_operator_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_driver_i, '^[0-9]+$') AND TRY_CAST(n.jhs_driver_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_driver_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_security_guard_i, '^[0-9]+$') AND TRY_CAST(n.jhs_security_guard_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_security_guard_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_light_equipment_operator, '^[0-9]+$') AND TRY_CAST(n.jhs_light_equipment_operator AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_light_equipment_operator AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_utility_worker_i, '^[0-9]+$') AND TRY_CAST(n.jhs_utility_worker_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_utility_worker_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_principal_iv, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_total_school_principal, '^[0-9]+$') AND TRY_CAST(n.shs_total_school_principal AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_total_school_principal AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_assistant_principal_iii, '^[0-9]+$') AND TRY_CAST(n.shs_assistant_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_assistant_principal_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_assistant_principal_ii, '^[0-9]+$') AND TRY_CAST(n.shs_assistant_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_assistant_principal_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_assistant_principal_i, '^[0-9]+$') AND TRY_CAST(n.shs_assistant_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_assistant_principal_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_head_teacher_vi, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_vi AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_head_teacher_v, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_v AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_head_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_head_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_head_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_head_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_nurse_ii, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_officer_iv, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_iv AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_officer_ii, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_librarian_iii, '^[0-9]+$') AND TRY_CAST(n.shs_school_librarian_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_librarian_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_librarian_ii, '^[0-9]+$') AND TRY_CAST(n.shs_school_librarian_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_librarian_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_librarian_i, '^[0-9]+$') AND TRY_CAST(n.shs_school_librarian_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_librarian_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_service_specialist_ii, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_service_specialist_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_service_specialist_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_service_specialist_i, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_service_specialist_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_service_specialist_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_counselor_iii, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_iii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_counselor_ii, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_counselor_i, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_accounting_i, '^[0-9]+$') AND TRY_CAST(n.shs_accounting_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_accounting_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_project_development_officer_i, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_registrar_i, '^[0-9]+$') AND TRY_CAST(n.shs_registrar_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_registrar_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_cashier_i, '^[0-9]+$') AND TRY_CAST(n.shs_cashier_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_cashier_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_supply_officer_i, '^[0-9]+$') AND TRY_CAST(n.shs_supply_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_supply_officer_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_iii_senior_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_iii_senior_bookkeeper AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_ii_disbursing_officer_ii AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_assistant_i, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_aide_vi, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_vi AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_heavy_equipment_operator_i, '^[0-9]+$') AND TRY_CAST(n.shs_heavy_equipment_operator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_heavy_equipment_operator_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_security_guard_i, '^[0-9]+$') AND TRY_CAST(n.shs_security_guard_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_security_guard_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_light_equipment_operator_i, '^[0-9]+$') AND TRY_CAST(n.shs_light_equipment_operator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_light_equipment_operator_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_utility_worker_i, '^[0-9]+$') AND TRY_CAST(n.shs_utility_worker_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_utility_worker_i AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.kinder_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_sef_province AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.kinder_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_sef_municipality_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.kinder_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.kinder_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.es_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_sef_province AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.es_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_sef_municipality_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_sef_province AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_sef_municipality_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_sef_province AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_sef_municipality_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_learning_support_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_learning_support_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_learning_support_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_administrative_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_project_development_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_project_development_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_project_development_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_project_development_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_doctor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_doctor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_doctor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_doctor_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_dentist_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_dentist_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_dentist_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_dentist_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_nurse_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_nurse_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_nurse_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_school_nurse_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_librarian_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_librarian_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_librarian_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_librarian_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_librarian_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_librarian_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_librarian_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_librarian_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_library_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_library_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_library_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_library_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_counselor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_counselor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_counselor_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_advocate_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_advocate_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_advocate_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_guidance_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_computer_technician_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_computer_technician_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_computer_technician_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.es_computer_technician_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_learning_support_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_learning_support_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_learning_support_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_administrative_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_project_development_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_project_development_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_project_development_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_project_development_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_doctor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_doctor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_doctor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_doctor_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_dentist_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_dentist_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_dentist_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_dentist_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_nurse_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_nurse_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_nurse_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_school_nurse_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_librarian_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_librarian_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_librarian_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_librarian_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_library_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_library_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_library_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_library_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_counselor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_counselor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_counselor_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_advocate_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_advocate_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_advocate_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_guidance_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_computer_technician_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_computer_technician_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_computer_technician_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.jhs_computer_technician_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_learning_support_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_learning_support_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_learning_support_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_administrative_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_project_development_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_project_development_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_project_development_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_project_development_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_doctor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_doctor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_doctor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_doctor_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_dentist_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_dentist_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_dentist_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_dentist_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_nurse_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_nurse_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_nurse_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_school_nurse_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_librarian_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_librarian_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_librarian_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_librarian_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_library_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_library_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_library_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_library_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_counselor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_counselor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_counselor_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_advocate_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_advocate_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_advocate_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_guidance_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_other_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_computer_technician_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_sef_provincial AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_computer_technician_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_sef_municipal_city AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_computer_technician_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_lgu_funding AS INT) END > n.enrollment_total
        OR CASE WHEN regexp_like(n.shs_computer_technician_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_other_funding AS INT) END > n.enrollment_total) THEN 'personnel_exceeds_enrollment' END
    ) AS quarantine_reasons,
    concat_ws(',',
      CASE WHEN CASE WHEN regexp_like(n.es_master_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_iv AS INT) END > n.enrollment_total THEN 'es_master_teacher_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.es_master_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_iii AS INT) END > n.enrollment_total THEN 'es_master_teacher_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_master_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_ii AS INT) END > n.enrollment_total THEN 'es_master_teacher_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_master_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_master_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_master_teacher_i AS INT) END > n.enrollment_total THEN 'es_master_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.es_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teacher_iii AS INT) END > n.enrollment_total THEN 'es_teacher_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teacher_ii AS INT) END > n.enrollment_total THEN 'es_teacher_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teacher_i AS INT) END > n.enrollment_total THEN 'es_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.es_sped_sned_teacher_v, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_v AS INT) END > n.enrollment_total THEN 'es_sped_sned_teacher_v' END,
      CASE WHEN CASE WHEN regexp_like(n.es_sped_sned_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_iv AS INT) END > n.enrollment_total THEN 'es_sped_sned_teacher_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.es_sped_sned_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_iii AS INT) END > n.enrollment_total THEN 'es_sped_sned_teacher_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_sped_sned_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_ii AS INT) END > n.enrollment_total THEN 'es_sped_sned_teacher_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_sped_sned_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_sped_sned_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_sped_sned_teacher_i AS INT) END > n.enrollment_total THEN 'es_sped_sned_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_instructor_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_instructor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_instructor_iii AS INT) END > n.enrollment_total THEN 'jhs_instructor_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_instructor_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_instructor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_instructor_ii AS INT) END > n.enrollment_total THEN 'jhs_instructor_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_instructor_i, '^[0-9]+$') AND TRY_CAST(n.jhs_instructor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_instructor_i AS INT) END > n.enrollment_total THEN 'jhs_instructor_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_master_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_iv AS INT) END > n.enrollment_total THEN 'jhs_master_teacher_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_master_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_iii AS INT) END > n.enrollment_total THEN 'jhs_master_teacher_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_master_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_ii AS INT) END > n.enrollment_total THEN 'jhs_master_teacher_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_master_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_master_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_master_teacher_i AS INT) END > n.enrollment_total THEN 'jhs_master_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teacher_iii AS INT) END > n.enrollment_total THEN 'jhs_teacher_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teacher_ii AS INT) END > n.enrollment_total THEN 'jhs_teacher_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teacher_i AS INT) END > n.enrollment_total THEN 'jhs_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_special_science_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_special_science_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_special_science_teacher_i AS INT) END > n.enrollment_total THEN 'jhs_special_science_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_sped_teacher_v, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_v AS INT) END > n.enrollment_total THEN 'jhs_sped_teacher_v' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_sped_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_iv AS INT) END > n.enrollment_total THEN 'jhs_sped_teacher_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_sped_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_iii AS INT) END > n.enrollment_total THEN 'jhs_sped_teacher_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_sped_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_ii AS INT) END > n.enrollment_total THEN 'jhs_sped_teacher_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_sped_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_sped_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_sped_teacher_i AS INT) END > n.enrollment_total THEN 'jhs_sped_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_master_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_iv AS INT) END > n.enrollment_total THEN 'shs_master_teacher_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_master_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_iii AS INT) END > n.enrollment_total THEN 'shs_master_teacher_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_master_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_ii AS INT) END > n.enrollment_total THEN 'shs_master_teacher_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_master_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_master_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_master_teacher_i AS INT) END > n.enrollment_total THEN 'shs_master_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.shs_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teacher_iii AS INT) END > n.enrollment_total THEN 'shs_teacher_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.shs_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teacher_ii AS INT) END > n.enrollment_total THEN 'shs_teacher_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teacher_i AS INT) END > n.enrollment_total THEN 'shs_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_special_science_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_special_science_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_special_science_teacher_i AS INT) END > n.enrollment_total THEN 'shs_special_science_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_principal_iv, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_iv AS INT) END > n.enrollment_total THEN 'es_school_principal_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_iii AS INT) END > n.enrollment_total THEN 'es_school_principal_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_ii AS INT) END > n.enrollment_total THEN 'es_school_principal_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.es_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_principal_i AS INT) END > n.enrollment_total THEN 'es_school_principal_i' END,
      CASE WHEN CASE WHEN regexp_like(n.es_head_teacher_vi, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_vi AS INT) END > n.enrollment_total THEN 'es_head_teacher_vi' END,
      CASE WHEN CASE WHEN regexp_like(n.es_head_teacher_v, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_v AS INT) END > n.enrollment_total THEN 'es_head_teacher_v' END,
      CASE WHEN CASE WHEN regexp_like(n.es_head_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_iv AS INT) END > n.enrollment_total THEN 'es_head_teacher_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.es_head_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_iii AS INT) END > n.enrollment_total THEN 'es_head_teacher_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_head_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_ii AS INT) END > n.enrollment_total THEN 'es_head_teacher_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_head_teacher_i, '^[0-9]+$') AND TRY_CAST(n.es_head_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_head_teacher_i AS INT) END > n.enrollment_total THEN 'es_head_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_coordinator_iii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_coordinator_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_coordinator_iii AS INT) END > n.enrollment_total THEN 'es_guidance_coordinator_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_coordinator_ii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_coordinator_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_coordinator_ii AS INT) END > n.enrollment_total THEN 'es_guidance_coordinator_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_coordinator_i, '^[0-9]+$') AND TRY_CAST(n.es_guidance_coordinator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_coordinator_i AS INT) END > n.enrollment_total THEN 'es_guidance_coordinator_i' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_counselor_iii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_iii AS INT) END > n.enrollment_total THEN 'es_guidance_counselor_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_counselor_ii, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_ii AS INT) END > n.enrollment_total THEN 'es_guidance_counselor_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_counselor_i, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_i AS INT) END > n.enrollment_total THEN 'es_guidance_counselor_i' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_officer_ii, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_ii AS INT) END > n.enrollment_total THEN 'es_administrative_officer_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.es_project_development_officer_i, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_i AS INT) END > n.enrollment_total THEN 'es_project_development_officer_i' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_iii_senior_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_iii_senior_bookkeeper AS INT) END > n.enrollment_total THEN 'es_administrative_assistant_iii_(senior_bookkeeper)' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_ii_disbursing_officer_ii AS INT) END > n.enrollment_total THEN 'es_administrative_assistant_ii_/_(disbursing_officer_ii)' END,
      CASE WHEN CASE WHEN regexp_like(n.es_security_guard, '^[0-9]+$') AND TRY_CAST(n.es_security_guard AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_security_guard AS INT) END > n.enrollment_total THEN 'es_security_guard' END,
      CASE WHEN CASE WHEN regexp_like(n.es_utility_worker_i, '^[0-9]+$') AND TRY_CAST(n.es_utility_worker_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_utility_worker_i AS INT) END > n.enrollment_total THEN 'es_utility_worker_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_vocational_school_administrator_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_vocational_school_administrator_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_vocational_school_administrator_iii AS INT) END > n.enrollment_total THEN 'jhs_vocational_school_administrator_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_vocational_school_administrator_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_vocational_school_administrator_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_vocational_school_administrator_ii AS INT) END > n.enrollment_total THEN 'jhs_vocational_school_administrator_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_vocational_school_administrator_i, '^[0-9]+$') AND TRY_CAST(n.jhs_vocational_school_administrator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_vocational_school_administrator_i AS INT) END > n.enrollment_total THEN 'jhs_vocational_school_administrator_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_principal_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_iv AS INT) END > n.enrollment_total THEN 'jhs_school_principal_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_iii AS INT) END > n.enrollment_total THEN 'jhs_school_principal_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_ii AS INT) END > n.enrollment_total THEN 'jhs_school_principal_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.jhs_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_principal_i AS INT) END > n.enrollment_total THEN 'jhs_school_principal_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_assistant_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_assistant_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_assistant_school_principal_iii AS INT) END > n.enrollment_total THEN 'jhs_assistant_school_principal_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_assistant_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_assistant_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_assistant_school_principal_ii AS INT) END > n.enrollment_total THEN 'jhs_assistant_school_principal_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_assistant_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.jhs_assistant_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_assistant_school_principal_i AS INT) END > n.enrollment_total THEN 'jhs_assistant_school_principal_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_head_teacher_vi, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_vi AS INT) END > n.enrollment_total THEN 'jhs_head_teacher_vi' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_head_teacher_v, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_v AS INT) END > n.enrollment_total THEN 'jhs_head_teacher_v' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_head_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_iv AS INT) END > n.enrollment_total THEN 'jhs_head_teacher_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_head_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_iii AS INT) END > n.enrollment_total THEN 'jhs_head_teacher_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_head_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_ii AS INT) END > n.enrollment_total THEN 'jhs_head_teacher_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_head_teacher_i, '^[0-9]+$') AND TRY_CAST(n.jhs_head_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_head_teacher_i AS INT) END > n.enrollment_total THEN 'jhs_head_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_coordinator_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_coordinator_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_coordinator_iii AS INT) END > n.enrollment_total THEN 'jhs_guidance_coordinator_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_coordinator_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_coordinator_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_coordinator_ii AS INT) END > n.enrollment_total THEN 'jhs_guidance_coordinator_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_coordinator_i, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_coordinator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_coordinator_i AS INT) END > n.enrollment_total THEN 'jhs_guidance_coordinator_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_counselor_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_iii AS INT) END > n.enrollment_total THEN 'jhs_guidance_counselor_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_counselor_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_ii AS INT) END > n.enrollment_total THEN 'jhs_guidance_counselor_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_counselor_i, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_i AS INT) END > n.enrollment_total THEN 'jhs_guidance_counselor_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_officer_iv, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_iv AS INT) END > n.enrollment_total THEN 'jhs_administrative_officer_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_officer_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_ii AS INT) END > n.enrollment_total THEN 'jhs_administrative_officer_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_project_development_officer_i, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_i AS INT) END > n.enrollment_total THEN 'jhs_project_development_officer_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_librarian_iii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_librarian_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_librarian_iii AS INT) END > n.enrollment_total THEN 'jhs_school_librarian_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_librarian_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_school_librarian_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_librarian_ii AS INT) END > n.enrollment_total THEN 'jhs_school_librarian_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_librarian_i, '^[0-9]+$') AND TRY_CAST(n.jhs_school_librarian_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_librarian_i AS INT) END > n.enrollment_total THEN 'jhs_school_librarian_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_accountant_i, '^[0-9]+$') AND TRY_CAST(n.jhs_accountant_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_accountant_i AS INT) END > n.enrollment_total THEN 'jhs_accountant_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_cashier_i, '^[0-9]+$') AND TRY_CAST(n.jhs_cashier_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_cashier_i AS INT) END > n.enrollment_total THEN 'jhs_cashier_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_supply_officer_i, '^[0-9]+$') AND TRY_CAST(n.jhs_supply_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_supply_officer_i AS INT) END > n.enrollment_total THEN 'jhs_supply_officer_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_iii_senior_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_iii_senior_bookkeeper AS INT) END > n.enrollment_total THEN 'jhs_administrative_assistant_iii_(senior_bookkeeper)' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.jhs_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_bookkeeper AS INT) END > n.enrollment_total THEN 'jhs_bookkeeper' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_ii AS INT) END > n.enrollment_total THEN 'jhs_administrative_assistant_ii_(disbursing_officer_ii)' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_assistant_ii_disbursing_officer_i, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_ii_disbursing_officer_i AS INT) END > n.enrollment_total THEN 'jhs_administrative_assistant_ii_(disbursing_officer_i)' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_aide_vi, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_vi AS INT) END > n.enrollment_total THEN 'jhs_administrative_aide_vi' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_heavy_equipment_operator_i, '^[0-9]+$') AND TRY_CAST(n.jhs_heavy_equipment_operator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_heavy_equipment_operator_i AS INT) END > n.enrollment_total THEN 'jhs_heavy_equipment_operator_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_driver_i, '^[0-9]+$') AND TRY_CAST(n.jhs_driver_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_driver_i AS INT) END > n.enrollment_total THEN 'jhs_driver_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_security_guard_i, '^[0-9]+$') AND TRY_CAST(n.jhs_security_guard_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_security_guard_i AS INT) END > n.enrollment_total THEN 'jhs_security_guard_i' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_light_equipment_operator, '^[0-9]+$') AND TRY_CAST(n.jhs_light_equipment_operator AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_light_equipment_operator AS INT) END > n.enrollment_total THEN 'jhs_light_equipment_operator' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_utility_worker_i, '^[0-9]+$') AND TRY_CAST(n.jhs_utility_worker_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_utility_worker_i AS INT) END > n.enrollment_total THEN 'jhs_utility_worker_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_principal_iv, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_iv AS INT) END > n.enrollment_total THEN 'shs_school_principal_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_principal_iii, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_iii AS INT) END > n.enrollment_total THEN 'shs_school_principal_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_principal_ii, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_ii AS INT) END > n.enrollment_total THEN 'shs_school_principal_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_principal_i, '^[0-9]+$') AND TRY_CAST(n.shs_school_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_principal_i AS INT) END > n.enrollment_total THEN 'shs_school_principal_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_total_school_principal, '^[0-9]+$') AND TRY_CAST(n.shs_total_school_principal AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_total_school_principal AS INT) END > n.enrollment_total THEN 'shs_total_school_principal' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_assistant_principal_iii, '^[0-9]+$') AND TRY_CAST(n.shs_assistant_principal_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_assistant_principal_iii AS INT) END > n.enrollment_total THEN 'shs_assistant_principal_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_assistant_principal_ii, '^[0-9]+$') AND TRY_CAST(n.shs_assistant_principal_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_assistant_principal_ii AS INT) END > n.enrollment_total THEN 'shs_assistant_principal_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_assistant_principal_i, '^[0-9]+$') AND TRY_CAST(n.shs_assistant_principal_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_assistant_principal_i AS INT) END > n.enrollment_total THEN 'shs_assistant_principal_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_head_teacher_vi, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_vi AS INT) END > n.enrollment_total THEN 'shs_head_teacher_vi' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_head_teacher_v, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_v AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_v AS INT) END > n.enrollment_total THEN 'shs_head_teacher_v' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_head_teacher_iv, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_iv AS INT) END > n.enrollment_total THEN 'shs_head_teacher_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_head_teacher_iii, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_iii AS INT) END > n.enrollment_total THEN 'shs_head_teacher_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_head_teacher_ii, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_ii AS INT) END > n.enrollment_total THEN 'shs_head_teacher_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_head_teacher_i, '^[0-9]+$') AND TRY_CAST(n.shs_head_teacher_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_head_teacher_i AS INT) END > n.enrollment_total THEN 'shs_head_teacher_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_nurse_ii, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_ii AS INT) END > n.enrollment_total THEN 'shs_school_nurse_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_officer_iv, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_iv AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_iv AS INT) END > n.enrollment_total THEN 'shs_administrative_officer_iv' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_officer_ii, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_ii AS INT) END > n.enrollment_total THEN 'shs_administrative_officer_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_librarian_iii, '^[0-9]+$') AND TRY_CAST(n.shs_school_librarian_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_librarian_iii AS INT) END > n.enrollment_total THEN 'shs_school_librarian_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_librarian_ii, '^[0-9]+$') AND TRY_CAST(n.shs_school_librarian_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_librarian_ii AS INT) END > n.enrollment_total THEN 'shs_school_librarian_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_librarian_i, '^[0-9]+$') AND TRY_CAST(n.shs_school_librarian_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_librarian_i AS INT) END > n.enrollment_total THEN 'shs_school_librarian_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_service_specialist_ii, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_service_specialist_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_service_specialist_ii AS INT) END > n.enrollment_total THEN 'shs_guidance_service_specialist_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_service_specialist_i, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_service_specialist_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_service_specialist_i AS INT) END > n.enrollment_total THEN 'shs_guidance_service_specialist_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_counselor_iii, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_iii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_iii AS INT) END > n.enrollment_total THEN 'shs_guidance_counselor_iii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_counselor_ii, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_ii AS INT) END > n.enrollment_total THEN 'shs_guidance_counselor_ii' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_counselor_i, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_i AS INT) END > n.enrollment_total THEN 'shs_guidance_counselor_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_accounting_i, '^[0-9]+$') AND TRY_CAST(n.shs_accounting_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_accounting_i AS INT) END > n.enrollment_total THEN 'shs_accounting_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_project_development_officer_i, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_i AS INT) END > n.enrollment_total THEN 'shs_project_development_officer_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_registrar_i, '^[0-9]+$') AND TRY_CAST(n.shs_registrar_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_registrar_i AS INT) END > n.enrollment_total THEN 'shs_registrar_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_cashier_i, '^[0-9]+$') AND TRY_CAST(n.shs_cashier_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_cashier_i AS INT) END > n.enrollment_total THEN 'shs_cashier_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_supply_officer_i, '^[0-9]+$') AND TRY_CAST(n.shs_supply_officer_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_supply_officer_i AS INT) END > n.enrollment_total THEN 'shs_supply_officer_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_assistant_iii_senior_bookkeeper, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_iii_senior_bookkeeper AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_iii_senior_bookkeeper AS INT) END > n.enrollment_total THEN 'shs_administrative_assistant_iii_(senior_bookkeeper)' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_assistant_ii_disbursing_officer_ii, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_ii_disbursing_officer_ii AS INT) END > n.enrollment_total THEN 'shs_administrative_assistant_ii_(disbursing_officer_ii)' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_assistant_i, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_i AS INT) END > n.enrollment_total THEN 'shs_administrative_assistant_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_aide_vi, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_vi AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_vi AS INT) END > n.enrollment_total THEN 'shs_administrative_aide_vi' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_heavy_equipment_operator_i, '^[0-9]+$') AND TRY_CAST(n.shs_heavy_equipment_operator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_heavy_equipment_operator_i AS INT) END > n.enrollment_total THEN 'shs_heavy_equipment_operator_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_security_guard_i, '^[0-9]+$') AND TRY_CAST(n.shs_security_guard_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_security_guard_i AS INT) END > n.enrollment_total THEN 'shs_security_guard_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_light_equipment_operator_i, '^[0-9]+$') AND TRY_CAST(n.shs_light_equipment_operator_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_light_equipment_operator_i AS INT) END > n.enrollment_total THEN 'shs_light_equipment_operator_i' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_utility_worker_i, '^[0-9]+$') AND TRY_CAST(n.shs_utility_worker_i AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_utility_worker_i AS INT) END > n.enrollment_total THEN 'shs_utility_worker_i' END,
      CASE WHEN CASE WHEN regexp_like(n.kinder_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_sef_province AS INT) END > n.enrollment_total THEN 'kinder_teachers_sef_province' END,
      CASE WHEN CASE WHEN regexp_like(n.kinder_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_sef_municipality_city AS INT) END > n.enrollment_total THEN 'kinder_teachers_sef_municipality_city' END,
      CASE WHEN CASE WHEN regexp_like(n.kinder_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_lgu_funding AS INT) END > n.enrollment_total THEN 'kinder_teachers_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.kinder_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.kinder_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.kinder_teachers_other_funding AS INT) END > n.enrollment_total THEN 'kinder_teachers_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.es_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_sef_province AS INT) END > n.enrollment_total THEN 'es_teachers_sef_province' END,
      CASE WHEN CASE WHEN regexp_like(n.es_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.es_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_sef_municipality_city AS INT) END > n.enrollment_total THEN 'es_teachers_sef_municipality_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_lgu_funding AS INT) END > n.enrollment_total THEN 'es_teachers_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_teachers_other_funding AS INT) END > n.enrollment_total THEN 'es_teachers_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_sef_province AS INT) END > n.enrollment_total THEN 'jhs_teachers_sef_province' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_sef_municipality_city AS INT) END > n.enrollment_total THEN 'jhs_teachers_sef_municipality_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_teachers_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_teachers_other_funding AS INT) END > n.enrollment_total THEN 'jhs_teachers_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_teachers_sef_province, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_sef_province AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_sef_province AS INT) END > n.enrollment_total THEN 'shs_teachers_sef_province' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_teachers_sef_municipality_city, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_sef_municipality_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_sef_municipality_city AS INT) END > n.enrollment_total THEN 'shs_teachers_sef_municipality_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_teachers_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_teachers_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_teachers_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_teachers_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_teachers_other_funding AS INT) END > n.enrollment_total THEN 'shs_teachers_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_learning_support_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_sef_provincial AS INT) END > n.enrollment_total THEN 'es_learning_support_aide_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_learning_support_aide_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_learning_support_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_lgu_funding AS INT) END > n.enrollment_total THEN 'es_learning_support_aide_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_learning_support_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_learning_support_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_learning_support_aide_other_funding AS INT) END > n.enrollment_total THEN 'es_learning_support_aide_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_sef_provincial AS INT) END > n.enrollment_total THEN 'es_administrative_officer_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_administrative_officer_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_lgu_funding AS INT) END > n.enrollment_total THEN 'es_administrative_officer_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_officer_other_funding AS INT) END > n.enrollment_total THEN 'es_administrative_officer_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_sef_provincial AS INT) END > n.enrollment_total THEN 'es_administrative_assistant_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_administrative_assistant_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_lgu_funding AS INT) END > n.enrollment_total THEN 'es_administrative_assistant_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_assistant_other_funding AS INT) END > n.enrollment_total THEN 'es_administrative_assistant_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_sef_provincial AS INT) END > n.enrollment_total THEN 'es_administrative_aide_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_administrative_aide_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_lgu_funding AS INT) END > n.enrollment_total THEN 'es_administrative_aide_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_administrative_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_administrative_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_administrative_aide_other_funding AS INT) END > n.enrollment_total THEN 'es_administrative_aide_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_project_development_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_sef_provincial AS INT) END > n.enrollment_total THEN 'es_project_development_officer_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_project_development_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_project_development_officer_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_project_development_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_lgu_funding AS INT) END > n.enrollment_total THEN 'es_project_development_officer_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_project_development_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_project_development_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_project_development_officer_other_funding AS INT) END > n.enrollment_total THEN 'es_project_development_officer_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_doctor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_sef_provincial AS INT) END > n.enrollment_total THEN 'es_school_doctor_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_doctor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_school_doctor_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_doctor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_lgu_funding AS INT) END > n.enrollment_total THEN 'es_school_doctor_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_doctor_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_doctor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_doctor_other_funding AS INT) END > n.enrollment_total THEN 'es_school_doctor_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_dentist_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_sef_provincial AS INT) END > n.enrollment_total THEN 'es_school_dentist_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_dentist_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_school_dentist_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_dentist_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_lgu_funding AS INT) END > n.enrollment_total THEN 'es_school_dentist_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_dentist_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_dentist_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_dentist_other_funding AS INT) END > n.enrollment_total THEN 'es_school_dentist_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_nurse_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_sef_provincial AS INT) END > n.enrollment_total THEN 'es_school_nurse_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_nurse_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_school_nurse_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_nurse_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_lgu_funding AS INT) END > n.enrollment_total THEN 'es_school_nurse_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_school_nurse_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_school_nurse_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_school_nurse_other_funding AS INT) END > n.enrollment_total THEN 'es_school_nurse_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_librarian_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_librarian_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_sef_provincial AS INT) END > n.enrollment_total THEN 'es_librarian_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_librarian_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_librarian_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_librarian_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_librarian_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_librarian_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_lgu_funding AS INT) END > n.enrollment_total THEN 'es_librarian_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_librarian_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_librarian_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_librarian_other_funding AS INT) END > n.enrollment_total THEN 'es_librarian_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_library_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_sef_provincial AS INT) END > n.enrollment_total THEN 'es_library_assistant_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_library_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_library_assistant_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_library_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_lgu_funding AS INT) END > n.enrollment_total THEN 'es_library_assistant_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_library_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_library_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_library_assistant_other_funding AS INT) END > n.enrollment_total THEN 'es_library_assistant_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_counselor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_sef_provincial AS INT) END > n.enrollment_total THEN 'es_guidance_counselor_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_guidance_counselor_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_counselor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_lgu_funding AS INT) END > n.enrollment_total THEN 'es_guidance_counselor_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_counselor_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_counselor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_counselor_other_funding AS INT) END > n.enrollment_total THEN 'es_guidance_counselor_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_advocate_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_sef_provincial AS INT) END > n.enrollment_total THEN 'es_guidance_advocate_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_guidance_advocate_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_advocate_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_lgu_funding AS INT) END > n.enrollment_total THEN 'es_guidance_advocate_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_advocate_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_advocate_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_advocate_other_funding AS INT) END > n.enrollment_total THEN 'es_guidance_advocate_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_sef_provincial AS INT) END > n.enrollment_total THEN 'es_guidance_assistant_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_guidance_assistant_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_lgu_funding AS INT) END > n.enrollment_total THEN 'es_guidance_assistant_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_guidance_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_guidance_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_guidance_assistant_other_funding AS INT) END > n.enrollment_total THEN 'es_guidance_assistant_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_computer_technician_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_sef_provincial AS INT) END > n.enrollment_total THEN 'es_computer_technician_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.es_computer_technician_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_sef_municipal_city AS INT) END > n.enrollment_total THEN 'es_computer_technician_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.es_computer_technician_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_lgu_funding AS INT) END > n.enrollment_total THEN 'es_computer_technician_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.es_computer_technician_other_funding, '^[0-9]+$') AND TRY_CAST(n.es_computer_technician_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.es_computer_technician_other_funding AS INT) END > n.enrollment_total THEN 'es_computer_technician_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_learning_support_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_learning_support_aide_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_learning_support_aide_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_learning_support_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_learning_support_aide_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_learning_support_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_learning_support_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_learning_support_aide_other_funding AS INT) END > n.enrollment_total THEN 'jhs_learning_support_aide_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_administrative_officer_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_administrative_officer_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_administrative_officer_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_officer_other_funding AS INT) END > n.enrollment_total THEN 'jhs_administrative_officer_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_administrative_assistant_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_administrative_assistant_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_administrative_assistant_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_assistant_other_funding AS INT) END > n.enrollment_total THEN 'jhs_administrative_assistant_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_administrative_aide_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_administrative_aide_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_administrative_aide_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_administrative_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_administrative_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_administrative_aide_other_funding AS INT) END > n.enrollment_total THEN 'jhs_administrative_aide_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_project_development_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_project_development_officer_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_project_development_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_project_development_officer_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_project_development_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_project_development_officer_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_project_development_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_project_development_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_project_development_officer_other_funding AS INT) END > n.enrollment_total THEN 'jhs_project_development_officer_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_doctor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_school_doctor_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_doctor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_school_doctor_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_doctor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_school_doctor_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_doctor_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_doctor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_doctor_other_funding AS INT) END > n.enrollment_total THEN 'jhs_school_doctor_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_dentist_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_school_dentist_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_dentist_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_school_dentist_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_dentist_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_school_dentist_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_dentist_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_dentist_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_dentist_other_funding AS INT) END > n.enrollment_total THEN 'jhs_school_dentist_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_nurse_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_school_nurse_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_nurse_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_school_nurse_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_nurse_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_school_nurse_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_school_nurse_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_school_nurse_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_school_nurse_other_funding AS INT) END > n.enrollment_total THEN 'jhs_school_nurse_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_librarian_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_librarian_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_librarian_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_librarian_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_librarian_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_librarian_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_librarian_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_librarian_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_librarian_other_funding AS INT) END > n.enrollment_total THEN 'jhs_librarian_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_library_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_library_assistant_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_library_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_library_assistant_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_library_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_library_assistant_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_library_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_library_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_library_assistant_other_funding AS INT) END > n.enrollment_total THEN 'jhs_library_assistant_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_counselor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_guidance_counselor_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_guidance_counselor_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_counselor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_guidance_counselor_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_counselor_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_counselor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_counselor_other_funding AS INT) END > n.enrollment_total THEN 'jhs_guidance_counselor_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_advocate_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_guidance_advocate_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_guidance_advocate_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_advocate_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_guidance_advocate_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_advocate_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_advocate_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_advocate_other_funding AS INT) END > n.enrollment_total THEN 'jhs_guidance_advocate_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_guidance_assistant_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_guidance_assistant_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_guidance_assistant_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_guidance_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_guidance_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_guidance_assistant_other_funding AS INT) END > n.enrollment_total THEN 'jhs_guidance_assistant_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_computer_technician_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_sef_provincial AS INT) END > n.enrollment_total THEN 'jhs_computer_technician_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_computer_technician_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_sef_municipal_city AS INT) END > n.enrollment_total THEN 'jhs_computer_technician_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_computer_technician_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_lgu_funding AS INT) END > n.enrollment_total THEN 'jhs_computer_technician_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.jhs_computer_technician_other_funding, '^[0-9]+$') AND TRY_CAST(n.jhs_computer_technician_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.jhs_computer_technician_other_funding AS INT) END > n.enrollment_total THEN 'jhs_computer_technician_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_learning_support_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_learning_support_aide_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_learning_support_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_learning_support_aide_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_learning_support_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_learning_support_aide_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_learning_support_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_learning_support_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_learning_support_aide_other_funding AS INT) END > n.enrollment_total THEN 'shs_learning_support_aide_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_administrative_officer_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_administrative_officer_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_administrative_officer_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_officer_other_funding AS INT) END > n.enrollment_total THEN 'shs_administrative_officer_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_administrative_assistant_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_administrative_assistant_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_administrative_assistant_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_assistant_other_funding AS INT) END > n.enrollment_total THEN 'shs_administrative_assistant_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_aide_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_administrative_aide_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_aide_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_administrative_aide_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_aide_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_administrative_aide_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_administrative_aide_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_administrative_aide_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_administrative_aide_other_funding AS INT) END > n.enrollment_total THEN 'shs_administrative_aide_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_project_development_officer_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_project_development_officer_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_project_development_officer_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_project_development_officer_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_project_development_officer_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_project_development_officer_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_project_development_officer_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_project_development_officer_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_project_development_officer_other_funding AS INT) END > n.enrollment_total THEN 'shs_project_development_officer_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_doctor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_school_doctor_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_doctor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_school_doctor_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_doctor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_school_doctor_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_doctor_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_doctor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_doctor_other_funding AS INT) END > n.enrollment_total THEN 'shs_school_doctor_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_dentist_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_school_dentist_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_dentist_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_school_dentist_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_dentist_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_school_dentist_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_dentist_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_dentist_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_dentist_other_funding AS INT) END > n.enrollment_total THEN 'shs_school_dentist_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_nurse_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_school_nurse_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_nurse_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_school_nurse_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_nurse_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_school_nurse_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_school_nurse_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_school_nurse_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_school_nurse_other_funding AS INT) END > n.enrollment_total THEN 'shs_school_nurse_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_librarian_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_librarian_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_librarian_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_librarian_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_librarian_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_librarian_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_librarian_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_librarian_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_librarian_other_funding AS INT) END > n.enrollment_total THEN 'shs_librarian_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_library_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_library_assistant_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_library_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_library_assistant_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_library_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_library_assistant_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_library_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_library_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_library_assistant_other_funding AS INT) END > n.enrollment_total THEN 'shs_library_assistant_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_counselor_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_guidance_counselor_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_counselor_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_guidance_counselor_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_counselor_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_guidance_counselor_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_counselor_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_counselor_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_counselor_other_funding AS INT) END > n.enrollment_total THEN 'shs_guidance_counselor_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_advocate_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_guidance_advocate_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_advocate_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_guidance_advocate_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_advocate_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_guidance_advocate_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_advocate_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_advocate_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_advocate_other_funding AS INT) END > n.enrollment_total THEN 'shs_guidance_advocate_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_assistant_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_guidance_assistant_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_assistant_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_guidance_assistant_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_assistant_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_guidance_assistant_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_guidance_assistant_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_guidance_assistant_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_guidance_assistant_other_funding AS INT) END > n.enrollment_total THEN 'shs_guidance_assistant_other_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_computer_technician_sef_provincial, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_sef_provincial AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_sef_provincial AS INT) END > n.enrollment_total THEN 'shs_computer_technician_sef_provincial' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_computer_technician_sef_municipal_city, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_sef_municipal_city AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_sef_municipal_city AS INT) END > n.enrollment_total THEN 'shs_computer_technician_sef_municipal_city' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_computer_technician_lgu_funding, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_lgu_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_lgu_funding AS INT) END > n.enrollment_total THEN 'shs_computer_technician_lgu_funding' END,
      CASE WHEN CASE WHEN regexp_like(n.shs_computer_technician_other_funding, '^[0-9]+$') AND TRY_CAST(n.shs_computer_technician_other_funding AS BIGINT) <= 2147483647 THEN TRY_CAST(n.shs_computer_technician_other_funding AS INT) END > n.enrollment_total THEN 'shs_computer_technician_other_funding' END
    ) AS enrollment_outlier_fields
  FROM normalized AS n
)
SELECT
  t.school_year,
  t.school_id,
  t.sector,
  t.school_management,
  t.offers_es,
  t.offers_jhs,
  t.offers_shs,
  t.es_master_teacher_iv,
  t.es_master_teacher_iii,
  t.es_master_teacher_ii,
  t.es_master_teacher_i,
  t.es_teacher_iii,
  t.es_teacher_ii,
  t.es_teacher_i,
  t.es_sped_sned_teacher_v,
  t.es_sped_sned_teacher_iv,
  t.es_sped_sned_teacher_iii,
  t.es_sped_sned_teacher_ii,
  t.es_sped_sned_teacher_i,
  t.jhs_instructor_iii,
  t.jhs_instructor_ii,
  t.jhs_instructor_i,
  t.jhs_master_teacher_iv,
  t.jhs_master_teacher_iii,
  t.jhs_master_teacher_ii,
  t.jhs_master_teacher_i,
  t.jhs_teacher_iii,
  t.jhs_teacher_ii,
  t.jhs_teacher_i,
  t.jhs_special_science_teacher_i,
  t.jhs_sped_teacher_v,
  t.jhs_sped_teacher_iv,
  t.jhs_sped_teacher_iii,
  t.jhs_sped_teacher_ii,
  t.jhs_sped_teacher_i,
  t.shs_master_teacher_iv,
  t.shs_master_teacher_iii,
  t.shs_master_teacher_ii,
  t.shs_master_teacher_i,
  t.shs_teacher_iii,
  t.shs_teacher_ii,
  t.shs_teacher_i,
  t.shs_special_science_teacher_i,
  t.es_school_principal_iv,
  t.es_school_principal_iii,
  t.es_school_principal_ii,
  t.es_school_principal_i,
  t.es_head_teacher_vi,
  t.es_head_teacher_v,
  t.es_head_teacher_iv,
  t.es_head_teacher_iii,
  t.es_head_teacher_ii,
  t.es_head_teacher_i,
  t.es_guidance_coordinator_iii,
  t.es_guidance_coordinator_ii,
  t.es_guidance_coordinator_i,
  t.es_guidance_counselor_iii,
  t.es_guidance_counselor_ii,
  t.es_guidance_counselor_i,
  t.es_administrative_officer_ii,
  t.es_project_development_officer_i,
  t.es_administrative_assistant_iii_senior_bookkeeper,
  t.es_administrative_assistant_ii_disbursing_officer_ii,
  t.es_security_guard,
  t.es_utility_worker_i,
  t.jhs_vocational_school_administrator_iii,
  t.jhs_vocational_school_administrator_ii,
  t.jhs_vocational_school_administrator_i,
  t.jhs_school_principal_iv,
  t.jhs_school_principal_iii,
  t.jhs_school_principal_ii,
  t.jhs_school_principal_i,
  t.jhs_assistant_school_principal_iii,
  t.jhs_assistant_school_principal_ii,
  t.jhs_assistant_school_principal_i,
  t.jhs_head_teacher_vi,
  t.jhs_head_teacher_v,
  t.jhs_head_teacher_iv,
  t.jhs_head_teacher_iii,
  t.jhs_head_teacher_ii,
  t.jhs_head_teacher_i,
  t.jhs_guidance_coordinator_iii,
  t.jhs_guidance_coordinator_ii,
  t.jhs_guidance_coordinator_i,
  t.jhs_guidance_counselor_iii,
  t.jhs_guidance_counselor_ii,
  t.jhs_guidance_counselor_i,
  t.jhs_administrative_officer_iv,
  t.jhs_administrative_officer_ii,
  t.jhs_project_development_officer_i,
  t.jhs_school_librarian_iii,
  t.jhs_school_librarian_ii,
  t.jhs_school_librarian_i,
  t.jhs_accountant_i,
  t.jhs_cashier_i,
  t.jhs_supply_officer_i,
  t.jhs_administrative_assistant_iii_senior_bookkeeper,
  t.jhs_bookkeeper,
  t.jhs_administrative_assistant_ii_disbursing_officer_ii,
  t.jhs_administrative_assistant_ii_disbursing_officer_i,
  t.jhs_administrative_aide_vi,
  t.jhs_heavy_equipment_operator_i,
  t.jhs_driver_i,
  t.jhs_security_guard_i,
  t.jhs_light_equipment_operator,
  t.jhs_utility_worker_i,
  t.shs_school_principal_iv,
  t.shs_school_principal_iii,
  t.shs_school_principal_ii,
  t.shs_school_principal_i,
  t.shs_total_school_principal,
  t.shs_assistant_principal_iii,
  t.shs_assistant_principal_ii,
  t.shs_assistant_principal_i,
  t.shs_head_teacher_vi,
  t.shs_head_teacher_v,
  t.shs_head_teacher_iv,
  t.shs_head_teacher_iii,
  t.shs_head_teacher_ii,
  t.shs_head_teacher_i,
  t.shs_school_nurse_ii,
  t.shs_administrative_officer_iv,
  t.shs_administrative_officer_ii,
  t.shs_school_librarian_iii,
  t.shs_school_librarian_ii,
  t.shs_school_librarian_i,
  t.shs_guidance_service_specialist_ii,
  t.shs_guidance_service_specialist_i,
  t.shs_guidance_counselor_iii,
  t.shs_guidance_counselor_ii,
  t.shs_guidance_counselor_i,
  t.shs_accounting_i,
  t.shs_project_development_officer_i,
  t.shs_registrar_i,
  t.shs_cashier_i,
  t.shs_supply_officer_i,
  t.shs_administrative_assistant_iii_senior_bookkeeper,
  t.shs_administrative_assistant_ii_disbursing_officer_ii,
  t.shs_administrative_assistant_i,
  t.shs_administrative_aide_vi,
  t.shs_heavy_equipment_operator_i,
  t.shs_security_guard_i,
  t.shs_light_equipment_operator_i,
  t.shs_utility_worker_i,
  t.kinder_teachers_sef_province,
  t.kinder_teachers_sef_municipality_city,
  t.kinder_teachers_lgu_funding,
  t.kinder_teachers_other_funding,
  t.es_teachers_sef_province,
  t.es_teachers_sef_municipality_city,
  t.es_teachers_lgu_funding,
  t.es_teachers_other_funding,
  t.jhs_teachers_sef_province,
  t.jhs_teachers_sef_municipality_city,
  t.jhs_teachers_lgu_funding,
  t.jhs_teachers_other_funding,
  t.shs_teachers_sef_province,
  t.shs_teachers_sef_municipality_city,
  t.shs_teachers_lgu_funding,
  t.shs_teachers_other_funding,
  t.es_learning_support_aide_sef_provincial,
  t.es_learning_support_aide_sef_municipal_city,
  t.es_learning_support_aide_lgu_funding,
  t.es_learning_support_aide_other_funding,
  t.es_administrative_officer_sef_provincial,
  t.es_administrative_officer_sef_municipal_city,
  t.es_administrative_officer_lgu_funding,
  t.es_administrative_officer_other_funding,
  t.es_administrative_assistant_sef_provincial,
  t.es_administrative_assistant_sef_municipal_city,
  t.es_administrative_assistant_lgu_funding,
  t.es_administrative_assistant_other_funding,
  t.es_administrative_aide_sef_provincial,
  t.es_administrative_aide_sef_municipal_city,
  t.es_administrative_aide_lgu_funding,
  t.es_administrative_aide_other_funding,
  t.es_project_development_officer_sef_provincial,
  t.es_project_development_officer_sef_municipal_city,
  t.es_project_development_officer_lgu_funding,
  t.es_project_development_officer_other_funding,
  t.es_school_doctor_sef_provincial,
  t.es_school_doctor_sef_municipal_city,
  t.es_school_doctor_lgu_funding,
  t.es_school_doctor_other_funding,
  t.es_school_dentist_sef_provincial,
  t.es_school_dentist_sef_municipal_city,
  t.es_school_dentist_lgu_funding,
  t.es_school_dentist_other_funding,
  t.es_school_nurse_sef_provincial,
  t.es_school_nurse_sef_municipal_city,
  t.es_school_nurse_lgu_funding,
  t.es_school_nurse_other_funding,
  t.es_librarian_sef_provincial,
  t.es_librarian_sef_municipal_city,
  t.es_librarian_lgu_funding,
  t.es_librarian_other_funding,
  t.es_library_assistant_sef_provincial,
  t.es_library_assistant_sef_municipal_city,
  t.es_library_assistant_lgu_funding,
  t.es_library_assistant_other_funding,
  t.es_guidance_counselor_sef_provincial,
  t.es_guidance_counselor_sef_municipal_city,
  t.es_guidance_counselor_lgu_funding,
  t.es_guidance_counselor_other_funding,
  t.es_guidance_advocate_sef_provincial,
  t.es_guidance_advocate_sef_municipal_city,
  t.es_guidance_advocate_lgu_funding,
  t.es_guidance_advocate_other_funding,
  t.es_guidance_assistant_sef_provincial,
  t.es_guidance_assistant_sef_municipal_city,
  t.es_guidance_assistant_lgu_funding,
  t.es_guidance_assistant_other_funding,
  t.es_computer_technician_sef_provincial,
  t.es_computer_technician_sef_municipal_city,
  t.es_computer_technician_lgu_funding,
  t.es_computer_technician_other_funding,
  t.jhs_learning_support_aide_sef_provincial,
  t.jhs_learning_support_aide_sef_municipal_city,
  t.jhs_learning_support_aide_lgu_funding,
  t.jhs_learning_support_aide_other_funding,
  t.jhs_administrative_officer_sef_provincial,
  t.jhs_administrative_officer_sef_municipal_city,
  t.jhs_administrative_officer_lgu_funding,
  t.jhs_administrative_officer_other_funding,
  t.jhs_administrative_assistant_sef_provincial,
  t.jhs_administrative_assistant_sef_municipal_city,
  t.jhs_administrative_assistant_lgu_funding,
  t.jhs_administrative_assistant_other_funding,
  t.jhs_administrative_aide_sef_provincial,
  t.jhs_administrative_aide_sef_municipal_city,
  t.jhs_administrative_aide_lgu_funding,
  t.jhs_administrative_aide_other_funding,
  t.jhs_project_development_officer_sef_provincial,
  t.jhs_project_development_officer_sef_municipal_city,
  t.jhs_project_development_officer_lgu_funding,
  t.jhs_project_development_officer_other_funding,
  t.jhs_school_doctor_sef_provincial,
  t.jhs_school_doctor_sef_municipal_city,
  t.jhs_school_doctor_lgu_funding,
  t.jhs_school_doctor_other_funding,
  t.jhs_school_dentist_sef_provincial,
  t.jhs_school_dentist_sef_municipal_city,
  t.jhs_school_dentist_lgu_funding,
  t.jhs_school_dentist_other_funding,
  t.jhs_school_nurse_sef_provincial,
  t.jhs_school_nurse_sef_municipal_city,
  t.jhs_school_nurse_lgu_funding,
  t.jhs_school_nurse_other_funding,
  t.jhs_librarian_sef_provincial,
  t.jhs_librarian_sef_municipal_city,
  t.jhs_librarian_lgu_funding,
  t.jhs_librarian_other_funding,
  t.jhs_library_assistant_sef_provincial,
  t.jhs_library_assistant_sef_municipal_city,
  t.jhs_library_assistant_lgu_funding,
  t.jhs_library_assistant_other_funding,
  t.jhs_guidance_counselor_sef_provincial,
  t.jhs_guidance_counselor_sef_municipal_city,
  t.jhs_guidance_counselor_lgu_funding,
  t.jhs_guidance_counselor_other_funding,
  t.jhs_guidance_advocate_sef_provincial,
  t.jhs_guidance_advocate_sef_municipal_city,
  t.jhs_guidance_advocate_lgu_funding,
  t.jhs_guidance_advocate_other_funding,
  t.jhs_guidance_assistant_sef_provincial,
  t.jhs_guidance_assistant_sef_municipal_city,
  t.jhs_guidance_assistant_lgu_funding,
  t.jhs_guidance_assistant_other_funding,
  t.jhs_computer_technician_sef_provincial,
  t.jhs_computer_technician_sef_municipal_city,
  t.jhs_computer_technician_lgu_funding,
  t.jhs_computer_technician_other_funding,
  t.shs_learning_support_aide_sef_provincial,
  t.shs_learning_support_aide_sef_municipal_city,
  t.shs_learning_support_aide_lgu_funding,
  t.shs_learning_support_aide_other_funding,
  t.shs_administrative_officer_sef_provincial,
  t.shs_administrative_officer_sef_municipal_city,
  t.shs_administrative_officer_lgu_funding,
  t.shs_administrative_officer_other_funding,
  t.shs_administrative_assistant_sef_provincial,
  t.shs_administrative_assistant_sef_municipal_city,
  t.shs_administrative_assistant_lgu_funding,
  t.shs_administrative_assistant_other_funding,
  t.shs_administrative_aide_sef_provincial,
  t.shs_administrative_aide_sef_municipal_city,
  t.shs_administrative_aide_lgu_funding,
  t.shs_administrative_aide_other_funding,
  t.shs_project_development_officer_sef_provincial,
  t.shs_project_development_officer_sef_municipal_city,
  t.shs_project_development_officer_lgu_funding,
  t.shs_project_development_officer_other_funding,
  t.shs_school_doctor_sef_provincial,
  t.shs_school_doctor_sef_municipal_city,
  t.shs_school_doctor_lgu_funding,
  t.shs_school_doctor_other_funding,
  t.shs_school_dentist_sef_provincial,
  t.shs_school_dentist_sef_municipal_city,
  t.shs_school_dentist_lgu_funding,
  t.shs_school_dentist_other_funding,
  t.shs_school_nurse_sef_provincial,
  t.shs_school_nurse_sef_municipal_city,
  t.shs_school_nurse_lgu_funding,
  t.shs_school_nurse_other_funding,
  t.shs_librarian_sef_provincial,
  t.shs_librarian_sef_municipal_city,
  t.shs_librarian_lgu_funding,
  t.shs_librarian_other_funding,
  t.shs_library_assistant_sef_provincial,
  t.shs_library_assistant_sef_municipal_city,
  t.shs_library_assistant_lgu_funding,
  t.shs_library_assistant_other_funding,
  t.shs_guidance_counselor_sef_provincial,
  t.shs_guidance_counselor_sef_municipal_city,
  t.shs_guidance_counselor_lgu_funding,
  t.shs_guidance_counselor_other_funding,
  t.shs_guidance_advocate_sef_provincial,
  t.shs_guidance_advocate_sef_municipal_city,
  t.shs_guidance_advocate_lgu_funding,
  t.shs_guidance_advocate_other_funding,
  t.shs_guidance_assistant_sef_provincial,
  t.shs_guidance_assistant_sef_municipal_city,
  t.shs_guidance_assistant_lgu_funding,
  t.shs_guidance_assistant_other_funding,
  t.shs_computer_technician_sef_provincial,
  t.shs_computer_technician_sef_municipal_city,
  t.shs_computer_technician_lgu_funding,
  t.shs_computer_technician_other_funding,
  COALESCE(CAST(t.shs_school_principal_i AS BIGINT), 0) + COALESCE(CAST(t.shs_school_principal_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_school_principal_iii AS BIGINT), 0) + COALESCE(CAST(t.shs_school_principal_iv AS BIGINT), 0) AS shs_school_principal_calculated,
  CASE WHEN t.shs_total_school_principal IS NULL THEN FALSE ELSE t.shs_total_school_principal <> COALESCE(CAST(t.shs_school_principal_i AS BIGINT), 0) + COALESCE(CAST(t.shs_school_principal_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_school_principal_iii AS BIGINT), 0) + COALESCE(CAST(t.shs_school_principal_iv AS BIGINT), 0) END AS shs_principal_total_discrepancy,
  COALESCE(t.shs_master_teacher_iv IS NULL, TRUE) AS shs_master_teacher_iv_unavailable,
  CASE WHEN t.sector <> 'Public' THEN 'out_of_scope' WHEN COALESCE(t.es_master_teacher_iv, t.es_master_teacher_iii, t.es_master_teacher_ii, t.es_master_teacher_i, t.es_teacher_iii, t.es_teacher_ii, t.es_teacher_i, t.es_sped_sned_teacher_v, t.es_sped_sned_teacher_iv, t.es_sped_sned_teacher_iii, t.es_sped_sned_teacher_ii, t.es_sped_sned_teacher_i, t.jhs_instructor_iii, t.jhs_instructor_ii, t.jhs_instructor_i, t.jhs_master_teacher_iv, t.jhs_master_teacher_iii, t.jhs_master_teacher_ii, t.jhs_master_teacher_i, t.jhs_teacher_iii, t.jhs_teacher_ii, t.jhs_teacher_i, t.jhs_special_science_teacher_i, t.jhs_sped_teacher_v, t.jhs_sped_teacher_iv, t.jhs_sped_teacher_iii, t.jhs_sped_teacher_ii, t.jhs_sped_teacher_i, t.shs_master_teacher_iv, t.shs_master_teacher_iii, t.shs_master_teacher_ii, t.shs_master_teacher_i, t.shs_teacher_iii, t.shs_teacher_ii, t.shs_teacher_i, t.shs_special_science_teacher_i, t.es_school_principal_iv, t.es_school_principal_iii, t.es_school_principal_ii, t.es_school_principal_i, t.es_head_teacher_vi, t.es_head_teacher_v, t.es_head_teacher_iv, t.es_head_teacher_iii, t.es_head_teacher_ii, t.es_head_teacher_i, t.es_guidance_coordinator_iii, t.es_guidance_coordinator_ii, t.es_guidance_coordinator_i, t.es_guidance_counselor_iii, t.es_guidance_counselor_ii, t.es_guidance_counselor_i, t.es_administrative_officer_ii, t.es_project_development_officer_i, t.es_administrative_assistant_iii_senior_bookkeeper, t.es_administrative_assistant_ii_disbursing_officer_ii, t.es_security_guard, t.es_utility_worker_i, t.jhs_vocational_school_administrator_iii, t.jhs_vocational_school_administrator_ii, t.jhs_vocational_school_administrator_i, t.jhs_school_principal_iv, t.jhs_school_principal_iii, t.jhs_school_principal_ii, t.jhs_school_principal_i, t.jhs_assistant_school_principal_iii, t.jhs_assistant_school_principal_ii, t.jhs_assistant_school_principal_i, t.jhs_head_teacher_vi, t.jhs_head_teacher_v, t.jhs_head_teacher_iv, t.jhs_head_teacher_iii, t.jhs_head_teacher_ii, t.jhs_head_teacher_i, t.jhs_guidance_coordinator_iii, t.jhs_guidance_coordinator_ii, t.jhs_guidance_coordinator_i, t.jhs_guidance_counselor_iii, t.jhs_guidance_counselor_ii, t.jhs_guidance_counselor_i, t.jhs_administrative_officer_iv, t.jhs_administrative_officer_ii, t.jhs_project_development_officer_i, t.jhs_school_librarian_iii, t.jhs_school_librarian_ii, t.jhs_school_librarian_i, t.jhs_accountant_i, t.jhs_cashier_i, t.jhs_supply_officer_i, t.jhs_administrative_assistant_iii_senior_bookkeeper, t.jhs_bookkeeper, t.jhs_administrative_assistant_ii_disbursing_officer_ii, t.jhs_administrative_assistant_ii_disbursing_officer_i, t.jhs_administrative_aide_vi, t.jhs_heavy_equipment_operator_i, t.jhs_driver_i, t.jhs_security_guard_i, t.jhs_light_equipment_operator, t.jhs_utility_worker_i, t.shs_school_principal_iv, t.shs_school_principal_iii, t.shs_school_principal_ii, t.shs_school_principal_i, t.shs_total_school_principal, t.shs_assistant_principal_iii, t.shs_assistant_principal_ii, t.shs_assistant_principal_i, t.shs_head_teacher_vi, t.shs_head_teacher_v, t.shs_head_teacher_iv, t.shs_head_teacher_iii, t.shs_head_teacher_ii, t.shs_head_teacher_i, t.shs_school_nurse_ii, t.shs_administrative_officer_iv, t.shs_administrative_officer_ii, t.shs_school_librarian_iii, t.shs_school_librarian_ii, t.shs_school_librarian_i, t.shs_guidance_service_specialist_ii, t.shs_guidance_service_specialist_i, t.shs_guidance_counselor_iii, t.shs_guidance_counselor_ii, t.shs_guidance_counselor_i, t.shs_accounting_i, t.shs_project_development_officer_i, t.shs_registrar_i, t.shs_cashier_i, t.shs_supply_officer_i, t.shs_administrative_assistant_iii_senior_bookkeeper, t.shs_administrative_assistant_ii_disbursing_officer_ii, t.shs_administrative_assistant_i, t.shs_administrative_aide_vi, t.shs_heavy_equipment_operator_i, t.shs_security_guard_i, t.shs_light_equipment_operator_i, t.shs_utility_worker_i, t.kinder_teachers_sef_province, t.kinder_teachers_sef_municipality_city, t.kinder_teachers_lgu_funding, t.kinder_teachers_other_funding, t.es_teachers_sef_province, t.es_teachers_sef_municipality_city, t.es_teachers_lgu_funding, t.es_teachers_other_funding, t.jhs_teachers_sef_province, t.jhs_teachers_sef_municipality_city, t.jhs_teachers_lgu_funding, t.jhs_teachers_other_funding, t.shs_teachers_sef_province, t.shs_teachers_sef_municipality_city, t.shs_teachers_lgu_funding, t.shs_teachers_other_funding, t.es_learning_support_aide_sef_provincial, t.es_learning_support_aide_sef_municipal_city, t.es_learning_support_aide_lgu_funding, t.es_learning_support_aide_other_funding, t.es_administrative_officer_sef_provincial, t.es_administrative_officer_sef_municipal_city, t.es_administrative_officer_lgu_funding, t.es_administrative_officer_other_funding, t.es_administrative_assistant_sef_provincial, t.es_administrative_assistant_sef_municipal_city, t.es_administrative_assistant_lgu_funding, t.es_administrative_assistant_other_funding, t.es_administrative_aide_sef_provincial, t.es_administrative_aide_sef_municipal_city, t.es_administrative_aide_lgu_funding, t.es_administrative_aide_other_funding, t.es_project_development_officer_sef_provincial, t.es_project_development_officer_sef_municipal_city, t.es_project_development_officer_lgu_funding, t.es_project_development_officer_other_funding, t.es_school_doctor_sef_provincial, t.es_school_doctor_sef_municipal_city, t.es_school_doctor_lgu_funding, t.es_school_doctor_other_funding, t.es_school_dentist_sef_provincial, t.es_school_dentist_sef_municipal_city, t.es_school_dentist_lgu_funding, t.es_school_dentist_other_funding, t.es_school_nurse_sef_provincial, t.es_school_nurse_sef_municipal_city, t.es_school_nurse_lgu_funding, t.es_school_nurse_other_funding, t.es_librarian_sef_provincial, t.es_librarian_sef_municipal_city, t.es_librarian_lgu_funding, t.es_librarian_other_funding, t.es_library_assistant_sef_provincial, t.es_library_assistant_sef_municipal_city, t.es_library_assistant_lgu_funding, t.es_library_assistant_other_funding, t.es_guidance_counselor_sef_provincial, t.es_guidance_counselor_sef_municipal_city, t.es_guidance_counselor_lgu_funding, t.es_guidance_counselor_other_funding, t.es_guidance_advocate_sef_provincial, t.es_guidance_advocate_sef_municipal_city, t.es_guidance_advocate_lgu_funding, t.es_guidance_advocate_other_funding, t.es_guidance_assistant_sef_provincial, t.es_guidance_assistant_sef_municipal_city, t.es_guidance_assistant_lgu_funding, t.es_guidance_assistant_other_funding, t.es_computer_technician_sef_provincial, t.es_computer_technician_sef_municipal_city, t.es_computer_technician_lgu_funding, t.es_computer_technician_other_funding, t.jhs_learning_support_aide_sef_provincial, t.jhs_learning_support_aide_sef_municipal_city, t.jhs_learning_support_aide_lgu_funding, t.jhs_learning_support_aide_other_funding, t.jhs_administrative_officer_sef_provincial, t.jhs_administrative_officer_sef_municipal_city, t.jhs_administrative_officer_lgu_funding, t.jhs_administrative_officer_other_funding, t.jhs_administrative_assistant_sef_provincial, t.jhs_administrative_assistant_sef_municipal_city, t.jhs_administrative_assistant_lgu_funding, t.jhs_administrative_assistant_other_funding, t.jhs_administrative_aide_sef_provincial, t.jhs_administrative_aide_sef_municipal_city, t.jhs_administrative_aide_lgu_funding, t.jhs_administrative_aide_other_funding, t.jhs_project_development_officer_sef_provincial, t.jhs_project_development_officer_sef_municipal_city, t.jhs_project_development_officer_lgu_funding, t.jhs_project_development_officer_other_funding, t.jhs_school_doctor_sef_provincial, t.jhs_school_doctor_sef_municipal_city, t.jhs_school_doctor_lgu_funding, t.jhs_school_doctor_other_funding, t.jhs_school_dentist_sef_provincial, t.jhs_school_dentist_sef_municipal_city, t.jhs_school_dentist_lgu_funding, t.jhs_school_dentist_other_funding, t.jhs_school_nurse_sef_provincial, t.jhs_school_nurse_sef_municipal_city, t.jhs_school_nurse_lgu_funding, t.jhs_school_nurse_other_funding, t.jhs_librarian_sef_provincial, t.jhs_librarian_sef_municipal_city, t.jhs_librarian_lgu_funding, t.jhs_librarian_other_funding, t.jhs_library_assistant_sef_provincial, t.jhs_library_assistant_sef_municipal_city, t.jhs_library_assistant_lgu_funding, t.jhs_library_assistant_other_funding, t.jhs_guidance_counselor_sef_provincial, t.jhs_guidance_counselor_sef_municipal_city, t.jhs_guidance_counselor_lgu_funding, t.jhs_guidance_counselor_other_funding, t.jhs_guidance_advocate_sef_provincial, t.jhs_guidance_advocate_sef_municipal_city, t.jhs_guidance_advocate_lgu_funding, t.jhs_guidance_advocate_other_funding, t.jhs_guidance_assistant_sef_provincial, t.jhs_guidance_assistant_sef_municipal_city, t.jhs_guidance_assistant_lgu_funding, t.jhs_guidance_assistant_other_funding, t.jhs_computer_technician_sef_provincial, t.jhs_computer_technician_sef_municipal_city, t.jhs_computer_technician_lgu_funding, t.jhs_computer_technician_other_funding, t.shs_learning_support_aide_sef_provincial, t.shs_learning_support_aide_sef_municipal_city, t.shs_learning_support_aide_lgu_funding, t.shs_learning_support_aide_other_funding, t.shs_administrative_officer_sef_provincial, t.shs_administrative_officer_sef_municipal_city, t.shs_administrative_officer_lgu_funding, t.shs_administrative_officer_other_funding, t.shs_administrative_assistant_sef_provincial, t.shs_administrative_assistant_sef_municipal_city, t.shs_administrative_assistant_lgu_funding, t.shs_administrative_assistant_other_funding, t.shs_administrative_aide_sef_provincial, t.shs_administrative_aide_sef_municipal_city, t.shs_administrative_aide_lgu_funding, t.shs_administrative_aide_other_funding, t.shs_project_development_officer_sef_provincial, t.shs_project_development_officer_sef_municipal_city, t.shs_project_development_officer_lgu_funding, t.shs_project_development_officer_other_funding, t.shs_school_doctor_sef_provincial, t.shs_school_doctor_sef_municipal_city, t.shs_school_doctor_lgu_funding, t.shs_school_doctor_other_funding, t.shs_school_dentist_sef_provincial, t.shs_school_dentist_sef_municipal_city, t.shs_school_dentist_lgu_funding, t.shs_school_dentist_other_funding, t.shs_school_nurse_sef_provincial, t.shs_school_nurse_sef_municipal_city, t.shs_school_nurse_lgu_funding, t.shs_school_nurse_other_funding, t.shs_librarian_sef_provincial, t.shs_librarian_sef_municipal_city, t.shs_librarian_lgu_funding, t.shs_librarian_other_funding, t.shs_library_assistant_sef_provincial, t.shs_library_assistant_sef_municipal_city, t.shs_library_assistant_lgu_funding, t.shs_library_assistant_other_funding, t.shs_guidance_counselor_sef_provincial, t.shs_guidance_counselor_sef_municipal_city, t.shs_guidance_counselor_lgu_funding, t.shs_guidance_counselor_other_funding, t.shs_guidance_advocate_sef_provincial, t.shs_guidance_advocate_sef_municipal_city, t.shs_guidance_advocate_lgu_funding, t.shs_guidance_advocate_other_funding, t.shs_guidance_assistant_sef_provincial, t.shs_guidance_assistant_sef_municipal_city, t.shs_guidance_assistant_lgu_funding, t.shs_guidance_assistant_other_funding, t.shs_computer_technician_sef_provincial, t.shs_computer_technician_sef_municipal_city, t.shs_computer_technician_lgu_funding, t.shs_computer_technician_other_funding) IS NULL THEN 'no_counts' WHEN COALESCE(CAST(t.es_master_teacher_iv AS BIGINT), 0) + COALESCE(CAST(t.es_master_teacher_iii AS BIGINT), 0) + COALESCE(CAST(t.es_master_teacher_ii AS BIGINT), 0) + COALESCE(CAST(t.es_master_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.es_teacher_iii AS BIGINT), 0) + COALESCE(CAST(t.es_teacher_ii AS BIGINT), 0) + COALESCE(CAST(t.es_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.es_sped_sned_teacher_v AS BIGINT), 0) + COALESCE(CAST(t.es_sped_sned_teacher_iv AS BIGINT), 0) + COALESCE(CAST(t.es_sped_sned_teacher_iii AS BIGINT), 0) + COALESCE(CAST(t.es_sped_sned_teacher_ii AS BIGINT), 0) + COALESCE(CAST(t.es_sped_sned_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_instructor_iii AS BIGINT), 0) + COALESCE(CAST(t.jhs_instructor_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_instructor_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_master_teacher_iv AS BIGINT), 0) + COALESCE(CAST(t.jhs_master_teacher_iii AS BIGINT), 0) + COALESCE(CAST(t.jhs_master_teacher_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_master_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_teacher_iii AS BIGINT), 0) + COALESCE(CAST(t.jhs_teacher_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_special_science_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_sped_teacher_v AS BIGINT), 0) + COALESCE(CAST(t.jhs_sped_teacher_iv AS BIGINT), 0) + COALESCE(CAST(t.jhs_sped_teacher_iii AS BIGINT), 0) + COALESCE(CAST(t.jhs_sped_teacher_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_sped_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.shs_master_teacher_iv AS BIGINT), 0) + COALESCE(CAST(t.shs_master_teacher_iii AS BIGINT), 0) + COALESCE(CAST(t.shs_master_teacher_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_master_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.shs_teacher_iii AS BIGINT), 0) + COALESCE(CAST(t.shs_teacher_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.shs_special_science_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.es_school_principal_iv AS BIGINT), 0) + COALESCE(CAST(t.es_school_principal_iii AS BIGINT), 0) + COALESCE(CAST(t.es_school_principal_ii AS BIGINT), 0) + COALESCE(CAST(t.es_school_principal_i AS BIGINT), 0) + COALESCE(CAST(t.es_head_teacher_vi AS BIGINT), 0) + COALESCE(CAST(t.es_head_teacher_v AS BIGINT), 0) + COALESCE(CAST(t.es_head_teacher_iv AS BIGINT), 0) + COALESCE(CAST(t.es_head_teacher_iii AS BIGINT), 0) + COALESCE(CAST(t.es_head_teacher_ii AS BIGINT), 0) + COALESCE(CAST(t.es_head_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_coordinator_iii AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_coordinator_ii AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_coordinator_i AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_counselor_iii AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_counselor_ii AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_counselor_i AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_officer_ii AS BIGINT), 0) + COALESCE(CAST(t.es_project_development_officer_i AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_assistant_iii_senior_bookkeeper AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_assistant_ii_disbursing_officer_ii AS BIGINT), 0) + COALESCE(CAST(t.es_security_guard AS BIGINT), 0) + COALESCE(CAST(t.es_utility_worker_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_vocational_school_administrator_iii AS BIGINT), 0) + COALESCE(CAST(t.jhs_vocational_school_administrator_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_vocational_school_administrator_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_principal_iv AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_principal_iii AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_principal_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_principal_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_assistant_school_principal_iii AS BIGINT), 0) + COALESCE(CAST(t.jhs_assistant_school_principal_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_assistant_school_principal_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_head_teacher_vi AS BIGINT), 0) + COALESCE(CAST(t.jhs_head_teacher_v AS BIGINT), 0) + COALESCE(CAST(t.jhs_head_teacher_iv AS BIGINT), 0) + COALESCE(CAST(t.jhs_head_teacher_iii AS BIGINT), 0) + COALESCE(CAST(t.jhs_head_teacher_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_head_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_coordinator_iii AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_coordinator_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_coordinator_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_counselor_iii AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_counselor_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_counselor_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_officer_iv AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_officer_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_project_development_officer_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_librarian_iii AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_librarian_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_librarian_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_accountant_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_cashier_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_supply_officer_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_assistant_iii_senior_bookkeeper AS BIGINT), 0) + COALESCE(CAST(t.jhs_bookkeeper AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_assistant_ii_disbursing_officer_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_aide_vi AS BIGINT), 0) + COALESCE(CAST(t.jhs_heavy_equipment_operator_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_driver_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_security_guard_i AS BIGINT), 0) + COALESCE(CAST(t.jhs_light_equipment_operator AS BIGINT), 0) + COALESCE(CAST(t.jhs_utility_worker_i AS BIGINT), 0) + COALESCE(CAST(t.shs_school_principal_iv AS BIGINT), 0) + COALESCE(CAST(t.shs_school_principal_iii AS BIGINT), 0) + COALESCE(CAST(t.shs_school_principal_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_school_principal_i AS BIGINT), 0) + COALESCE(CAST(t.shs_total_school_principal AS BIGINT), 0) + COALESCE(CAST(t.shs_assistant_principal_iii AS BIGINT), 0) + COALESCE(CAST(t.shs_assistant_principal_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_assistant_principal_i AS BIGINT), 0) + COALESCE(CAST(t.shs_head_teacher_vi AS BIGINT), 0) + COALESCE(CAST(t.shs_head_teacher_v AS BIGINT), 0) + COALESCE(CAST(t.shs_head_teacher_iv AS BIGINT), 0) + COALESCE(CAST(t.shs_head_teacher_iii AS BIGINT), 0) + COALESCE(CAST(t.shs_head_teacher_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_head_teacher_i AS BIGINT), 0) + COALESCE(CAST(t.shs_school_nurse_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_officer_iv AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_officer_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_school_librarian_iii AS BIGINT), 0) + COALESCE(CAST(t.shs_school_librarian_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_school_librarian_i AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_service_specialist_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_service_specialist_i AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_counselor_iii AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_counselor_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_counselor_i AS BIGINT), 0) + COALESCE(CAST(t.shs_accounting_i AS BIGINT), 0) + COALESCE(CAST(t.shs_project_development_officer_i AS BIGINT), 0) + COALESCE(CAST(t.shs_registrar_i AS BIGINT), 0) + COALESCE(CAST(t.shs_cashier_i AS BIGINT), 0) + COALESCE(CAST(t.shs_supply_officer_i AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_assistant_iii_senior_bookkeeper AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_assistant_ii_disbursing_officer_ii AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_assistant_i AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_aide_vi AS BIGINT), 0) + COALESCE(CAST(t.shs_heavy_equipment_operator_i AS BIGINT), 0) + COALESCE(CAST(t.shs_security_guard_i AS BIGINT), 0) + COALESCE(CAST(t.shs_light_equipment_operator_i AS BIGINT), 0) + COALESCE(CAST(t.shs_utility_worker_i AS BIGINT), 0) + COALESCE(CAST(t.kinder_teachers_sef_province AS BIGINT), 0) + COALESCE(CAST(t.kinder_teachers_sef_municipality_city AS BIGINT), 0) + COALESCE(CAST(t.kinder_teachers_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.kinder_teachers_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_teachers_sef_province AS BIGINT), 0) + COALESCE(CAST(t.es_teachers_sef_municipality_city AS BIGINT), 0) + COALESCE(CAST(t.es_teachers_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_teachers_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_teachers_sef_province AS BIGINT), 0) + COALESCE(CAST(t.jhs_teachers_sef_municipality_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_teachers_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_teachers_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_teachers_sef_province AS BIGINT), 0) + COALESCE(CAST(t.shs_teachers_sef_municipality_city AS BIGINT), 0) + COALESCE(CAST(t.shs_teachers_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_teachers_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_learning_support_aide_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_learning_support_aide_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_learning_support_aide_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_learning_support_aide_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_officer_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_officer_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_officer_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_officer_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_assistant_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_assistant_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_assistant_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_assistant_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_aide_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_aide_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_aide_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_administrative_aide_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_project_development_officer_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_project_development_officer_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_project_development_officer_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_project_development_officer_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_school_doctor_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_school_doctor_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_school_doctor_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_school_doctor_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_school_dentist_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_school_dentist_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_school_dentist_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_school_dentist_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_school_nurse_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_school_nurse_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_school_nurse_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_school_nurse_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_librarian_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_librarian_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_librarian_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_librarian_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_library_assistant_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_library_assistant_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_library_assistant_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_library_assistant_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_counselor_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_counselor_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_counselor_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_counselor_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_advocate_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_advocate_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_advocate_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_advocate_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_assistant_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_assistant_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_assistant_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_guidance_assistant_other_funding AS BIGINT), 0) + COALESCE(CAST(t.es_computer_technician_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.es_computer_technician_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.es_computer_technician_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.es_computer_technician_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_learning_support_aide_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_learning_support_aide_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_learning_support_aide_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_learning_support_aide_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_officer_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_officer_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_officer_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_officer_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_assistant_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_assistant_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_assistant_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_assistant_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_aide_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_aide_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_aide_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_administrative_aide_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_project_development_officer_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_project_development_officer_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_project_development_officer_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_project_development_officer_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_doctor_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_doctor_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_doctor_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_doctor_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_dentist_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_dentist_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_dentist_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_dentist_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_nurse_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_nurse_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_nurse_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_school_nurse_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_librarian_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_librarian_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_librarian_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_librarian_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_library_assistant_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_library_assistant_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_library_assistant_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_library_assistant_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_counselor_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_counselor_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_counselor_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_counselor_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_advocate_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_advocate_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_advocate_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_advocate_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_assistant_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_assistant_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_assistant_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_guidance_assistant_other_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_computer_technician_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.jhs_computer_technician_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.jhs_computer_technician_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.jhs_computer_technician_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_learning_support_aide_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_learning_support_aide_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_learning_support_aide_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_learning_support_aide_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_officer_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_officer_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_officer_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_officer_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_assistant_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_assistant_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_assistant_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_assistant_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_aide_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_aide_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_aide_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_administrative_aide_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_project_development_officer_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_project_development_officer_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_project_development_officer_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_project_development_officer_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_school_doctor_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_school_doctor_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_school_doctor_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_school_doctor_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_school_dentist_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_school_dentist_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_school_dentist_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_school_dentist_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_school_nurse_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_school_nurse_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_school_nurse_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_school_nurse_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_librarian_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_librarian_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_librarian_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_librarian_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_library_assistant_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_library_assistant_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_library_assistant_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_library_assistant_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_counselor_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_counselor_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_counselor_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_counselor_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_advocate_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_advocate_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_advocate_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_advocate_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_assistant_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_assistant_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_assistant_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_guidance_assistant_other_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_computer_technician_sef_provincial AS BIGINT), 0) + COALESCE(CAST(t.shs_computer_technician_sef_municipal_city AS BIGINT), 0) + COALESCE(CAST(t.shs_computer_technician_lgu_funding AS BIGINT), 0) + COALESCE(CAST(t.shs_computer_technician_other_funding AS BIGINT), 0) = 0 THEN 'all_zero' ELSE 'has_personnel' END AS personnel_reporting_status,
  t.enrollment_total,
  t.enrollment_outlier_fields,
  t.quarantine_reasons,
  t.batch_id,
  t.delivery_version,
  t.schema_version,
  t.source_sha256,
  t.source_row_number,
  session.silver_run_id AS run_id,
  session.silver_cleaned_at_utc AS cleaned_at_utc,
  session.silver_code_revision AS code_revision
FROM typed AS t;

CREATE OR REPLACE TABLE edu_access.`03-silver`.deped_personnel_clean_candidate USING DELTA AS
SELECT
  school_year,
  school_id,
  sector,
  school_management,
  offers_es,
  offers_jhs,
  offers_shs,
  es_master_teacher_iv,
  es_master_teacher_iii,
  es_master_teacher_ii,
  es_master_teacher_i,
  es_teacher_iii,
  es_teacher_ii,
  es_teacher_i,
  es_sped_sned_teacher_v,
  es_sped_sned_teacher_iv,
  es_sped_sned_teacher_iii,
  es_sped_sned_teacher_ii,
  es_sped_sned_teacher_i,
  jhs_instructor_iii,
  jhs_instructor_ii,
  jhs_instructor_i,
  jhs_master_teacher_iv,
  jhs_master_teacher_iii,
  jhs_master_teacher_ii,
  jhs_master_teacher_i,
  jhs_teacher_iii,
  jhs_teacher_ii,
  jhs_teacher_i,
  jhs_special_science_teacher_i,
  jhs_sped_teacher_v,
  jhs_sped_teacher_iv,
  jhs_sped_teacher_iii,
  jhs_sped_teacher_ii,
  jhs_sped_teacher_i,
  shs_master_teacher_iv,
  shs_master_teacher_iii,
  shs_master_teacher_ii,
  shs_master_teacher_i,
  shs_teacher_iii,
  shs_teacher_ii,
  shs_teacher_i,
  shs_special_science_teacher_i,
  es_school_principal_iv,
  es_school_principal_iii,
  es_school_principal_ii,
  es_school_principal_i,
  es_head_teacher_vi,
  es_head_teacher_v,
  es_head_teacher_iv,
  es_head_teacher_iii,
  es_head_teacher_ii,
  es_head_teacher_i,
  es_guidance_coordinator_iii,
  es_guidance_coordinator_ii,
  es_guidance_coordinator_i,
  es_guidance_counselor_iii,
  es_guidance_counselor_ii,
  es_guidance_counselor_i,
  es_administrative_officer_ii,
  es_project_development_officer_i,
  es_administrative_assistant_iii_senior_bookkeeper,
  es_administrative_assistant_ii_disbursing_officer_ii,
  es_security_guard,
  es_utility_worker_i,
  jhs_vocational_school_administrator_iii,
  jhs_vocational_school_administrator_ii,
  jhs_vocational_school_administrator_i,
  jhs_school_principal_iv,
  jhs_school_principal_iii,
  jhs_school_principal_ii,
  jhs_school_principal_i,
  jhs_assistant_school_principal_iii,
  jhs_assistant_school_principal_ii,
  jhs_assistant_school_principal_i,
  jhs_head_teacher_vi,
  jhs_head_teacher_v,
  jhs_head_teacher_iv,
  jhs_head_teacher_iii,
  jhs_head_teacher_ii,
  jhs_head_teacher_i,
  jhs_guidance_coordinator_iii,
  jhs_guidance_coordinator_ii,
  jhs_guidance_coordinator_i,
  jhs_guidance_counselor_iii,
  jhs_guidance_counselor_ii,
  jhs_guidance_counselor_i,
  jhs_administrative_officer_iv,
  jhs_administrative_officer_ii,
  jhs_project_development_officer_i,
  jhs_school_librarian_iii,
  jhs_school_librarian_ii,
  jhs_school_librarian_i,
  jhs_accountant_i,
  jhs_cashier_i,
  jhs_supply_officer_i,
  jhs_administrative_assistant_iii_senior_bookkeeper,
  jhs_bookkeeper,
  jhs_administrative_assistant_ii_disbursing_officer_ii,
  jhs_administrative_assistant_ii_disbursing_officer_i,
  jhs_administrative_aide_vi,
  jhs_heavy_equipment_operator_i,
  jhs_driver_i,
  jhs_security_guard_i,
  jhs_light_equipment_operator,
  jhs_utility_worker_i,
  shs_school_principal_iv,
  shs_school_principal_iii,
  shs_school_principal_ii,
  shs_school_principal_i,
  shs_total_school_principal,
  shs_assistant_principal_iii,
  shs_assistant_principal_ii,
  shs_assistant_principal_i,
  shs_head_teacher_vi,
  shs_head_teacher_v,
  shs_head_teacher_iv,
  shs_head_teacher_iii,
  shs_head_teacher_ii,
  shs_head_teacher_i,
  shs_school_nurse_ii,
  shs_administrative_officer_iv,
  shs_administrative_officer_ii,
  shs_school_librarian_iii,
  shs_school_librarian_ii,
  shs_school_librarian_i,
  shs_guidance_service_specialist_ii,
  shs_guidance_service_specialist_i,
  shs_guidance_counselor_iii,
  shs_guidance_counselor_ii,
  shs_guidance_counselor_i,
  shs_accounting_i,
  shs_project_development_officer_i,
  shs_registrar_i,
  shs_cashier_i,
  shs_supply_officer_i,
  shs_administrative_assistant_iii_senior_bookkeeper,
  shs_administrative_assistant_ii_disbursing_officer_ii,
  shs_administrative_assistant_i,
  shs_administrative_aide_vi,
  shs_heavy_equipment_operator_i,
  shs_security_guard_i,
  shs_light_equipment_operator_i,
  shs_utility_worker_i,
  kinder_teachers_sef_province,
  kinder_teachers_sef_municipality_city,
  kinder_teachers_lgu_funding,
  kinder_teachers_other_funding,
  es_teachers_sef_province,
  es_teachers_sef_municipality_city,
  es_teachers_lgu_funding,
  es_teachers_other_funding,
  jhs_teachers_sef_province,
  jhs_teachers_sef_municipality_city,
  jhs_teachers_lgu_funding,
  jhs_teachers_other_funding,
  shs_teachers_sef_province,
  shs_teachers_sef_municipality_city,
  shs_teachers_lgu_funding,
  shs_teachers_other_funding,
  es_learning_support_aide_sef_provincial,
  es_learning_support_aide_sef_municipal_city,
  es_learning_support_aide_lgu_funding,
  es_learning_support_aide_other_funding,
  es_administrative_officer_sef_provincial,
  es_administrative_officer_sef_municipal_city,
  es_administrative_officer_lgu_funding,
  es_administrative_officer_other_funding,
  es_administrative_assistant_sef_provincial,
  es_administrative_assistant_sef_municipal_city,
  es_administrative_assistant_lgu_funding,
  es_administrative_assistant_other_funding,
  es_administrative_aide_sef_provincial,
  es_administrative_aide_sef_municipal_city,
  es_administrative_aide_lgu_funding,
  es_administrative_aide_other_funding,
  es_project_development_officer_sef_provincial,
  es_project_development_officer_sef_municipal_city,
  es_project_development_officer_lgu_funding,
  es_project_development_officer_other_funding,
  es_school_doctor_sef_provincial,
  es_school_doctor_sef_municipal_city,
  es_school_doctor_lgu_funding,
  es_school_doctor_other_funding,
  es_school_dentist_sef_provincial,
  es_school_dentist_sef_municipal_city,
  es_school_dentist_lgu_funding,
  es_school_dentist_other_funding,
  es_school_nurse_sef_provincial,
  es_school_nurse_sef_municipal_city,
  es_school_nurse_lgu_funding,
  es_school_nurse_other_funding,
  es_librarian_sef_provincial,
  es_librarian_sef_municipal_city,
  es_librarian_lgu_funding,
  es_librarian_other_funding,
  es_library_assistant_sef_provincial,
  es_library_assistant_sef_municipal_city,
  es_library_assistant_lgu_funding,
  es_library_assistant_other_funding,
  es_guidance_counselor_sef_provincial,
  es_guidance_counselor_sef_municipal_city,
  es_guidance_counselor_lgu_funding,
  es_guidance_counselor_other_funding,
  es_guidance_advocate_sef_provincial,
  es_guidance_advocate_sef_municipal_city,
  es_guidance_advocate_lgu_funding,
  es_guidance_advocate_other_funding,
  es_guidance_assistant_sef_provincial,
  es_guidance_assistant_sef_municipal_city,
  es_guidance_assistant_lgu_funding,
  es_guidance_assistant_other_funding,
  es_computer_technician_sef_provincial,
  es_computer_technician_sef_municipal_city,
  es_computer_technician_lgu_funding,
  es_computer_technician_other_funding,
  jhs_learning_support_aide_sef_provincial,
  jhs_learning_support_aide_sef_municipal_city,
  jhs_learning_support_aide_lgu_funding,
  jhs_learning_support_aide_other_funding,
  jhs_administrative_officer_sef_provincial,
  jhs_administrative_officer_sef_municipal_city,
  jhs_administrative_officer_lgu_funding,
  jhs_administrative_officer_other_funding,
  jhs_administrative_assistant_sef_provincial,
  jhs_administrative_assistant_sef_municipal_city,
  jhs_administrative_assistant_lgu_funding,
  jhs_administrative_assistant_other_funding,
  jhs_administrative_aide_sef_provincial,
  jhs_administrative_aide_sef_municipal_city,
  jhs_administrative_aide_lgu_funding,
  jhs_administrative_aide_other_funding,
  jhs_project_development_officer_sef_provincial,
  jhs_project_development_officer_sef_municipal_city,
  jhs_project_development_officer_lgu_funding,
  jhs_project_development_officer_other_funding,
  jhs_school_doctor_sef_provincial,
  jhs_school_doctor_sef_municipal_city,
  jhs_school_doctor_lgu_funding,
  jhs_school_doctor_other_funding,
  jhs_school_dentist_sef_provincial,
  jhs_school_dentist_sef_municipal_city,
  jhs_school_dentist_lgu_funding,
  jhs_school_dentist_other_funding,
  jhs_school_nurse_sef_provincial,
  jhs_school_nurse_sef_municipal_city,
  jhs_school_nurse_lgu_funding,
  jhs_school_nurse_other_funding,
  jhs_librarian_sef_provincial,
  jhs_librarian_sef_municipal_city,
  jhs_librarian_lgu_funding,
  jhs_librarian_other_funding,
  jhs_library_assistant_sef_provincial,
  jhs_library_assistant_sef_municipal_city,
  jhs_library_assistant_lgu_funding,
  jhs_library_assistant_other_funding,
  jhs_guidance_counselor_sef_provincial,
  jhs_guidance_counselor_sef_municipal_city,
  jhs_guidance_counselor_lgu_funding,
  jhs_guidance_counselor_other_funding,
  jhs_guidance_advocate_sef_provincial,
  jhs_guidance_advocate_sef_municipal_city,
  jhs_guidance_advocate_lgu_funding,
  jhs_guidance_advocate_other_funding,
  jhs_guidance_assistant_sef_provincial,
  jhs_guidance_assistant_sef_municipal_city,
  jhs_guidance_assistant_lgu_funding,
  jhs_guidance_assistant_other_funding,
  jhs_computer_technician_sef_provincial,
  jhs_computer_technician_sef_municipal_city,
  jhs_computer_technician_lgu_funding,
  jhs_computer_technician_other_funding,
  shs_learning_support_aide_sef_provincial,
  shs_learning_support_aide_sef_municipal_city,
  shs_learning_support_aide_lgu_funding,
  shs_learning_support_aide_other_funding,
  shs_administrative_officer_sef_provincial,
  shs_administrative_officer_sef_municipal_city,
  shs_administrative_officer_lgu_funding,
  shs_administrative_officer_other_funding,
  shs_administrative_assistant_sef_provincial,
  shs_administrative_assistant_sef_municipal_city,
  shs_administrative_assistant_lgu_funding,
  shs_administrative_assistant_other_funding,
  shs_administrative_aide_sef_provincial,
  shs_administrative_aide_sef_municipal_city,
  shs_administrative_aide_lgu_funding,
  shs_administrative_aide_other_funding,
  shs_project_development_officer_sef_provincial,
  shs_project_development_officer_sef_municipal_city,
  shs_project_development_officer_lgu_funding,
  shs_project_development_officer_other_funding,
  shs_school_doctor_sef_provincial,
  shs_school_doctor_sef_municipal_city,
  shs_school_doctor_lgu_funding,
  shs_school_doctor_other_funding,
  shs_school_dentist_sef_provincial,
  shs_school_dentist_sef_municipal_city,
  shs_school_dentist_lgu_funding,
  shs_school_dentist_other_funding,
  shs_school_nurse_sef_provincial,
  shs_school_nurse_sef_municipal_city,
  shs_school_nurse_lgu_funding,
  shs_school_nurse_other_funding,
  shs_librarian_sef_provincial,
  shs_librarian_sef_municipal_city,
  shs_librarian_lgu_funding,
  shs_librarian_other_funding,
  shs_library_assistant_sef_provincial,
  shs_library_assistant_sef_municipal_city,
  shs_library_assistant_lgu_funding,
  shs_library_assistant_other_funding,
  shs_guidance_counselor_sef_provincial,
  shs_guidance_counselor_sef_municipal_city,
  shs_guidance_counselor_lgu_funding,
  shs_guidance_counselor_other_funding,
  shs_guidance_advocate_sef_provincial,
  shs_guidance_advocate_sef_municipal_city,
  shs_guidance_advocate_lgu_funding,
  shs_guidance_advocate_other_funding,
  shs_guidance_assistant_sef_provincial,
  shs_guidance_assistant_sef_municipal_city,
  shs_guidance_assistant_lgu_funding,
  shs_guidance_assistant_other_funding,
  shs_computer_technician_sef_provincial,
  shs_computer_technician_sef_municipal_city,
  shs_computer_technician_lgu_funding,
  shs_computer_technician_other_funding,
  shs_school_principal_calculated,
  shs_principal_total_discrepancy,
  shs_master_teacher_iv_unavailable,
  personnel_reporting_status,
  enrollment_total,
  batch_id,
  delivery_version,
  schema_version,
  source_sha256,
  source_row_number,
  run_id,
  cleaned_at_utc,
  code_revision
FROM deped_personnel_classified WHERE quarantine_reasons = '';

COMMENT ON TABLE edu_access.`03-silver`.deped_personnel_clean_candidate IS 'Unpublished build for the Silver gate, which may have failed. Do not read: use deped_personnel_clean, trusted by the run its rows carry (D-025).';
ALTER TABLE edu_access.`03-silver`.deped_personnel_clean_candidate OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`03-silver`.deped_personnel_quarantine_candidate USING DELTA AS
SELECT
  school_year,
  school_id,
  split(quarantine_reasons, ',') AS quarantine_reasons,
  split(enrollment_outlier_fields, ',') AS enrollment_outlier_fields,
  batch_id,
  delivery_version,
  schema_version,
  source_sha256,
  source_row_number,
  run_id,
  cleaned_at_utc,
  code_revision
FROM deped_personnel_classified WHERE quarantine_reasons <> '';

COMMENT ON TABLE edu_access.`03-silver`.deped_personnel_quarantine_candidate IS 'Unpublished build for the Silver gate, which may have failed. Do not read: use deped_personnel_quarantine, trusted by the run its rows carry (D-025).';
ALTER TABLE edu_access.`03-silver`.deped_personnel_quarantine_candidate OWNER TO `reached-hq`;
