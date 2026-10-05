"""Batch identity, and what to do with a delivery given what the control tables remember.

A batch is one distinct archive, identified by its SHA-256. The same bytes
always get the same batch_id, wherever the file sits and however often it is
seen, so "has this exact file been processed?" is one lookup.

| Seen before?                          | Action | Effect                                         |
|---------------------------------------|--------|------------------------------------------------|
| no                                    | load   | first attempt                                  |
| yes, succeeded                        | skip   | recorded in the attempts log; nothing loaded   |
| yes, succeeded, rerun asked for       | rerun  | validated and merged again; adds no rows       |
| yes, failed or interrupted            | retry  | merged again; adds only rows that are missing  |
| yes, blocked, and now approved        | load   | first real attempt                             |
| yes, skipped as a re-zipped copy      | skip   |                                                |

The load type says why a new batch arrived, relative to what already
succeeded for the source: the first ever (initial), a later school year
(incremental), an earlier one (backfill), or a new version of a school year
(revision).
"""

RETRYABLE = {"validating", "loading", "failed"}


def batch_id(source_id, school_year, archive_sha256):
    return f"{source_id}__{school_year or 'unknown'}__{archive_sha256[:12]}"


def choose_action(existing, rerun=False):
    if existing is None or existing["status"] == "blocked":
        return "load"
    if existing["status"] == "succeeded":
        return "rerun" if rerun else "skip"
    if existing["status"] in RETRYABLE:
        return "retry"
    return "skip"


def load_type(delivery, succeeded_years):
    """succeeded_years: school years with at least one succeeded batch for this source."""
    if delivery["delivery_version"] > 1:
        return "revision"
    if not succeeded_years:
        return "initial"
    if delivery["school_year"] < max(succeeded_years):
        return "backfill"
    return "incremental"
