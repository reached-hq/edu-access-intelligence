"""The data-quality dashboard, `dashboards/data_quality.lvdash.json`, generated (#97).

The dashboard reads only the control tables in `01-control`: what every gate
recorded in `data_quality_results`, the runs in `pipeline_runs`, and the
deliveries in `ingestion_batches` and `current_batches`. It never reads a
Bronze, Silver, Integration, or Gold table, so it works before Gold exists, and
a layer whose gates have not run yet shows "No checks recorded yet", not PASS.

`data_quality_results` is append-only: a check is recorded again every run. So
the dashboard keeps two views apart (see dashboards/README.md):

- current: the newest result of each check, one row per (layer, source_id,
  table_name, check_name, batch_id), all its PASS/WARN/FAIL counts and pass
  rate come from this. Results of a superseded delivery are left out; results
  of a failed or blocked one stay until it is retried.
- history: every recorded result, in the dashboard's date range, for the trend
  and the explorer. It counts result events, never checks.

Which quality attribute a check tests comes from one reviewed file,
`config/quality_attributes.yml`, written into the current dataset only; a
check it does not list is shown as Unclassified.

Kept cheap on the shared Free Edition warehouse: five small datasets over the
control tables, history limited by the date range in its WHERE, no refresh
schedule, and nothing new is created or persisted.

    python -m src.dashboard.data_quality > dashboards/data_quality.lvdash.json
"""

import inspect
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(inspect.currentframe().f_code.co_filename).resolve().parents[2]

PATH = "dashboards/data_quality.lvdash.json"
CONFIG = "config/quality_attributes.yml"
CONTROL = "edu_access.`01-control`"
DQ = f"{CONTROL}.data_quality_results"

# Pipeline layers in order (docs/architecture/overview.md), so one with no result is listed, not missing.
LAYERS = ["control", "bronze", "silver", "integration", "gold", "analytics"]
UNCLASSIFIED = "Unclassified"
RECORDED = "Recorded count"
# A trailing qualifier a gate adds when it checks each estimate year, census concept, school year, or
# level separately: rows_reconcile_2018, key_unique_household, match_rate_2023-24_bgy, learners/2023-24/ES.
QUALIFIER = "(/.*|_[0-9]{4}(-[0-9]{2})?(_[a-z_]+)?|_household|_total)$"
# A leading "<sheet>: " a Bronze gate adds when it checks a workbook sheet by sheet.
SHEET_PREFIX = "^[^:]+: "

STATUS_COLORS = {"PASS": "#009E73", "WARN": "#E69F00", "FAIL": "#D55E00"}
HISTORY_DAYS = 90


class CatalogError(Exception):
    pass


# ---------------------------------------------------------------- catalog

def load_catalog(repo_root=REPO_ROOT):
    """[(match_kind, check_key, quality_attribute, check_kind, note)] from the reviewed file, checked."""
    config = yaml.safe_load((Path(repo_root) / CONFIG).read_text(encoding="utf-8"))
    attributes = [a["name"] for a in config["attributes"]]
    core = [(a["name"], " ".join(a["means"].split())) for a in config["attributes"] if a.get("core")]
    rows = []
    for attribute, names in config["checks"].items():
        if attribute not in attributes:
            raise CatalogError(f"{CONFIG}: checks are listed under {attribute!r}, which is not an attribute.")
        rows += [("name", name, attribute, "test", None) for name in names]
    for prefix, family in config.get("families", {}).items():
        if family["attribute"] not in attributes:
            raise CatalogError(f"{CONFIG}: family {prefix!r} names {family['attribute']!r}, which is not an attribute.")
        rows.append(("family", prefix, family["attribute"], "test", None))
    recorded = config.get("recorded_counts", {})
    rows += [("name", name, RECORDED, "record", None) for name in recorded.get("checks", [])]
    rows += [("family", prefix, RECORDED, "record", None) for prefix in recorded.get("families", {})]
    for entry in config.get("unclassified", []):
        if not str(entry.get("reason", "")).strip():
            raise CatalogError(f"{CONFIG}: give the reason {entry.get('check')!r} is left unclassified.")
        rows.append(("name", entry["check"], UNCLASSIFIED, "test", " ".join(entry["reason"].split())))

    names = [key for kind, key, *_ in rows if kind == "name"]
    repeated = sorted({n for n in names if names.count(n) > 1})
    if repeated:
        raise CatalogError(f"{CONFIG}: listed more than once: {repeated}.")
    prefixes = [key for kind, key, *_ in rows if kind == "family"]
    overlapping = sorted((a, b) for a in prefixes for b in prefixes if a != b and b.startswith(a))
    if overlapping:
        raise CatalogError(f"{CONFIG}: families overlap: {overlapping}.")
    return attributes, core, rows


def _sql_text(value):
    return "NULL" if value is None else "'" + str(value).replace("'", "''") + "'"


def _catalog_cte(rows):
    values = ",\n    ".join(
        "(" + ", ".join(_sql_text(v) for v in row) + ")" for row in rows)
    return [
        "catalog AS (",
        "  SELECT * FROM (VALUES",
        f"    {values}",
        "  ) AS c(match_kind, check_key, quality_attribute, check_kind, note)",
        "),",
    ]


def _classified_ctes(rows, more=False):
    """The results with their attribute: exact name, then without a qualifier, then a family.

    `more` leaves the list open for another CTE after `classified`."""
    return [
        *_catalog_cte(rows),
        "results AS (",
        "  SELECT q.run_id, q.batch_id, q.source_id, q.layer, q.table_name, q.check_name, q.status,",
        "         q.expected, q.actual, q.checked_at_utc, q.code_revision,",
        f"         regexp_replace(q.check_name, '{SHEET_PREFIX}', '') AS check_key",
        f"  FROM {DQ} AS q",
        "),",
        "classified AS (",
        "  SELECT r.*,",
        f"         COALESCE(e.quality_attribute, b.quality_attribute, f.quality_attribute, '{UNCLASSIFIED}') AS quality_attribute,",
        "         COALESCE(e.check_kind, b.check_kind, f.check_kind, 'test') AS check_kind,",
        "         CASE WHEN e.check_key IS NOT NULL THEN COALESCE('deliberately unclassified: ' || e.note, 'listed')",
        "              WHEN b.check_key IS NOT NULL THEN 'listed, with a year or concept qualifier'",
        "              WHEN f.check_key IS NOT NULL THEN 'name family ' || f.check_key",
        f"              ELSE 'not in {CONFIG}' END AS classification_basis",
        "  FROM results AS r",
        "  LEFT JOIN catalog AS e ON e.match_kind = 'name' AND e.check_key = r.check_key",
        "  LEFT JOIN catalog AS b ON b.match_kind = 'name' AND e.check_key IS NULL",
        f"    AND b.check_key = regexp_replace(r.check_key, '{QUALIFIER}', '') AND b.check_key <> r.check_key",
        "  LEFT JOIN catalog AS f ON f.match_kind = 'family' AND e.check_key IS NULL AND b.check_key IS NULL",
        "    AND LEFT(r.check_key, LENGTH(f.check_key)) = f.check_key",
        ")," if more else ")",
    ]


# ---------------------------------------------------------------- datasets

STATUS_FLAGS = [
    "CASE WHEN status = 'PASS' THEN 1 ELSE 0 END AS is_pass",
    "CASE WHEN status = 'WARN' THEN 1 ELSE 0 END AS is_warn",
    "CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END AS is_fail",
]
IN_RANGE = "CAST(q.checked_at_utc AS DATE) BETWEEN :history_range.min AND :history_range.max"


def current_sql(rows):
    return [
        "-- Current: the newest result of each check. A check is one (layer, source_id, table_name,",
        "-- check_name, batch_id); RANK keeps every row one gate statement wrote together.",
        "WITH",
        *_classified_ctes(rows, more=True),
        "newest AS (",
        "  SELECT c.*, RANK() OVER (PARTITION BY c.layer, c.source_id, c.table_name, c.check_name, c.batch_id",
        "                           ORDER BY c.checked_at_utc DESC) AS result_rank",
        "  FROM classified AS c",
        "),",
        "batches AS (",
        "  SELECT b.batch_id, b.status AS batch_status, COALESCE(b.school_year, b.logical_dataset) AS batch_period,",
        "         cb.batch_id IS NOT NULL AS is_current_batch",
        f"  FROM {CONTROL}.ingestion_batches AS b",
        f"  LEFT JOIN {CONTROL}.current_batches AS cb ON cb.batch_id = b.batch_id",
        "),",
        "snapshot AS (",
        "  SELECT n.*, bt.batch_period,",
        "         CASE WHEN n.batch_id IS NULL THEN 'not batch-scoped'",
        "              WHEN bt.batch_id IS NULL THEN 'not in ingestion_batches'",
        "              WHEN bt.is_current_batch THEN 'current delivery'",
        "              ELSE 'batch ' || bt.batch_status END AS batch_state",
        "  FROM newest AS n",
        "  LEFT JOIN batches AS bt ON bt.batch_id = n.batch_id",
        "  WHERE n.result_rank = 1",
        "    -- A delivery replaced by a newer version is no longer read downstream.",
        "    AND NOT COALESCE(bt.batch_status = 'succeeded' AND NOT bt.is_current_batch, FALSE)",
        ")",
        "SELECT layer, source_id, table_name, check_name, status, expected, actual,",
        "       quality_attribute, check_kind, classification_basis,",
        "       run_id, batch_id, batch_period, batch_state, checked_at_utc AS last_checked_at_utc, code_revision,",
        *[f"       {flag}," for flag in STATUS_FLAGS],
        "       1 AS is_result,",
        "       CASE WHEN check_kind = 'test' THEN 1 ELSE 0 END AS is_test,",
        "       CASE WHEN check_kind = 'test' AND status = 'PASS' THEN 1 ELSE 0 END AS is_test_pass",
        "FROM snapshot",
    ]


def history_sql():
    return [
        "-- History: every recorded result in the date range. Counts result events, not checks.",
        "SELECT q.layer, q.source_id, q.table_name, q.check_name, q.status, q.expected, q.actual,",
        "       q.run_id, q.batch_id, q.checked_at_utc, q.code_revision",
        f"FROM {DQ} AS q",
        f"WHERE {IN_RANGE}",
    ]


def runs_sql():
    return [
        "-- One row per job run. A Bronze load records its own run_id and the job run in job_run_id,",
        "-- and writes its batch checks under its own run_id; every gate writes under the job run. So",
        "-- both sides are rolled up to the job run, and aggregated, before the join: nothing counts twice.",
        "WITH run_keys AS (",
        "  SELECT DISTINCT run_id, COALESCE(job_run_id, run_id) AS run_key",
        f"  FROM {CONTROL}.pipeline_runs",
        "),",
        "runs AS (",
        "  SELECT COALESCE(job_run_id, run_id) AS run_id,",
        "         MAX(environment) AS environment,",
        "         MIN(started_at_utc) AS started_at_utc,",
        "         CASE WHEN COUNT_IF(finished_at_utc IS NULL) = 0 THEN MAX(finished_at_utc) END AS finished_at_utc,",
        "         COUNT(*) AS steps,",
        "         COUNT_IF(status = 'failed') AS failed_steps,",
        "         COUNT_IF(status = 'running') AS unfinished_steps,",
        "         string_agg(CASE WHEN status <> 'succeeded' THEN pipeline_name || ' ' || source_id END, ', ') AS steps_not_succeeded,",
        "         string_agg(DISTINCT failure_stage, ', ') AS failure_stages,",
        "         max_by(error_message, COALESCE(finished_at_utc, started_at_utc)) AS last_error_message,",
        "         string_agg(DISTINCT code_revision, ', ') AS code_revisions",
        f"  FROM {CONTROL}.pipeline_runs",
        "  GROUP BY COALESCE(job_run_id, run_id)",
        "),",
        "checks AS (",
        "  SELECT COALESCE(k.run_key, q.run_id) AS run_id,",
        "         COUNT_IF(q.status = 'PASS') AS pass_results, COUNT_IF(q.status = 'WARN') AS warn_results,",
        "         COUNT_IF(q.status = 'FAIL') AS fail_results, MIN(q.checked_at_utc) AS first_checked_at_utc",
        f"  FROM {DQ} AS q",
        "  LEFT JOIN run_keys AS k ON k.run_id = q.run_id",
        "  GROUP BY COALESCE(k.run_key, q.run_id)",
        "),",
        "joined AS (",
        "  SELECT COALESCE(r.run_id, c.run_id) AS run_id, r.environment,",
        "         CASE WHEN r.run_id IS NULL THEN 'no pipeline_runs row'",
        "              WHEN r.failed_steps > 0 THEN 'failed'",
        "              WHEN r.unfinished_steps > 0 THEN 'running or interrupted'",
        "              ELSE 'succeeded' END AS run_status,",
        "         COALESCE(r.started_at_utc, c.first_checked_at_utc) AS run_started_at_utc,",
        "         r.finished_at_utc AS run_finished_at_utc,",
        "         timestampdiff(SECOND, r.started_at_utc, r.finished_at_utc) / 60.0 AS duration_minutes,",
        "         r.steps, r.failed_steps, r.steps_not_succeeded, r.failure_stages,",
        "         LEFT(r.last_error_message, 300) AS last_error_message, r.code_revisions,",
        "         COALESCE(c.pass_results, 0) AS pass_results, COALESCE(c.warn_results, 0) AS warn_results,",
        "         COALESCE(c.fail_results, 0) AS fail_results",
        "  FROM runs AS r",
        "  FULL OUTER JOIN checks AS c ON c.run_id = r.run_id",
        ")",
        "SELECT *, RANK() OVER (ORDER BY run_started_at_utc DESC) AS run_recency",
        "FROM joined",
    ]


def freshness_sql():
    return [
        "-- The rows the stale_sources alert reads: the latest run that checked freshness, newest",
        "-- result per source, with the source's latest succeeded delivery beside it.",
        "WITH latest_run AS (",
        f"  SELECT run_id FROM {DQ}",
        "  WHERE check_name = 'source_fresh'",
        "  ORDER BY checked_at_utc DESC LIMIT 1",
        "),",
        "newest AS (",
        "  SELECT q.*, RANK() OVER (PARTITION BY q.source_id ORDER BY q.checked_at_utc DESC) AS result_rank",
        f"  FROM {DQ} AS q",
        "  JOIN latest_run AS r ON q.run_id = r.run_id",
        "  WHERE q.check_name = 'source_fresh'",
        "),",
        "delivered AS (",
        "  SELECT source_id, MAX(succeeded_at_utc) AS last_succeeded_at_utc, COUNT(*) AS current_batches",
        f"  FROM {CONTROL}.current_batches",
        "  GROUP BY source_id",
        ")",
        "SELECT n.source_id, n.status AS freshness_status, n.expected AS freshness_limit,",
        "       n.actual AS freshness_observed, n.checked_at_utc AS freshness_checked_at_utc, n.run_id,",
        "       d.last_succeeded_at_utc, d.current_batches,",
        "       CASE WHEN n.status = 'WARN' THEN 1 ELSE 0 END AS is_stale",
        "FROM newest AS n",
        "LEFT JOIN delivered AS d ON d.source_id = n.source_id",
        "WHERE n.result_rank = 1",
    ]


def layers_sql():
    values = ", ".join(f"({i}, '{layer}')" for i, layer in enumerate(LAYERS, start=1))
    return [
        "-- Every pipeline layer, with or without results, and any other layer a gate recorded.",
        "WITH recorded AS (",
        "  SELECT layer, COUNT(*) AS result_events, COUNT(DISTINCT run_id) AS runs,",
        "         COUNT(DISTINCT check_name) AS distinct_checks, MAX(checked_at_utc) AS last_checked_at_utc",
        f"  FROM {DQ}",
        "  GROUP BY layer",
        ")",
        "SELECT COALESCE(l.layer, r.layer) AS layer, COALESCE(l.layer_order, 99) AS layer_order,",
        "       CASE WHEN r.layer IS NULL THEN 'No checks recorded yet'",
        "            WHEN l.layer IS NULL THEN 'Checks recorded (layer not in the pipeline list)'",
        "            ELSE 'Checks recorded' END AS coverage_state,",
        "       r.result_events, r.runs, r.distinct_checks, r.last_checked_at_utc",
        f"FROM (VALUES {values}) AS l(layer_order, layer)",
        "FULL OUTER JOIN recorded AS r ON r.layer = l.layer",
    ]


def history_parameter():
    return {
        "displayName": "Date range (UTC)",
        "keyword": "history_range",
        "dataType": "DATE",
        "complexType": "RANGE",
        "defaultSelection": {"range": {"dataType": "DATE",
                                       "min": {"value": f"now-{HISTORY_DAYS}d/d"},
                                       "max": {"value": "now/d"}}},
    }


def datasets(rows):
    def dataset(name, display, lines, **extra):
        return {"name": name, "displayName": display, "queryLines": [line + "\n" for line in lines], **extra}

    return [
        dataset("ds_current", "Current check results", current_sql(rows), columns=[
            {"displayName": "Pass rate (tests)",
             "description": "PASS / (PASS + WARN + FAIL) over current results of tests; recorded counts are left "
                            "out. Empty when there is no test result.",
             "expression": "SUM(`is_test_pass`) * 1.0 / NULLIF(SUM(`is_test`), 0)"},
        ]),
        dataset("ds_history", "Check result events", history_sql(), parameters=[history_parameter()]),
        dataset("ds_runs", "Job runs", runs_sql()),
        dataset("ds_freshness", "Source freshness", freshness_sql()),
        dataset("ds_layers", "Layer coverage", layers_sql()),
    ]


# ---------------------------------------------------------------- widgets

def _frame(title, description=None):
    frame = {"showTitle": True, "title": title}
    if description:
        frame.update({"showDescription": True, "description": description})
    return frame


def _place(widget, x, y, width, height):
    return {"widget": widget, "position": {"x": x, "y": y, "width": width, "height": height}}


def _field(name, expression=None):
    return {"name": name, "expression": expression or f"`{name}`"}


def text(name, lines, x, y, width, height):
    return _place({"name": name, "multilineTextboxSpec": {"lines": lines}}, x, y, width, height)


def counter(name, dataset, field, expression, title, description, x, y, value_format=None):
    value = {"fieldName": field, "displayName": title}
    if value_format:
        value["format"] = value_format
    return _place({
        "name": name,
        "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": [_field(field, expression)],
                                                     "disaggregated": False}}],
        "spec": {"version": 2, "widgetType": "counter", "encodings": {"value": value},
                 "frame": _frame(title, description)},
    }, x, y, 2, 3)


def status_bar(name, dataset, dimension, title, description, x, y, width, height, filters=None):
    """Result count per value of `dimension`, stacked by status, horizontal so long names stay readable."""
    query = {"datasetName": dataset,
             "fields": [_field(dimension), _field("status"), _field("count(*)", "COUNT(`*`)")],
             "disaggregated": False}
    if filters:
        query["filters"] = [{"expression": f} for f in filters]
    return _place({
        "name": name,
        "queries": [{"name": "main_query", "query": query}],
        "spec": {
            "version": 3, "widgetType": "bar",
            "encodings": {
                "x": {"fieldName": "count(*)", "scale": {"type": "quantitative"}, "displayName": "Results"},
                "y": {"fieldName": dimension, "scale": {"type": "categorical"},
                      "displayName": dimension.replace("_", " ").capitalize()},
                "color": {"fieldName": "status", "scale": {"type": "categorical", "mappings": [
                    {"value": status, "color": color} for status, color in STATUS_COLORS.items()]},
                          "displayName": "Status"},
            },
            "frame": _frame(title, description),
        },
    }, x, y, width, height)


def heatmap(name, x_field, y_field, value_name, value_expression, value_label, ramp, title, description,
            x, y, width, height, value_format=None, filters=None):
    """A grid of x by y on the current dataset, colored by one aggregate, with the value in each cell."""
    color = {"fieldName": value_name, "displayName": value_label,
             "scale": {"type": "quantitative", "colorRamp": {"mode": "custom-sequential",
                                                             "colors": {"start": ramp[0], "end": ramp[1]}}}}
    if value_format:
        color["format"] = value_format
    return _place({
        "name": name,
        "queries": [{"name": "main_query", "query": {
            "datasetName": "ds_current",
            "fields": [_field(x_field), _field(y_field), _field(value_name, value_expression)],
            **({"filters": [{"expression": f} for f in filters]} if filters else {}),
            "disaggregated": False}}],
        "spec": {
            "version": 3, "widgetType": "heatmap",
            "encodings": {
                "x": {"fieldName": x_field, "scale": {"type": "categorical"},
                      "displayName": x_field.replace("_", " ").capitalize()},
                "y": {"fieldName": y_field, "scale": {"type": "categorical"},
                      "displayName": y_field.replace("_", " ").capitalize()},
                "color": color,
                "label": {"show": True},
            },
            "frame": _frame(title, description),
        },
    }, x, y, width, height)


def trend(name, x, y, width, height):
    return _place({
        "name": name,
        "queries": [{"name": "main_query", "query": {
            "datasetName": "ds_history",
            "fields": [_field("daily(checked_at_utc)", 'DATE_TRUNC("DAY", `checked_at_utc`)'),
                       _field("status"), _field("count(*)", "COUNT(`*`)")],
            "disaggregated": False}}],
        "spec": {
            "version": 3, "widgetType": "line",
            "encodings": {
                "x": {"fieldName": "daily(checked_at_utc)", "scale": {"type": "temporal"}, "displayName": "Day (UTC)"},
                "y": {"fieldName": "count(*)", "scale": {"type": "quantitative"}, "displayName": "Result events"},
                "color": {"fieldName": "status", "scale": {"type": "categorical", "mappings": [
                    {"value": status, "color": color} for status, color in STATUS_COLORS.items()]},
                          "displayName": "Status"},
            },
            "frame": _frame("History: check-result events per day (UTC)",
                            "Every recorded result in the date range. A check that ran in three runs is three "
                            "events, so this is activity and direction, not the number of checks."),
        },
    }, x, y, width, height)


def donut(name, attribute, means, x, y, width, height):
    """One core attribute's pass rate of current tests, as a donut (Vega-Lite; standard pies have no hole).

    Aggregated with no GROUP BY, the query returns one row even when the attribute has no test, with
    NULLs, which the donut shows as "No checks", never as 0% or 100%."""
    vega = {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
        "data": {"name": "databricks_query"},
        "width": "container", "height": "container",
        "config": {"autosize": {"type": "fit", "contains": "padding"}, "view": {"stroke": None}},
        "transform": [
            {"calculate": "datum.tests > 0 ? datum.passed / datum.tests : null", "as": "rate"},
            {"calculate": "datum.rate == null ? 'No checks' : format(datum.rate, '.0%')", "as": "label"},
            {"calculate": "datum.rate == null ? 0 : datum.rate", "as": "PASS"},
            {"calculate": "datum.rate == null ? 1 : 1 - datum.rate", "as": "Not PASS"},
            {"fold": ["PASS", "Not PASS"], "as": ["part", "share"]},
        ],
        "layer": [
            {"mark": {"type": "arc", "innerRadius": {"expr": "min(width, height) * 0.3"},
                      "outerRadius": {"expr": "min(width, height) * 0.48"}},
             "encoding": {
                 "theta": {"field": "share", "type": "quantitative", "stack": True},
                 "color": {"field": "part", "type": "nominal", "legend": None,
                           "scale": {"domain": ["PASS", "Not PASS"], "range": [STATUS_COLORS["PASS"], "#D9D9D9"]}},
                 "order": {"field": "part", "sort": "descending"},
                 "tooltip": [{"field": "passed", "type": "quantitative", "title": "PASS tests"},
                             {"field": "tests", "type": "quantitative", "title": "Current tests"}]}},
            {"transform": [{"filter": "datum.part == 'PASS'"}],
             "mark": {"type": "text", "fontSize": 18, "fontWeight": "bold",
                      "color": {"expr": "colors.textPrimary.default"}},
             "encoding": {"text": {"field": "label", "type": "nominal"}}},
        ],
    }
    return _place({
        "name": name,
        "queries": [{"name": "main_query", "query": {
            "datasetName": "ds_current",
            "fields": [_field("passed", "SUM(`is_test_pass`)"), _field("tests", "SUM(`is_test`)")],
            "filters": [{"expression": f"`quality_attribute` = '{attribute}'"}],
            "disaggregated": False}}],
        "spec": {"version": 1, "widgetType": "custom-vega-viz",
                 "jsonSpec": {"type": "vega-lite", "spec": json.dumps(vega)},
                 "encodings": {"fields": [{"fieldName": "passed"}, {"fieldName": "tests"}]},
                 "data": {"queryName": "main_query"},
                 "frame": _frame(attribute, means)},
    }, x, y, width, height)


def table(name, dataset, columns, title, description, x, y, width, height, filters=None):
    query = {"datasetName": dataset, "fields": [_field(field) for field, _ in columns], "disaggregated": True}
    if filters:
        query["filters"] = [{"expression": f} for f in filters]
    return _place({
        "name": name,
        "queries": [{"name": "main_query", "query": query}],
        "spec": {"version": 2, "widgetType": "table",
                 "encodings": {"columns": [{"fieldName": field, "displayName": label} for field, label in columns]},
                 "frame": _frame(title, description)},
    }, x, y, width, height)


def multi_filter(name, title, field, datasets_, x, y, width, height=2, default=None):
    widget = {
        "name": name,
        "queries": [{"name": f"{name}_{d}", "query": {"datasetName": d, "fields": [_field(field)],
                                                      "disaggregated": False}} for d in datasets_],
        "spec": {"version": 2, "widgetType": "filter-multi-select",
                 "encodings": {"fields": [{"fieldName": field, "displayName": title, "queryName": f"{name}_{d}"}
                                          for d in datasets_]},
                 "frame": _frame(title)},
    }
    if default:
        widget["spec"]["selection"] = {"defaultSelection": {"values": {
            "dataType": "STRING", "values": [{"value": v} for v in default]}}}
    return _place(widget, x, y, width, height)


def date_filter(name, x, y, width, height=2):
    by_parameter = ["ds_history"]
    queries = [{"name": f"{name}_{d}", "query": {"datasetName": d, "parameters": [
        {"name": "history_range", "keyword": "history_range"}], "disaggregated": False}} for d in by_parameter]
    queries.append({"name": f"{name}_ds_runs", "query": {"datasetName": "ds_runs",
                                                         "fields": [_field("run_started_at_utc")],
                                                         "disaggregated": False}})
    fields = [{"parameterName": "history_range", "queryName": f"{name}_{d}"} for d in by_parameter]
    fields.append({"fieldName": "run_started_at_utc", "queryName": f"{name}_ds_runs"})
    return _place({
        "name": name, "queries": queries,
        "spec": {"version": 2, "widgetType": "filter-date-range-picker", "encodings": {"fields": fields},
                 "frame": _frame("Date range (UTC)",
                                 f"History and runs; default the last {HISTORY_DAYS} days. "
                                 "Current results are not date-filtered.")},
    }, x, y, width, height)


# ---------------------------------------------------------------- pages

PERCENT = {"type": "number-percent", "decimalPlaces": {"type": "max", "places": 1}}
CURRENT_SCOPE = ("Current results: the newest result of each check, from whichever run checked it last. "
                 "Counts are check results, not data rows.")


def overview_page(attributes, core):
    run_columns = [("run_id", "Job run"), ("run_status", "Run status"), ("environment", "Environment"),
                   ("run_started_at_utc", "Started (UTC)"), ("run_finished_at_utc", "Finished (UTC)"),
                   ("duration_minutes", "Minutes"), ("steps_not_succeeded", "Steps not succeeded"),
                   ("failure_stages", "Failure stage"), ("last_error_message", "Error (first 300 characters)"),
                   ("pass_results", "PASS results"), ("warn_results", "WARN results"),
                   ("fail_results", "FAIL results"), ("code_revisions", "Code revision")]
    layout = [
        text("overview_title", [
            "# Data quality: Education Access Intelligence pipeline\n", "\n",
            "What every gate recorded in `edu_access.01-control.data_quality_results`, with runs from "
            "`pipeline_runs` and deliveries from `ingestion_batches`. **Counts are check results, never data "
            "rows.** All times are UTC. **Current** widgets show the newest result of each check; **History** "
            "widgets count every recorded result in the date range. A layer with no results says so, it is not "
            "shown as passing. Definitions are at the bottom of this page.",
        ], 0, 0, 12, 3),
        counter("kpi_checks", "ds_current", "sum(is_result)", "SUM(`is_result`)", "Current checks",
                "Results in the current view (tests and recorded counts). Empty: nothing recorded yet.", 0, 3),
        counter("kpi_pass", "ds_current", "sum(is_pass)", "SUM(`is_pass`)", "PASS",
                "Current results with status PASS", 2, 3),
        counter("kpi_warn", "ds_current", "sum(is_warn)", "SUM(`is_warn`)", "WARN",
                "Current results with status WARN", 4, 3),
        counter("kpi_fail", "ds_current", "sum(is_fail)", "SUM(`is_fail`)", "FAIL",
                "Current results with status FAIL", 6, 3),
        counter("kpi_pass_rate", "ds_current", "measure(Pass rate (tests))", "MEASURE(`Pass rate (tests)`)",
                "Pass rate (tests)", "PASS / (PASS + WARN + FAIL) of current tests, recorded counts left out. "
                "Not a data-quality score.", 8, 3, PERCENT),
        counter("kpi_stale", "ds_freshness", "sum(is_stale)", "SUM(`is_stale`)", "Stale-source WARNs",
                "source_fresh WARNs in the latest freshness check, the rows the stale_sources alert emails", 10, 3),
        table("latest_run", "ds_runs", run_columns[:12],
              "Latest job run", "The run that started last (pipeline_runs rolled up to the job run). Result "
              "counts are that run's events only.", 0, 6, 12, 3, filters=["`run_recency` = 1"]),
        heatmap("current_by_layer", "status", "layer", "count(*)", "COUNT(`*`)", "Results", ("#E8F1FA", "#0072B2"),
                "Current results by layer and status",
                CURRENT_SCOPE + " A layer with no results is absent here; see Layer coverage.", 0, 9, 6, 6),
        table("layer_coverage", "ds_layers", [
            ("layer", "Layer"), ("coverage_state", "Coverage"), ("result_events", "Result events (all time)"),
            ("runs", "Runs"), ("distinct_checks", "Check names"), ("last_checked_at_utc", "Last checked (UTC)")],
              "Layer coverage", "Every pipeline layer. 'No checks recorded yet' means no gate of that layer has "
              "written a result: not built or not run, never a pass.", 6, 9, 6, 6),
        heatmap("current_by_source", "quality_attribute", "source_id", "measure(Pass rate (tests))",
                "MEASURE(`Pass rate (tests)`)", "Pass rate (tests)", (STATUS_COLORS["FAIL"], STATUS_COLORS["PASS"]),
                "Pass rate by source and core attribute, sources only (current)",
                "Each cell: PASS / (PASS + WARN + FAIL) of that source's current tests of that attribute. An empty "
                "cell has no test, which is not a pass. Gold and Analytics tables have their own chart below.",
                0, 15, 6, 7, PERCENT, filters=[
                    "`layer` IN ('control', 'bronze', 'silver', 'integration')",
                    "`quality_attribute` IN (" + ", ".join(f"'{name}'" for name, _ in core) + ")"]),
        status_bar("current_by_attribute", "ds_current", "quality_attribute", "Current results by quality attribute",
                   "From config/quality_attributes.yml. An attribute missing here has no check, which is not a "
                   "pass. Unclassified checks stay visible; Recorded count is evidence, always PASS.",
                   6, 15, 6, 7),
        status_bar("gold_by_table", "ds_current", "table_name", "Gold and Analytics: current results by table",
                   "Each Gold dimension and fact, and each Analytics output, as its gate last checked it "
                   "(docs/architecture/data-model.md). Fact-to-dimension keys are the Referential integrity checks.",
                   0, 22, 6, 7, filters=["`layer` IN ('gold', 'analytics')"]),
        table("gold_lineage", "ds_current", [
            ("table_name", "Gold table"), ("check_name", "Reads"), ("status", "Status"),
            ("expected", "Expected"), ("actual", "Job run read"), ("last_checked_at_utc", "Checked (UTC)")],
              "Gold lineage: upstream builds each Gold table read (current)",
              "One upstream_run_<table> check per Silver or Integration table a Gold gate reads: PASS when that "
              "build succeeded in the same job run.", 6, 22, 6, 7, filters=["`check_name` LIKE 'upstream_run_%'"]),
        trend("history_by_day", 0, 29, 12, 6),
        table("freshness", "ds_freshness", [
            ("source_id", "Source"), ("freshness_status", "Status"), ("freshness_limit", "Limit"),
            ("freshness_observed", "Observed"), ("last_succeeded_at_utc", "Last succeeded delivery (UTC)"),
            ("current_batches", "Current batches"), ("freshness_checked_at_utc", "Checked (UTC)")],
              "Source freshness (current)", "Latest source_fresh check, as the stale_sources alert reads it. "
              "Limits come from config/freshness.yml; a WARN means check the publisher, not that data is wrong.",
              0, 35, 6, 7),
        table("recent_runs", "ds_runs", run_columns, "Job runs (history)",
              "Runs that started in the date range. A Bronze load's own run is rolled up to its job run. "
              "'no pipeline_runs row' means results exist under a run id with no run record.", 6, 35, 6, 7),
        table("quarantine", "ds_current", [
            ("source_id", "Source"), ("batch_period", "School year or dataset"), ("table_name", "Table"),
            ("check_name", "Check"), ("status", "Status"), ("expected", "Expected"),
            ("actual", "Quarantined rows"), ("last_checked_at_utc", "Checked (UTC)")],
              "Quarantine against the 1% limit (current)", "Silver quarantine_rate per delivery: WARN above 0, "
              "FAIL above 1% of that year's Bronze rows. Expected and actual are shown as recorded.",
              0, 42, 6, 6, filters=["`check_name` LIKE 'quarantine_rate%'"]),
        table("match_rates", "ds_current", [
            ("source_id", "Source"), ("table_name", "Map"), ("check_name", "Check (school year, level)"),
            ("status", "Status"), ("expected", "Expected"), ("actual", "Match rate (%)"),
            ("last_checked_at_utc", "Checked (UTC)")],
              "PSGC match rates (current)", "As each PSGC map's gate records them. The DepEd school map checks "
              "each school year and level (match_rate_<school year>_<level>) and FAILs below 99%; the other maps "
              "record their rate, per census year for school-age population.",
              6, 42, 6, 6, filters=["`check_name` LIKE 'match_rate%'"]),
        text("definitions", [
            "### Definitions\n", "\n",
            "**PASS** as expected. **WARN** worth knowing, not necessarily wrong (for example rows quarantined "
            "within the limit, a stale source); the batch or build stands. **FAIL** the batch or build is not "
            "trusted: a Bronze batch is not marked succeeded, a Silver or Integration candidate is not "
            "published, and the gate task fails.\n", "\n",
            "**Current** is one row per (layer, source, table, check, batch): its newest result. Results of a "
            "delivery replaced by a newer version are left out; a failed or blocked delivery stays until it is "
            "retried. A check no gate runs any more keeps its last result, with its date.\n", "\n",
            "**Pass rate (tests)** = PASS / (PASS + WARN + FAIL) over current tests; each donut is the same rate for "
            "one core attribute. *Recorded counts* (how many "
            "rows a cleaning rule changed, matches per method, row kinds) are always PASS and left out. It is "
            "empty, not 0% or 100%, when there is no test result.\n", "\n",
            "**Quality attributes**: " + ", ".join(attributes) + ". Assigned in config/quality_attributes.yml; "
            "a check it does not list is **Unclassified**, shown, and covers no attribute.",
        ], 0, 48, 12, 5),
    ]
    # The core attributes' donuts go under the counters; everything after them moves down.
    donut_height, top = 6, 6
    for item in layout:
        if item["position"]["y"] >= top:
            item["position"]["y"] += donut_height
    width = 12 // len(core)
    layout[7:7] = [donut(f"donut_{name.lower()}", name, means, i * width, top, width, donut_height)
                   for i, (name, means) in enumerate(core)]
    return {"name": "overview", "displayName": "Quality overview", "pageType": "PAGE_TYPE_CANVAS",
            "layoutVersion": "GRID_V1", "layout": layout}


def explorer_page():
    explored = ["ds_history", "ds_current"]
    layout = [
        text("explorer_title", [
            "## Check explorer\n", "\n",
            "Find a WARN or FAIL and trace it to its run, batch, and code revision. Status starts at WARN and "
            "FAIL; add PASS to compare. Results hold counts and rules, never row values. Times are UTC.",
        ], 0, 0, 12, 2),
        multi_filter("f_status", "Status", "status", explored, 0, 2, 2, default=["WARN", "FAIL"]),
        multi_filter("f_attribute", "Quality attribute (current)", "quality_attribute", ["ds_current"], 2, 2, 2),
        multi_filter("f_table", "Table", "table_name", explored, 4, 2, 3),
        multi_filter("f_check", "Check", "check_name", explored, 7, 2, 3),
        multi_filter("f_run", "Job run", "run_id", explored, 10, 2, 2),
        table("events", "ds_history", [
            ("checked_at_utc", "Checked (UTC)"), ("status", "Status"), ("layer", "Layer"), ("source_id", "Source"),
            ("table_name", "Table"), ("check_name", "Check"), ("expected", "Expected"), ("actual", "Actual"),
            ("run_id", "Job run"), ("batch_id", "Batch"), ("code_revision", "Code revision")],
              "History: every result event in the date range",
              "Each row is one recorded result. The same check appears once per run (and batch) that ran it, "
              "so a check that keeps warning shows once per run.", 0, 4, 12, 9),
        table("current_detail", "ds_current", [
            ("last_checked_at_utc", "Last checked (UTC)"), ("status", "Status"), ("layer", "Layer"),
            ("source_id", "Source"), ("table_name", "Table"), ("check_name", "Check"), ("expected", "Expected"),
            ("actual", "Actual"), ("quality_attribute", "Attribute"), ("classification_basis", "Why this attribute"),
            ("batch_period", "Period"), ("batch_state", "Batch"), ("run_id", "Job run"), ("batch_id", "Batch id"),
            ("code_revision", "Code revision")],
              "Current: newest result of each check",
              "Not date-filtered. One row per (layer, source, table, check, batch).", 0, 13, 12, 9),
    ]
    return {"name": "explorer", "displayName": "Check explorer", "pageType": "PAGE_TYPE_CANVAS",
            "layoutVersion": "GRID_V1", "layout": layout}


def filters_page():
    checked = ["ds_current", "ds_history"]
    layout = [
        date_filter("g_dates", 0, 0, 12),
        multi_filter("g_layer", "Layer", "layer", checked + ["ds_layers"], 0, 2, 12),
        multi_filter("g_source", "Source", "source_id", checked + ["ds_freshness"], 0, 4, 12),
    ]
    return {"name": "filters", "displayName": "Filters", "pageType": "PAGE_TYPE_GLOBAL_FILTERS",
            "layoutVersion": "GRID_V1", "layout": layout}


def dashboard(repo_root=REPO_ROOT):
    attributes, core, rows = load_catalog(repo_root)
    return {
        "datasets": datasets(rows),
        "pages": [overview_page(attributes, core), explorer_page(), filters_page()],
        "uiSettings": {"theme": {
            "canvasBackgroundColor": {"light": "#F7F8FA", "dark": "#1F272D"},
            "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#11171C"},
            "widgetBorderColor": {"light": "#FFFFFF", "dark": "#11171C"},
            "fontColor": {"light": "#11171C", "dark": "#E8ECF0"},
            "selectionColor": {"light": "#2272B4", "dark": "#8ACAFF"},
            "visualizationColors": ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9",
                                    "#999999", "#F0E442"],
            "widgetHeaderAlignment": "LEFT",
        }},
    }


def render(repo_root=REPO_ROOT):
    return json.dumps(dashboard(repo_root), indent=2, ensure_ascii=False) + "\n"


def main():
    try:
        sys.stdout.write(render())
    except CatalogError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
