# Shared profiling code

Helpers used by more than one script in `notebooks/profiling/` (D-007). The profiling scripts themselves stay in `notebooks/profiling/`.

| Module | What it holds |
|---|---|
| `xlsx.py` | Reads one sheet of an xlsx workbook with the standard library: `read_sheet` (rows as `(row number, {column number: text})`), `sheet_names`, `sheet_xml_path`, `rich_text` (skips phonetic guides), `column_number`, `column_letter` |

## Using it from a profiling script

A script in `notebooks/profiling/` runs from its own folder, so it puts the repository root on the import path first:

```python
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import read_sheet
```

Tests import it the same way as `python -m pytest tests -q` runs from the repository root.

Add a helper here when a second script needs it, and keep it free of source-specific names.
