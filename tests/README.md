# Tests

Run the complete local suite from the repository root:

```bash
python -m pytest tests -q
```

| Location | Purpose |
|---|---|
| `factories/` | Python builders that create deterministic, made-up inputs in temporary directories |
| `data/` | Small static, made-up files when a factory is not practical |
| `test_repo_policy.py` | Data, secret, environment, and file-size rules |
| `test_documentation_structure.py` | Required indexes, retired paths, and local Markdown links |
| `test_naming.py` | Naming configuration and ETL path conventions |
| `test_ingestion_*.py` | Delivery validation, loading, rerun, and source-specific behavior |

Tests must never depend on real source rows or credentials.
