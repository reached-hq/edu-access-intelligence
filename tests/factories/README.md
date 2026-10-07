# Test factories

Python builders for deterministic, made-up test inputs. Factories write into
pytest-provided temporary directories; generated files are never committed.

| Factory | What it builds |
|---|---|
| `deped_deliveries.py` | DepEd-shaped ZIPs from the real column contracts, with invented schools and fixed timestamps so checksums are repeatable |
