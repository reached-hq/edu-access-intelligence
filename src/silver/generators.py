"""Which module generates a source's Silver files.

Most sources follow the DepEd mapping format (src/silver/spec.py, sql.py,
dictionary.py). A source whose shape that format cannot describe names its own
module in its rules file as "generator" (PSA Poverty Stat: one wide row per unit
holding several estimate years, D-027). Every generator module provides
load_spec, build_sql, gate_sql and dictionary_markdown.
"""

import importlib
import json
import types
from pathlib import Path

from src.silver import dictionary, spec, sql

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT = types.SimpleNamespace(load_spec=spec.load_spec, build_sql=sql.build_sql, gate_sql=sql.gate_sql,
                                dictionary_markdown=dictionary.dictionary_markdown)


def generator(source_id, repo_root=REPO_ROOT):
    path = Path(repo_root) / "config" / "mappings" / f"{source_id}.json"
    name = json.loads(path.read_text(encoding="utf-8")).get("generator") if path.is_file() else None
    return importlib.import_module(f"src.silver.{name}") if name else DEFAULT
