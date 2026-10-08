# Test factories

Python builders for deterministic, made-up test inputs. Factories write into
pytest-provided temporary directories; generated files are never committed.

| Factory | What it builds |
|---|---|
| `deped_deliveries.py` | DepEd-shaped ZIPs from the real column contracts, with invented schools and fixed timestamps so checksums are repeatable |
| `psa_workbooks.py` | PSA Poverty Stat-shaped xlsx workbooks (title, merged header in rows 2 to 5, region banners, empty column S, `Notes:` footer) from the real contract's columns, with invented places (IDs from 99xxx) and one of each known publisher quirk; standard library only, fixed timestamps |
