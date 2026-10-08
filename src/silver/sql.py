"""The Silver build and gate SQL for a source, generated from its spec (src/silver/spec.py).

Both files are committed under etl/03_silver/, and each is one SQL task of the
job (databricks.yml) on the SQL warehouse; src/job/local_run.py runs the same
files locally. A test fails if a committed file differs from what this module
generates, so the reviewed mapping is the only place a rule is written down.

The SQL uses only what Databricks and DuckDB share, plus names that
src/ingestion/store.py translates for DuckDB: regexp_like (DuckDB:
regexp_matches), regexp_replace (Spark replaces every match, DuckDB only the
first unless asked), and session variables (session.<name>). No regular
expression or string literal contains a backslash, because the two engines read
backslashes in literals differently. Job parameters reach the files as :name;
they are copied into session variables first, because a parameter marker cannot
appear in a view or table definition.
"""

from src.ingestion.bronze import OWNER_GROUP
from src.silver.spec import (
    BOOLEAN, CATEGORY, ENROLLMENT_STATUSES, FREE_TEXT, LINEAGE, QUARANTINE_REASONS, RUN_STAMP, SCHEMA,
)

CONTROL = "edu_access.`01-control`"
WHOLE_NUMBER = "^[0-9]{1,%d}$"
NEGATIVE = "^-[0-9]+$"


def silver_ref(table):
    return f"edu_access.`{SCHEMA}`.{table}"


def dq_table_name(table):
    """How data_quality_results names a table: no backticks, as the Bronze gates write it."""
    return f"edu_access.{SCHEMA}.{table}"


def bronze_ref(spec):
    return f"edu_access.`02-bronze`.{spec.bronze_table}"


def lit(value):
    return f"'{value}'"


def in_list(values):
    return "(" + ", ".join(lit(v) for v in values) + ")"


def whitespace(expr):
    """Tab and no-break space become spaces, runs of spaces become one, ends are trimmed."""
    return f"TRIM(regexp_replace(translate({expr}, chr(9) || chr(160), '  '), ' +', ' '))"


def repaired(expr, repairs):
    for published, standard in repairs:
        expr = f"replace({expr}, {lit(published)}, {lit(standard)})"
    return expr


def cleaned_text(spec, column, ref):
    """The text value Silver keeps: repaired (free text only), whitespace normalized, blank to NULL."""
    expr = repaired(ref, spec.repairs) if column.kind == FREE_TEXT else ref
    return f"NULLIF({whitespace(expr)}, '')"


def bq(name):
    return f"`{name}`"


def joined(items, indent, separator=","):
    pad = " " * indent
    return (separator + "\n").join(pad + item for item in items)


def any_of(conditions, indent):
    return ("\n" + " " * indent + "OR ").join(conditions)


def whole_number(spec):
    return WHOLE_NUMBER % spec.max_digits


def typed_count(spec, ref, kind="INT"):
    return f"CASE WHEN regexp_like({ref}, {lit(whole_number(spec))}) THEN TRY_CAST({ref} AS {kind}) END"


def null_safe_sum(refs):
    return " + ".join(f"COALESCE({r}, 0)" for r in refs)


def as_bigint(ref):
    """A count widened before it is added: 66 INT counts of up to nine digits overflow an INT sum."""
    return f"CAST({ref} AS BIGINT)"


def header(spec, what, command, path):
    return [
        f"-- {what} for {spec.source_id}. Generated from config/ingestion/{spec.source_id}.json",
        f"-- and config/mappings/{spec.source_id}.json:",
        f"--   python -m src.silver.cli {command} --source {spec.source_id} > etl/03_silver/{path}",
        "-- Do not edit by hand; tests/test_silver.py fails if it differs.",
    ]


# --- Build ------------------------------------------------------------------------

def build_sql(spec):
    source = spec.source_id
    view = f"{source}_classified"
    clean, quarantine = silver_ref(spec.clean_table), silver_ref(spec.quarantine_table)
    lineage = [name for name, _ in LINEAGE]
    run_stamp = [name for name, _ in RUN_STAMP]
    counts = spec.counts

    normalized = ["r.school_year", f"r.{bq(spec.identifier)}",
                  f"COUNT(*) OVER (PARTITION BY r.school_year, r.{bq(spec.identifier)}) AS {spec.identifier}_rows",
                  f"length(r.{bq(spec.barangay)}) AS {spec.barangay}_published_length"]
    for c in spec.text:
        normalized.append(f"{cleaned_text(spec, c, 'r.' + bq(c.source))} AS {c.name}")
    normalized += [f"r.{bq(c.source)} AS {c.name}" for c in counts]
    normalized += [f"r.{name}" for name in lineage]

    typed = ["n.school_year", f"n.{spec.identifier}"]
    for c in spec.columns:
        if c.kind == FREE_TEXT and c.name in spec.placeholders:
            typed.append(f"CASE WHEN n.{c.name} IN {in_list(spec.placeholders[c.name])} THEN NULL "
                         f"ELSE n.{c.name} END AS {c.name}")
        elif c.kind == FREE_TEXT:
            typed.append(f"n.{c.name}")
        elif c.kind == CATEGORY:
            cases = "\n".join(f"      WHEN {lit(published)} THEN {lit(standard)}"
                              for published, standard in spec.categories[c.name].labels.items())
            typed.append(f"CASE n.{c.name}\n{cases}\n    END AS {c.name}")
        elif c.kind == BOOLEAN:
            typed.append(f"CASE WHEN n.{c.name} IN {in_list(spec.boolean_true)} THEN TRUE "
                         f"WHEN n.{c.name} IN {in_list(spec.boolean_false)} THEN FALSE END AS {c.name}")
    typed += [f"{typed_count(spec, 'n.' + c.name)} AS {c.name}" for c in counts]
    typed.append(f"COALESCE(n.{spec.barangay}_published_length = {spec.barangay_cap}, FALSE) AS barangay_possibly_truncated")
    negative = any_of([f"regexp_like(n.{c.name}, {lit(NEGATIVE)})" for c in counts], 9)
    uncastable = any_of([f"(n.{c.name} <> '' AND NOT regexp_like(n.{c.name}, {lit(whole_number(spec))}) "
                         f"AND NOT regexp_like(n.{c.name}, {lit(NEGATIVE)}))" for c in counts], 9)
    ident = f"n.{spec.identifier}"
    typed.append(
        "concat_ws(',',\n"
        f"      CASE WHEN {ident} IS NULL OR {ident} = '' THEN 'school_id_blank'\n"
        f"           WHEN NOT regexp_like({ident}, {lit(spec.identifier_pattern)}) THEN 'school_id_malformed' END,\n"
        f"      CASE WHEN {ident} <> '' AND n.{spec.identifier}_rows > 1 THEN 'school_id_duplicated' END,\n"
        f"      CASE WHEN {negative}\n      THEN 'count_negative' END,\n"
        f"      CASE WHEN {uncastable}\n      THEN 'count_uncastable' END\n"
        "    ) AS quarantine_reasons")
    typed += [f"n.{name}" for name in lineage]

    overseas = " OR ".join(f"t.{column} = {lit(value)}" for column, value in spec.overseas.items())
    count_refs = [f"t.{c.name}" for c in counts]
    final = ["t.school_year"] + [f"t.{c.name}" for c in spec.columns] + [
        f"COALESCE({overseas}, FALSE) AS is_overseas",
        "CASE WHEN COALESCE(\n" + joined(count_refs, 12) + "\n         ) IS NULL THEN 'no_counts'\n"
        "       WHEN " + null_safe_sum([as_bigint(count_refs[0])]) + "\n" + joined(
            [f"+ COALESCE({as_bigint(r)}, 0)" for r in count_refs[1:]], 12, "") + " = 0 THEN 'all_zero'\n"
        "       ELSE 'has_learners' END AS enrollment_status",
        "t.barangay_possibly_truncated",
        "t.quarantine_reasons",
    ] + [f"t.{name}" for name in lineage] + [f"session.silver_{name} AS {name}" for name in run_stamp]

    clean_columns = [name for name, _ in spec.clean_columns()]
    quarantine_select = ["school_year", spec.identifier, "split(quarantine_reasons, ',') AS quarantine_reasons",
                         *lineage, *run_stamp]
    lines = header(spec, "Silver build", "sql", spec.clean_file) + [
        "--",
        "-- Rebuilds both Silver tables from the current Bronze batches only (01-control.current_batches:",
        "-- the latest succeeded delivery version of each school year). Bronze is read, never changed.",
        "-- Every current Bronze row ends in exactly one of the two tables:",
        f"--   {spec.clean_table}       one row per school per school year, typed and standardized;",
        f"--   {spec.quarantine_table}  rows that cannot be trusted, with their reasons.",
        "-- Each CREATE OR REPLACE is one atomic Delta commit, but the pair is not, so the run is",
        "-- trusted only once the gate (the next task) records it succeeded in pipeline_runs",
        "-- (docs/operations/silver.md). It rebuilds on every run (D-025).",
        "--",
        "-- Parameters, supplied by the job (or src/job/local_run.py):",
        "--   :run_id         the job run; every row built here, and the gate's results, carry it",
        "--   :code_revision  the commit that ran, from the job parameter; never a literal",
        "--   :environment    the deploy target: local, dev, or prod",
        "",
        "-- One run stamp for the whole file, so both tables carry the same run and the same time.",
        "DECLARE OR REPLACE VARIABLE silver_run_id STRING;",
        "SET VARIABLE silver_run_id = :run_id;",
        "DECLARE OR REPLACE VARIABLE silver_code_revision STRING;",
        "SET VARIABLE silver_code_revision = COALESCE(NULLIF(:code_revision, ''), 'UNSET');",
        "DECLARE OR REPLACE VARIABLE silver_environment STRING;",
        "SET VARIABLE silver_environment = COALESCE(NULLIF(:environment, ''), 'UNSET');",
        "DECLARE OR REPLACE VARIABLE silver_cleaned_at_utc TIMESTAMP;",
        "SET VARIABLE silver_cleaned_at_utc = current_timestamp();",
        "",
        "-- The run starts. Its row stays 'running' until the gate records how it ended, so a",
        "-- build that dies is never mistaken for a good one.",
        f"MERGE INTO {CONTROL}.pipeline_runs AS t",
        "USING (SELECT session.silver_run_id AS run_id) AS s",
        f"ON t.run_id = s.run_id AND t.pipeline_name = 'silver_build' AND t.source_id = {lit(source)}",
        "WHEN MATCHED THEN UPDATE SET",
        "  status = 'running', started_at_utc = session.silver_cleaned_at_utc, finished_at_utc = NULL,",
        "  failure_stage = NULL, error_message = NULL, code_revision = session.silver_code_revision",
        "WHEN NOT MATCHED THEN INSERT (run_id, pipeline_name, source_id, environment, status, started_at_utc, code_revision)",
        f"  VALUES (s.run_id, 'silver_build', {lit(source)}, session.silver_environment, 'running',",
        "          session.silver_cleaned_at_utc, session.silver_code_revision);",
        "",
        f"CREATE SCHEMA IF NOT EXISTS edu_access.`{SCHEMA}`;",
        f"ALTER SCHEMA edu_access.`{SCHEMA}` OWNER TO `{OWNER_GROUP}`;",
        "",
        "-- Every current Bronze row once, cleaned, with the reasons it would be quarantined.",
        "-- A reason is decided with explicit NULL handling, and concat_ws never returns NULL, so",
        "-- quarantine_reasons = '' and <> '' split the rows without losing any.",
        f"CREATE OR REPLACE TEMPORARY VIEW {view} AS",
        "WITH bronze AS (",
        "  SELECT r.*",
        f"  FROM {bronze_ref(spec)} AS r",
        f"  JOIN {CONTROL}.current_batches AS c ON r.batch_id = c.batch_id",
        f"  WHERE c.source_id = {lit(source)}",
        "),",
        "-- Text: character repair (free text only), whitespace normalized, blank to NULL. Counts stay as published here.",
        "normalized AS (",
        "  SELECT",
        joined(normalized, 4),
        "  FROM bronze AS r",
        "),",
        "-- Labels mapped to the standard set (unmapped: NULL, and the gate fails), booleans, placeholders,",
        "-- counts typed only when they are whole numbers (TRY_CAST alone accepts '5.0' in DuckDB).",
        "typed AS (",
        "  SELECT",
        joined(typed, 4),
        "  FROM normalized AS n",
        ")",
        "SELECT",
        joined(final, 2),
        "FROM typed AS t;",
        "",
        "-- One row per school per school year, with the Bronze row it came from.",
        f"CREATE OR REPLACE TABLE {clean} USING DELTA AS",
        "SELECT",
        joined(clean_columns, 2),
        f"FROM {view}",
        "WHERE quarantine_reasons = '';",
        "",
        f"ALTER TABLE {clean} OWNER TO `{OWNER_GROUP}`;",
        "",
        "-- Rows set aside, never deleted: the Bronze row, and why.",
        f"CREATE OR REPLACE TABLE {quarantine} USING DELTA AS",
        "SELECT",
        joined(quarantine_select, 2),
        f"FROM {view}",
        "WHERE quarantine_reasons <> '';",
        "",
        f"ALTER TABLE {quarantine} OWNER TO `{OWNER_GROUP}`;",
        "",
    ]
    return "\n".join(lines)


# --- Gate ---------------------------------------------------------------------------

def gate_sql(spec):
    source = spec.source_id
    counts = spec.counts
    clean_name, quarantine_name = dq_table_name(spec.clean_table), dq_table_name(spec.quarantine_table)
    lineage = [name for name, _ in LINEAGE]
    stamp = [name for name, _ in RUN_STAMP]
    categories = spec.of_kind(CATEGORY)
    mapped = spec.of_kind(CATEGORY, BOOLEAN)

    def raw(c):
        return f"b.{bq(c.source)}"

    def accepted(c):
        """Every published label the reviewed mapping accepts for a category or boolean column."""
        return list(spec.categories[c.name].labels) if c.kind == CATEGORY else spec.boolean_true + spec.boolean_false

    bronze_learners = null_safe_sum(typed_count(spec, raw(c), "BIGINT") for c in counts)
    bronze_missing = " + ".join(f"CASE WHEN {raw(c)} IS NULL OR {raw(c)} = '' THEN 1 ELSE 0 END" for c in counts)
    absent = [f"b.schema_version = {lit(v)}" for v in spec.absent]
    bronze_years = [
        "b.school_year",
        "COUNT(*) AS bronze_rows",
        "COUNT_IF(NOT b.in_quarantine) AS kept_rows",
        f"SUM(CASE WHEN b.in_quarantine THEN 0 ELSE\n        {bronze_learners}\n      END) AS kept_learners",
        f"SUM(CASE WHEN b.in_quarantine THEN 0 ELSE\n        {bronze_missing}\n      END) AS kept_missing_counts",
        "COUNT_IF(\n        " + any_of([f"{whitespace(raw(c))} <> {raw(c)}" for c in spec.text], 8) + "\n      ) AS whitespace_rows",
        "COUNT_IF(\n        " + any_of([f"{repaired(raw(c), spec.repairs)} <> {raw(c)}" for c in spec.of_kind(FREE_TEXT)], 8)
        + "\n      ) AS repaired_rows",
        "COUNT_IF(\n        " + any_of([f"{whitespace(raw(c))} = ''" for c in spec.text], 8) + "\n      ) AS blank_text_rows",
        "COUNT_IF(\n        " + any_of([f"{whitespace(repaired('b.' + bq(spec.column(name).source), spec.repairs))} IN {in_list(values)}"
                                        for name, values in spec.placeholders.items()], 8) + "\n      ) AS placeholder_rows",
        "COUNT_IF(\n        " + any_of([f"{raw(c)} = ''" for c in counts], 8) + "\n      ) AS blank_count_rows",
        (f"COUNT_IF({' OR '.join(absent)}) AS absent_column_rows" if absent else "0 AS absent_column_rows"),
    ] + [
        f"COUNT_IF(b.in_quarantine AND {whitespace(raw(x))} <> ''\n"
        f"        AND {whitespace(raw(x))} NOT IN {in_list(accepted(x))}) AS quarantined_unmapped_{x.name}"
        for x in mapped
    ]
    clean_learners = null_safe_sum(as_bigint(f"c.{x.name}") for x in counts)
    clean_missing = " + ".join(f"CASE WHEN c.{x.name} IS NULL THEN 1 ELSE 0 END" for x in counts)
    absent_filled = [f"(c.schema_version = {lit(v)} AND ({' OR '.join(f'c.{n} IS NOT NULL' for n in names)}))"
                     for v, names in spec.absent.items()]
    clean_years = [
        "c.school_year",
        "COUNT(*) AS clean_rows",
        f"COUNT(DISTINCT c.{spec.identifier}) AS clean_ids",
        f"COUNT_IF(c.{spec.identifier} IS NULL OR NOT regexp_like(c.{spec.identifier}, {lit(spec.identifier_pattern)})) AS invalid_ids",
        "COUNT_IF(\n        " + any_of([f"c.{x.name} < 0" for x in counts], 8) + "\n      ) AS negative_rows",
        f"SUM(\n        {clean_learners}\n      ) AS clean_learners",
        f"SUM(\n        {clean_missing}\n      ) AS clean_missing_counts",
        ("COUNT_IF(\n        " + any_of(absent_filled, 8) + "\n      ) AS absent_filled_rows") if absent_filled else "0 AS absent_filled_rows",
        "COUNT_IF(c.is_overseas) AS overseas_rows",
        "COUNT_IF(c.enrollment_status = 'all_zero') AS all_zero_rows",
        "COUNT_IF(c.enrollment_status = 'no_counts') AS no_counts_rows",
        f"COUNT_IF(c.enrollment_status IS NULL OR c.enrollment_status NOT IN {in_list(ENROLLMENT_STATUSES)}) AS invalid_status_rows",
        "COUNT_IF(c.barangay_possibly_truncated) AS truncated_rows",
        f"COUNT_IF(c.{spec.barangay} IS NULL) AS {spec.barangay}_null_rows",
    ]
    matched_years = ["c.school_year"] + [
        f"COUNT_IF(c.{x.name} IS NULL AND {whitespace(raw(x))} <> '') AS unmapped_{x.name}" for x in mapped
    ] + ["COUNT_IF(\n        " + any_of([f"{whitespace(raw(x))} <> c.{x.name}" for x in categories], 8) + "\n      ) AS relabelled_rows"]
    quarantine_years = ["q.school_year", "COUNT(*) AS quarantined_rows"] + [
        f"COUNT_IF(array_contains(q.quarantine_reasons, {lit(r)})) AS reason_{r}" for r in QUARANTINE_REASONS]

    year_columns = ["y.school_year", "y.batch_id", "COALESCE(bronze_rows, 0) AS bronze_rows",
                    "COALESCE(kept_rows, 0) AS kept_rows", "COALESCE(kept_learners, 0) AS kept_learners",
                    "COALESCE(kept_missing_counts, 0) AS kept_missing_counts",
                    "COALESCE(clean_rows, 0) AS clean_rows", "COALESCE(clean_ids, 0) AS clean_ids",
                    "COALESCE(clean_learners, 0) AS clean_learners",
                    "COALESCE(clean_missing_counts, 0) AS clean_missing_counts",
                    "COALESCE(quarantined_rows, 0) AS quarantined_rows"]
    passthrough = ["whitespace_rows", "repaired_rows", "blank_text_rows", "placeholder_rows", "blank_count_rows",
                   "absent_column_rows", "invalid_ids", "negative_rows", "absent_filled_rows", "overseas_rows",
                   "all_zero_rows", "no_counts_rows", "invalid_status_rows", "truncated_rows",
                   f"{spec.barangay}_null_rows", "relabelled_rows", *[f"reason_{r}" for r in QUARANTINE_REASONS]]
    year_columns += [f"COALESCE({name}, 0) AS {name}" for name in passthrough]
    # Unmapped labels: clean rows by what the build made of them, quarantined rows against the mapping itself.
    year_columns += [f"COALESCE(unmapped_{x.name}, 0) + COALESCE(quarantined_unmapped_{x.name}, 0) AS unmapped_{x.name}"
                     for x in mapped]

    def check(name, table, status, expected, actual, source="years"):
        batch = "batch_id" if source == "years" else "CAST(NULL AS STRING)"
        return (f"SELECT {batch} AS batch_id, {lit(table)} AS table_name, {lit(name)} AS check_name,\n"
                f"         {status} AS status,\n"
                f"         {expected} AS expected, {actual} AS actual FROM {source}")

    def must_equal(name, table, expected, actual, source="years"):
        return check(name, table, f"CASE WHEN {actual} = {expected} THEN 'PASS' ELSE 'FAIL' END",
                     f"CAST({expected} AS STRING)", f"CAST({actual} AS STRING)", source)

    def must_be_zero(name, table, actual, source="years"):
        return must_equal(name, table, "0", actual, source)

    def warn_if_any(name, table, actual):
        return check(name, table, f"CASE WHEN {actual} = 0 THEN 'PASS' ELSE 'WARN' END", "'0'",
                     f"CAST({actual} AS STRING)")

    def record(name, actual):
        return check(name, clean_name, "'PASS'", "CAST(NULL AS STRING)", f"CAST({actual} AS STRING)")

    checks = [
        "-- The whole table, both tables together",
        check("current_batches_present", clean_name, "CASE WHEN current_batches > 0 THEN 'PASS' ELSE 'FAIL' END",
              "'at least 1'", "CAST(current_batches AS STRING)", "found"),
        must_be_zero("lineage_complete", clean_name, "missing_lineage", "whole"),
        must_be_zero("rows_resolve_to_current_bronze", clean_name, "unresolved_rows", "unresolved"),
        must_be_zero("rows_built_by_this_run", clean_name, "other_run_rows", "whole"),
        must_equal("one_timestamp_per_run", clean_name, "1", "timestamps", "whole"),
        "-- Each school year: reconciliation, keys, ranges, NULLs",
        must_equal("rows_reconcile", clean_name, "bronze_rows", "clean_rows + quarantined_rows"),
        must_be_zero("school_id_unique", clean_name, "clean_rows - clean_ids"),
        must_be_zero("school_id_valid", clean_name, "invalid_ids"),
        must_be_zero("counts_non_negative", clean_name, "negative_rows"),
        must_equal("learners_reconcile", clean_name, "kept_learners", "clean_learners"),
        must_equal("missing_counts_stay_null", clean_name, "kept_missing_counts", "clean_missing_counts"),
        must_be_zero("absent_columns_stay_null", clean_name, "absent_filled_rows"),
        must_be_zero("enrollment_status_valid", clean_name, "invalid_status_rows"),
        "-- Each school year: every label is in the reviewed mapping",
        *[must_be_zero(f"labels_mapped_{x.name}", clean_name, f"unmapped_{x.name}") for x in mapped],
        "-- Each school year: quarantine (WARN above 0, FAIL above 1% of the year's Bronze rows)",
        check("quarantine_rate", quarantine_name,
              "CASE WHEN quarantined_rows = 0 THEN 'PASS' WHEN quarantined_rows * 100 > bronze_rows THEN 'FAIL' ELSE 'WARN' END",
              # No ';' inside a string: store.split_statements splits files on it.
              "'0 (FAIL above 1% of ' || CAST(bronze_rows AS STRING) || ')'", "CAST(quarantined_rows AS STRING)"),
        *[warn_if_any(f"quarantine_reason_{r}", quarantine_name, f"reason_{r}") for r in QUARANTINE_REASONS],
        "-- Each school year: how many rows each cleaning rule changed or flagged (records, always PASS)",
        record("rule_whitespace_normalized", "whitespace_rows"),
        record("rule_characters_repaired", "repaired_rows"),
        record("rule_blank_text_to_null", "blank_text_rows"),
        record("rule_placeholder_to_null", "placeholder_rows"),
        record("rule_blank_counts_to_null", "blank_count_rows"),
        record("rule_absent_columns_null", "absent_column_rows"),
        record("rule_labels_standardized", "relabelled_rows"),
        record("flag_is_overseas", "overseas_rows"),
        record("flag_enrollment_all_zero", "all_zero_rows"),
        record("flag_enrollment_no_counts", "no_counts_rows"),
        record("flag_barangay_possibly_truncated", "truncated_rows"),
        record(f"flag_{spec.barangay}_blank", f"{spec.barangay}_null_rows"),
    ]
    union = []
    for item in checks:
        if item.startswith("--"):
            union.append("  " + item)
        else:
            union.append(("  UNION ALL " if any(not u.lstrip().startswith("--") for u in union) else "  ") + item)

    silver_rows = (f"  SELECT {', '.join(['school_year', *lineage, *stamp])} FROM clean\n"
                   f"  UNION ALL SELECT {', '.join(['school_year', *lineage, *stamp])} FROM quarantined")
    missing_lineage = " OR ".join(f"{name} IS NULL" for name in ["school_year", *lineage, *stamp])
    lines = header(spec, "Silver gate", "gate", f"90_validate_{spec.clean_table}.sql") + [
        "--",
        "-- The job task after the Silver build. Each check writes one row to data_quality_results;",
        "-- then the run's pipeline_runs row records 'succeeded' or 'failed', and the last statement",
        "-- fails the task on any FAIL, so nothing downstream runs.",
        "-- PASS: as expected. WARN: recorded, the build stands (quarantined rows exist).",
        "-- FAIL: the Silver tables cannot be trusted. Results hold counts, never row values.",
        "--",
        "-- Parameters, supplied by the job (or src/job/local_run.py):",
        "--   :run_id         the job run that built the tables",
        "--   :code_revision  the commit that ran, from the job parameter; never a literal",
        "",
        "-- Only this execution's results decide: a repaired job run keeps its run_id, and the",
        "-- results of an earlier attempt must not fail it again.",
        "DECLARE OR REPLACE VARIABLE silver_gate_started_at_utc TIMESTAMP;",
        "SET VARIABLE silver_gate_started_at_utc = current_timestamp();",
        "",
        f"INSERT INTO {CONTROL}.data_quality_results",
        "  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)",
        f"SELECT :run_id, batch_id, {lit(source)}, 'silver', table_name, check_name, status, expected, actual,",
        "       current_timestamp(), :code_revision",
        "FROM (",
        "WITH cur AS (",
        f"  SELECT batch_id, school_year FROM {CONTROL}.current_batches WHERE source_id = {lit(source)}",
        "),",
        "bronze AS (",
        f"  SELECT r.* FROM {bronze_ref(spec)} AS r JOIN cur ON r.batch_id = cur.batch_id",
        "),",
        f"clean AS (SELECT * FROM {silver_ref(spec.clean_table)}),",
        f"quarantined AS (SELECT * FROM {silver_ref(spec.quarantine_table)}),",
        "-- Current Bronze rows, each marked if Silver set it aside.",
        "b AS (",
        "  SELECT bronze.*, q.source_row_number IS NOT NULL AS in_quarantine",
        "  FROM bronze",
        "  LEFT JOIN quarantined AS q",
        "    ON bronze.source_sha256 = q.source_sha256 AND bronze.source_row_number = q.source_row_number",
        "),",
        "-- A quarantined row has no clean value, so its labels are checked against the reviewed mapping here:",
        "-- a row set aside for another reason must not let an unmapped label through.",
        "bronze_years AS (",
        "  SELECT",
        joined(bronze_years, 4),
        "  FROM b GROUP BY b.school_year",
        "),",
        "clean_years AS (",
        "  SELECT",
        joined(clean_years, 4),
        "  FROM clean AS c GROUP BY c.school_year",
        "),",
        "-- Each clean row beside its Bronze row: is every published label mapped?",
        "matched_years AS (",
        "  SELECT",
        joined(matched_years, 4),
        "  FROM clean AS c",
        "  JOIN b ON c.source_sha256 = b.source_sha256 AND c.source_row_number = b.source_row_number",
        "  GROUP BY c.school_year",
        "),",
        "quarantine_years AS (",
        "  SELECT",
        joined(quarantine_years, 4),
        "  FROM quarantined AS q GROUP BY q.school_year",
        "),",
        "years AS (",
        "  SELECT",
        joined(year_columns, 4),
        "  FROM cur AS y",
        "  LEFT JOIN bronze_years ON bronze_years.school_year = y.school_year",
        "  LEFT JOIN clean_years ON clean_years.school_year = y.school_year",
        "  LEFT JOIN matched_years ON matched_years.school_year = y.school_year",
        "  LEFT JOIN quarantine_years ON quarantine_years.school_year = y.school_year",
        "),",
        "found AS (SELECT COUNT(*) AS current_batches FROM cur),",
        "silver_rows AS (",
        silver_rows,
        "),",
        "whole AS (",
        "  SELECT",
        f"    COUNT_IF({missing_lineage}) AS missing_lineage,",
        "    COUNT_IF(run_id IS NULL OR run_id <> :run_id) AS other_run_rows,",
        "    COUNT(DISTINCT cleaned_at_utc) AS timestamps",
        "  FROM silver_rows",
        "),",
        "-- Silver rows whose Bronze row is not in a current batch (an old version, or gone).",
        "unresolved AS (",
        "  SELECT COUNT(*) AS unresolved_rows",
        "  FROM silver_rows AS s",
        "  LEFT JOIN bronze ON s.source_sha256 = bronze.source_sha256 AND s.source_row_number = bronze.source_row_number",
        "  WHERE bronze.source_row_number IS NULL",
        "),",
        "checks AS (",
        *union,
        ")",
        "SELECT * FROM checks",
        ") AS results;",
        "",
        "-- How the run ended. 'succeeded' is the last write of a good build: Gold reads Silver",
        "-- only when the latest silver_build run of the source succeeded.",
        f"MERGE INTO {CONTROL}.pipeline_runs AS t",
        "USING (",
        "  SELECT :run_id AS run_id, COUNT_IF(status = 'FAIL') AS fails",
        f"  FROM {CONTROL}.data_quality_results",
        f"  WHERE run_id = :run_id AND source_id = {lit(source)} AND layer = 'silver'",
        "    AND checked_at_utc >= session.silver_gate_started_at_utc",
        ") AS s",
        f"ON t.run_id = s.run_id AND t.pipeline_name = 'silver_build' AND t.source_id = {lit(source)}",
        "WHEN MATCHED THEN UPDATE SET",
        "  status = CASE WHEN s.fails = 0 THEN 'succeeded' ELSE 'failed' END,",
        "  finished_at_utc = current_timestamp(),",
        "  failure_stage = CASE WHEN s.fails = 0 THEN NULL ELSE 'gate' END,",
        "  error_message = CASE WHEN s.fails = 0 THEN NULL",
        "                       ELSE CAST(s.fails AS STRING) || ' FAIL result(s) in data_quality_results' END;",
        "",
        "-- Stop here if anything failed in this execution.",
        "SELECT CASE WHEN COUNT(*) > 0",
        f"            THEN raise_error('Silver gate failed for {source}: ' || CAST(COUNT(*) AS STRING)",
        "                             || ' FAIL result(s) in data_quality_results for run ' || :run_id)",
        "       END",
        f"FROM {CONTROL}.data_quality_results",
        f"WHERE run_id = :run_id AND source_id = {lit(source)} AND layer = 'silver' AND status = 'FAIL'",
        "  AND checked_at_utc >= session.silver_gate_started_at_utc;",
        "",
    ]
    return "\n".join(lines)
