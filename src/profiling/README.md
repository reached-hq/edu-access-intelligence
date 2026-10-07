# Shared profiling code

Helpers used by more than one script in `analysis/profiling/` (D-007). The profiling scripts themselves stay in `analysis/profiling/`.

| Module | What it holds |
|---|---|
| `xlsx.py` | Reads one sheet of an xlsx workbook with the standard library: `read_sheet` (rows as `(row number, {column number: text})`), `sheet_names`, `sheet_xml_path`, `rich_text` (skips phonetic guides), `column_number`, `column_letter` |

## Using it from a profiling script

A script in `analysis/profiling/` runs from its own folder, so it puts the repository root on the import path first:

```python
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import read_sheet
```

Tests import `src.profiling.xlsx` directly, without that `sys.path` line, because `python -m pytest tests -q` run from the repository root already puts the repository root on the Python path.

Add a helper here when a second script needs it, and keep it free of source-specific names.
