-- What downstream (Silver) may read: for each source and period, the highest
-- delivery_version whose batch succeeded. The period is the school year for
-- school-year sources, and the logical dataset for workbook sources whose
-- delivery covers several estimate years (psa_poverty_stat). One version per
-- logical dataset is safe only because the contract refuses a revision that
-- drops an estimate year of the version it supersedes (D-018), so the current
-- version always covers every year approved for that dataset. Earlier versions
-- stay in Bronze and in ingestion_batches; this view only says which one is
-- current. Which version should be current after a publisher revision is an
-- open team decision (docs/governance/decisions.md); this view implements the default, latest.
CREATE OR REPLACE VIEW edu_access.`01-control`.current_batches AS
SELECT batch_id, source_id, school_year, logical_dataset, estimate_years_covered, delivery_version,
       archive_sha256, source_sha256, succeeded_at_utc
FROM (
  SELECT
    b.*,
    ROW_NUMBER() OVER (
      PARTITION BY source_id, COALESCE(school_year, logical_dataset)
      ORDER BY delivery_version DESC
    ) AS rank_in_period
  FROM edu_access.`01-control`.ingestion_batches AS b
  WHERE status = 'succeeded'
) AS ranked
WHERE rank_in_period = 1;

-- Owned by the team group, not by whoever ran the job first (D-009).
ALTER VIEW edu_access.`01-control`.current_batches OWNER TO `reached-hq`;
