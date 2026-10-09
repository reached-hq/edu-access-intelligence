"""What a source's Silver table looks like: every Bronze column, its Silver name, kind, and rule.

Two reviewed files define it, and nothing else:

- `config/ingestion/<source_id>.json`, the Bronze contract: which publisher
  columns exist in which schema version;
- `config/mappings/<source_id>.json`, the Silver mapping: how each column is
  cleaned, and every category label with the standard value it maps to.

Every publisher column must be classified exactly once (identifier, free text,
category, boolean, or count). A column the mapping does not classify stops the
generator, so a new schema version cannot reach Silver without a reviewed
change to the mapping. Labels may not contain quotes or backslashes, so the
generated SQL never has to escape them (Spark and DuckDB escape differently).
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.ingestion.bronze import source_columns
from src.ingestion.contract import load_source_config
from src.ingestion.errors import IngestionError

SCHEMA = "03-silver"

# Column kinds and the Silver type each one gets.
IDENTIFIER, FREE_TEXT, CATEGORY, BOOLEAN, COUNT = "identifier", "free_text", "category", "boolean", "count"
TYPES = {IDENTIFIER: "string", FREE_TEXT: "string", CATEGORY: "string", BOOLEAN: "boolean", COUNT: "int"}

# Why a row is set aside, in the order they are listed on a quarantined row.
QUARANTINE_REASONS = (
    "school_id_blank",
    "school_id_malformed",
    "school_id_duplicated",
    "count_negative",
    "count_uncastable",
    "count_above_plausible_max",
)

ENROLLMENT_STATUSES = ("has_learners", "all_zero", "no_counts")

# Bronze provenance carried on every Silver and quarantine row, then the Silver run's own stamp.
LINEAGE = (
    ("batch_id", "string"),
    ("delivery_version", "int"),
    ("schema_version", "string"),
    ("source_sha256", "string"),
    ("source_row_number", "bigint"),
)
RUN_STAMP = (("run_id", "string"), ("cleaned_at_utc", "timestamp"), ("code_revision", "string"))
FLAGS = (("is_overseas", "boolean"), ("enrollment_status", "string"), ("barangay_possibly_truncated", "boolean"))

SAFE_LITERAL = re.compile(r"^[^'\\]*$")


def _error(message):
    return IngestionError("config", "invalid_silver_mapping", message)


@dataclass
class Column:
    name: str            # Silver name
    source: str          # Bronze column it comes from
    kind: str
    rule: str = ""       # one line for the data dictionary
    finding: str = ""    # profile finding the rule comes from

    @property
    def type(self):
        return TYPES[self.kind]


@dataclass
class Category:
    column: str
    standard: list
    labels: dict         # published label -> standard value
    finding: str
    rule: str


@dataclass
class SilverSpec:
    source_id: str
    bronze_table: str
    clean_file: str
    clean_table: str
    quarantine_table: str
    clean_candidate: str               # the unpublished build the gate checks (D-025)
    quarantine_candidate: str
    identifier: str
    identifier_pattern: str
    max_digits: int
    plausible_max: int                 # a count above it quarantines the row
    columns: list                      # publisher columns, in Silver order
    categories: dict                   # Silver column -> Category
    boolean_true: list
    boolean_false: list
    repairs: list                      # [(published, standard)]
    placeholders: dict                 # Silver column -> [published values that mean "no value"]
    barangay: str
    barangay_cap: int
    overseas: dict                     # Silver category column -> standard value meaning overseas
    absent: dict                       # schema version -> Silver columns that version does not publish
    mapping: dict = field(repr=False)  # the reviewed file, for the data dictionary

    def of_kind(self, *kinds):
        return [c for c in self.columns if c.kind in kinds]

    @property
    def counts(self):
        return self.of_kind(COUNT)

    @property
    def text(self):
        """Every column cleaned as text: identifier excluded, it is validated exactly as published."""
        return self.of_kind(FREE_TEXT, CATEGORY, BOOLEAN)

    def column(self, name):
        return next(c for c in self.columns if c.name == name)

    def clean_columns(self):
        """[(name, type)] of the clean table, in order."""
        columns = [("school_year", "string")]
        columns += [(c.name, c.type) for c in self.columns]
        return columns + list(FLAGS) + list(LINEAGE) + list(RUN_STAMP)

    def quarantine_columns(self):
        return ([("school_year", "string"), (self.identifier, "string"), ("quarantine_reasons", "array<string>")]
                + list(LINEAGE) + list(RUN_STAMP))


def mapping_path(repo_root, source_id):
    return Path(repo_root) / "config" / "mappings" / f"{source_id}.json"


def load_spec(repo_root, source_id):
    path = mapping_path(repo_root, source_id)
    if not path.is_file():
        raise _error(f"{path} does not exist; {source_id} has no Silver mapping.")
    mapping = json.loads(path.read_text(encoding="utf-8"))
    contract, _ = load_source_config(repo_root, source_id)
    registry = yaml.safe_load((Path(repo_root) / "config" / "tables.yml").read_text(encoding="utf-8"))
    entry = next((s for s in registry["source_tables"] if s["source_id"] == source_id), None)
    return build_spec(mapping, contract, entry)


def build_spec(mapping, contract, registry_entry):
    source_id = contract["source_id"]
    if mapping.get("source_id") != source_id:
        raise _error("source_id differs from the Bronze contract.")
    if registry_entry is None or registry_entry["silver"]["table"] != mapping["silver_table"] \
            or registry_entry["silver"]["quarantine_table"] != mapping["quarantine_table"]:
        raise _error("silver_table and quarantine_table must match config/tables.yml.")

    renames = {src: r["to"] for src, r in mapping.get("renames", {}).items()}
    published = source_columns(contract)
    unknown_renames = sorted(set(renames) - set(published))
    if unknown_renames:
        raise _error(f"renames name columns the contract does not have: {unknown_renames}.")
    silver_name = {c: renames.get(c, c) for c in published}
    for name in silver_name.values():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise _error(f"column {name!r} is not snake_case; add it to renames.")

    identifier = mapping["identifier"]["column"]
    suffixes = tuple(mapping["count_columns"]["suffixes"])
    free_text = mapping["free_text_columns"]
    booleans = mapping["booleans"]["columns"]
    categories = mapping["categories"]

    kinds = {}
    for name in silver_name.values():
        found = [kind for kind, member in (
            (IDENTIFIER, name == identifier), (FREE_TEXT, name in free_text), (CATEGORY, name in categories),
            (BOOLEAN, name in booleans), (COUNT, name.endswith(suffixes))) if member]
        if len(found) != 1:
            raise _error(f"column {name!r} must be classified exactly once; found {found or 'none'}. "
                         "A new publisher column needs a reviewed entry in the Silver mapping.")
        kinds[name] = found[0]
    listed = {identifier, *free_text, *categories, *booleans}
    stray = sorted(listed - set(silver_name.values()))
    if stray:
        raise _error(f"the mapping lists columns the contract does not have: {stray}.")

    parsed = {}
    for name, entry in categories.items():
        standard = entry["standard"]
        labels = {}
        for label in entry["labels"]:
            if label["published"] in labels:
                raise _error(f"{name}: label {label['published']!r} is listed twice.")
            if label["standard"] not in standard:
                raise _error(f"{name}: {label['published']!r} maps to {label['standard']!r}, which is not in the standard set.")
            labels[label["published"]] = label["standard"]
        if len(set(standard)) != len(standard):
            raise _error(f"{name}: the standard set repeats a value.")
        parsed[name] = Category(name, standard, labels, entry.get("finding", ""), entry.get("rule", ""))

    true, false = mapping["booleans"]["true"], mapping["booleans"]["false"]
    if set(true) & set(false):
        raise _error("a boolean label cannot be both true and false.")
    repairs = [(r["published"], r["standard"]) for r in mapping.get("character_repairs", [])]
    placeholders = {column: entry["values"] for column, entry in mapping.get("placeholders", {}).items()}
    for column in placeholders:
        if kinds.get(column) != FREE_TEXT:
            raise _error(f"placeholders apply to free-text columns only; {column!r} is not one.")
    overseas = mapping["overseas"]["markers"]
    for column, value in overseas.items():
        if column not in parsed or value not in parsed[column].standard:
            raise _error(f"overseas marker {column}={value!r} is not a standard value of a category column.")
    barangay = mapping["barangay"]["column"]
    if kinds.get(barangay) != FREE_TEXT:
        raise _error(f"barangay column {barangay!r} must be free text.")
    max_digits, plausible_max = mapping["count_columns"]["max_digits"], mapping["count_columns"]["plausible_max"]
    if not (isinstance(plausible_max, int) and 0 < plausible_max < 10 ** max_digits):
        raise _error(f"plausible_max must be a whole number from 1 to {10 ** max_digits - 1}.")

    literals = [mapping["identifier"]["pattern"], *true, *false,
                *[v for c in parsed.values() for v in (*c.standard, *c.labels)],
                *[v for pair in repairs for v in pair], *[v for vs in placeholders.values() for v in vs]]
    unsafe = [v for v in literals if not SAFE_LITERAL.match(v)]
    if unsafe:
        raise _error(f"labels may not contain quotes or backslashes: {unsafe}.")

    rules = {
        IDENTIFIER: ("Kept as published; a blank, malformed, or repeated value quarantines the row", mapping["identifier"].get("finding", "")),
        FREE_TEXT: ("Character repair, whitespace trimmed and collapsed, blank to NULL", "O-5, O-15, O-17"),
        BOOLEAN: (f"{'/'.join(true)} to TRUE, {'/'.join(false)} to FALSE, blank to NULL; any other label fails the gate", mapping["booleans"].get("finding", "")),
        COUNT: (f"Whole number to INT; blank or absent to NULL, never 0; negative, not castable, or above {plausible_max:,} "
                "quarantines the row", mapping["count_columns"].get("finding", "")),
    }
    columns = []
    order = [c for c in published if kinds[silver_name[c]] != COUNT] + [c for c in published if kinds[silver_name[c]] == COUNT]
    for source in order:
        name = silver_name[source]
        kind = kinds[name]
        if kind == CATEGORY:
            rule, finding = f"Whitespace normalized, mapped to the standard set; an unmapped label fails the gate. {parsed[name].rule}", parsed[name].finding
        else:
            rule, finding = rules[kind]
        if name in placeholders:
            rule += f"; placeholders {', '.join(repr(v) for v in placeholders[name])} to NULL"
            finding += ", " + mapping["placeholders"][name]["finding"]
        columns.append(Column(name, source, kind, rule, finding))

    absent = {}
    for version, entry in contract["schema_versions"].items():
        missing = [silver_name[c] for c in published if c not in entry["columns"]]
        if missing:
            absent[version] = missing

    return SilverSpec(
        source_id=source_id, bronze_table=contract["bronze_table"], clean_file=registry_entry["silver"]["clean_file"],
        clean_table=mapping["silver_table"],
        quarantine_table=mapping["quarantine_table"],
        clean_candidate=registry_entry["silver"]["candidate_table"],
        quarantine_candidate=registry_entry["silver"]["candidate_quarantine_table"], identifier=identifier,
        identifier_pattern=mapping["identifier"]["pattern"], max_digits=max_digits, plausible_max=plausible_max,
        columns=columns, categories=parsed, boolean_true=true, boolean_false=false, repairs=repairs,
        placeholders=placeholders, barangay=barangay, barangay_cap=mapping["barangay"]["length_cap"],
        overseas=overseas, absent=absent, mapping=mapping,
    )
