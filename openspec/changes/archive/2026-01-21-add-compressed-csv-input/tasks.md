## 1. Implementation
- [x] 1.1 Detect `.csv.gz` and `.zip` inputs in input resolution and ensure output naming uses inner CSV name when needed.
- [x] 1.2 For `.zip`, resolve the single CSV entry and build a `zip://` path; fail with a clear error if zero or multiple CSVs are found.
- [x] 1.3 Auto-install/load DuckDB `zipfs` extension on `.zip` inputs and surface errors with guidance.
- [x] 1.4 Pass/ensure DuckDB CSV read options use compression autodetect for `.csv.gz`.
- [x] 1.5 Update processing summary and logging to mention compressed input handling.
- [x] 1.6 Add tests for `.csv.gz` success and `.zip` (single CSV) success, plus `.zip` multi/empty error cases.

## 2. Validation
- [ ] 2.1 `pytest`
- [ ] 2.2 `ruff check .`
- [ ] 2.3 `ruff format --check .`
