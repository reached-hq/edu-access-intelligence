-- What downstream (Silver) may read: for each source and school year, the
-- highest delivery_version whose batch succeeded. Earlier versions stay in
-- Bronze and in ingestion_batches; this view only says which one is current.
-- Which version should be current after a publisher revision is an open team
-- decision (docs/decisions.md); this view implements the default, latest.
CREATE OR REPLACE VIEW edu_access.`01-control`.current_batches AS
SELECT batch_id, source_id, school_year, delivery_version, archive_sha256, source_sha256, succeeded_at_utc
FROM (
  SELECT
    b.*,
    ROW_NUMBER() OVER (PARTITION BY source_id, school_year ORDER BY delivery_version DESC) AS rank_in_year
  FROM edu_access.`01-control`.ingestion_batches AS b
  WHERE status = 'succeeded'
) AS ranked
WHERE rank_in_year = 1;

-- Owned by the team group, not by whoever ran the job first (D-009).
ALTER VIEW edu_access.`01-control`.current_batches OWNER TO `reached-hq`;
